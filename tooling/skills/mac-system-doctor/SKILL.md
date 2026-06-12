---
name: mac-system-doctor
description: Diagnoses why a Mac is slow and applies safe, reversible cleanups — aggregates per-app CPU and RAM, samples memory pressure and swap, finds junk login items and launch agents, oversized regenerable caches, browser and Electron process bloat, and screen-compositing (WindowServer) overload, then fixes only what the user approves. Never touches personal data. Use when the user says "my Mac is slow", "run system doctor", "check my system health", "what's slowing down my machine", "clean up system junk", "Mac feels laggy", "why is my computer hot/loud", "do a performance checkup", or asks for safe Mac optimization or a system health diagnosis.
---

# Mac System Doctor

Read-only diagnosis of Mac slowness, then consent-gated reversible fixes. Built for repeat runs: every probe degrades gracefully across macOS versions, and nothing is ever deleted without explicit approval.

## Steps

### 1. Snapshot (read-only — run these in parallel Bash batches)

Probes vary across macOS versions: if a command errors or its output shape looks different than expected, adapt or skip it and move on — no single probe is a blocker. Add `2>/dev/null` wherever a tool might be missing.

```bash
# Hardware + OS
system_profiler SPHardwareDataType | grep -E "Model Name|Chip|Total Number of Cores|Memory:" ; sw_vers

# Load + instantaneous CPU (NOT ps — see Gotchas)
uptime ; top -l 2 -n 0 -s 2 | grep -E "CPU usage|Load Avg" | tail -2

# Memory truth: swap + pressure (grep, not tail — output layout shifts between versions)
sysctl vm.swapusage ; memory_pressure | grep -iE "free percentage|pressure"

# Disk + thermal (healthy therm = "No ... warning level has been recorded" or CPU_Speed_Limit = 100)
df -h / ; pmset -g therm

# Per-APP aggregate — groups every helper under its outer .app bundle (Electron apps hide as many small helpers)
ps axo pcpu,rss,comm | awk 'NR>1 {cmd=$3; for(i=4;i<=NF;i++) cmd=cmd" "$i; app=cmd; if (match(app, /\/[^\/]+\.app\//)) app=substr(app, RSTART+1, RLENGTH-2); else {n=split(app, p, "/"); app=p[n]} cpu[app]+=$1; mem[app]+=$2} END {for (a in cpu) printf "%6.1f%%CPU %8.0fMB  %s\n", cpu[a], mem[a]/1024, a}' | sort -rn | head -12

# Instantaneous per-process CPU — use ONLY the second sample (the first is cumulative garbage)
top -l 2 -s 2 -o cpu -stats pid,cpu,mem,command | tail -15

# Compositing + signing + indexing daemons
ps aux | grep -E "[W]indowServer|[t]rustd|[m]ds|[e]cosystem" | awk '{printf "%5s%%CPU  %s\n", $3, $11}'

# Startup surface
osascript -e 'tell application "System Events" to get the name of every login item'
ls ~/Library/LaunchAgents/ /Library/LaunchAgents/ 2>/dev/null

# Regenerable caches only (never plan to clear ~/Library/Caches wholesale)
du -sh ~/.npm ~/Library/Caches/Homebrew ~/Library/Caches/pip ~/.cache 2>/dev/null

# Browser bloat — anchor on the .app path; bare substrings false-positive wildly
# (e.g. "Edge" matches siriknowledged, "Arc" matches searchpartyd, "Chrome" matches every
#  Electron app's chrome_crashpad_handler). Safari web content runs as com.apple.WebKit.*
for b in "Brave Browser" "Google Chrome" "Safari" "Firefox" "Microsoft Edge" "Arc"; do ps aux | grep -F "/$b.app/Contents/" | grep -v grep | awk -v b="$b" '{n++; m+=$6} END {if (n) printf "%-16s %3d procs %6.0f MB\n", b, n, m/1024}'; done
```

### 2. Interpret — root-cause, don't enumerate

| Signal | Meaning |
|---|---|
| Swap = 0, free > 50% | RAM is NOT the problem. Stop hunting memory; it's CPU/compositing. Say so explicitly. |
| Swap used in GB, pageouts climbing | RAM pressure is real — find the resident hogs, recommend closing them. |
| WindowServer > 30% sustained | Compositing overload. Cause is the FEEDERS (overlays, always-on dictation/recording tools, streaming terminals, Electron apps), never WindowServer itself. |
| trustd high | Code-signature churn from heavy subprocess spawning (terminals, dev tools). A symptom, not a target. |
| `ecosystemd`/`analyticsd`/other Apple daemons high | OS-side churn. Often settles within hours of boot; persistent = Apple bug. Not fixable locally beyond the Settings → Privacy → Analytics toggle. |
| Load average > core count but CPU mostly idle | Transient spike (often the diagnosis itself). Re-sample before concluding. |

Match login items and launch agents against `references/junk-signatures.md` — it has the junk patterns and, critically, the keep-list.

### 3. Report (verdict first — see Output Format)

Rank findings by measured impact. Healthy subsystems get one "ruled out" line, not paragraphs.

### 4. Consent — one AskUserQuestion, multiSelect

Group every proposed fix into a single multi-select question with measured numbers in each option ("frees 3.2GB", "removes 31% CPU process"). Never delete, unload, or quit anything without this gate.

If running headless or as a subagent (no user to ask): stop after the report, replacing the "Fixes applied" section with "Fixes I would offer" listing each consented-fix candidate and its measured size. Diagnosis-only is the complete deliverable in that context.

### 5. Fix — reversible procedures only

- **Login items**: `osascript -e 'tell application "System Events" to delete login item "<exact name from step 1 output>"'`
- **Launch agents**: `launchctl bootout "gui/$(id -u)" "<full plist path>"` then `mv` the plist to `~/Library/LaunchAgents.disabled/` (create it). Moving — not deleting — makes restore a one-line `mv` back. `launchctl unload` is deprecated; don't use it.
- **Caches**: official tools only — `npm cache clean --force`, `brew cleanup --prune=all`, `pip cache purge`, `yarn cache clean`, `pnpm store prune`. Run only the ones whose tool is installed; each cache regenerates on next use.
- **Heavy idle apps**: sample instantaneous CPU first (`top -l 2`); only offer to quit if genuinely idle, and quit gracefully (`osascript -e 'quit app "X"'`). If it survives the quit, report that and stop — never escalate to `kill`.

### 6. Verify

Re-run the relevant probe from step 1 for everything changed. Report before → after numbers. A fix without a measured delta gets reported as "applied, no measurable change" — honesty over theater.

## Output Format

```markdown
## Verdict
<One sentence: the actual bottleneck and the single biggest win.>

## What's slowing the machine (ranked by measured impact)
- **<App/item>** — <measured number> — <why it matters in one clause>

## Ruled out
<One line: e.g., "RAM (zero swap, 61% free), disk (190GB free), thermal, Spotlight.">

## Fixes applied            ← only after consent
- <item>: <before> → <after>

## Left alone
<Anything deliberately not touched and the one-line reason.>
```

## Gotchas

- **`ps aux` %CPU is a lifetime average, not "right now".** A process that worked hard an hour ago still shows high %CPU while idle. Before quitting or blaming anything, confirm with a second-sample `top -l 2 -s 2` reading — the first `top` sample is also garbage (cumulative), only the second is instantaneous.
- **Electron apps masquerade as 15+ small helpers.** Per-process views miss them entirely; only the per-app aggregate (awk grouping above) reveals a 2GB, full-core app.
- **A graceful app quit can silently fail.** Apps auto-relaunch, sit in the menu bar, or throw a confirmation dialog you can't see. Verify with `ps` after quitting; if processes persist, report it and move on — force-killing a user's app risks losing their work.
- **Clearing `~/Library/Caches` wholesale is a trap.** It logs the user out of apps, slows every next launch, and the space comes back in days. Only ever clear named regenerable package-manager caches.
- **High WindowServer is never WindowServer's fault.** Killing or blaming it is wrong twice — it's load-bearing for the entire display, and the fix is always at the feeder apps.
- **Junk lists have false positives that break real workflows.** VPN clients, mail bridges (ProtonMail Bridge), cloud sync, window managers, and dictation tools look like background bloat but are deliberate infrastructure. Check the keep-list in `references/junk-signatures.md` before proposing removal.
- **Login item names must match the osascript listing exactly** — "Wispr Flow" not "WisprFlow". Always delete using names captured from the step 1 output, never from memory.
- **The diagnosis pollutes its own measurements.** Running probes spikes load average and trustd. Distinguish standing load from your own footprint by re-sampling before concluding.
- **Fresh uptime hides the real problem.** If the machine rebooted recently, today's healthy snapshot may not reflect the slow state the user experienced. Note uptime in the report and ask them to re-run at the next slow moment.
- **Spotlight is usually innocent.** Check actual `mds`/`mdworker` CPU before suggesting index rebuilds — rebuilding a healthy index makes the machine slower for hours.

## Constraints

- **Personal data is off-limits absolutely**: never read, list, or touch Photos, Messages, Mail, Documents, Desktop, iCloud Drive, browser profiles/history/cookies, or Keychain — not even read-only `du` over them.
- **No deletion, unload, or app-quit without the step 4 consent gate.** Reversibility is not a substitute for consent.
- **No sudo, ever.** Everything here works at user level. If a fix would need admin rights (system analytics toggle, /Library agents), describe the one Settings toggle instead.
- **Never kill system processes** — WindowServer, mds, trustd, kernel_task, or any Apple daemon. Misbehaving daemons get noted, not killed.
- **No third-party cleaner tools** — never recommend or install MacKeeper/CleanMyMac-class software; this skill exists to replace them.
- **Browser tabs and interactive app sessions belong to the user** — report their cost, never close them.
