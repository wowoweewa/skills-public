# Junk Signatures — startup items safe to propose removing, and the keep-list

Match against login items (`System Events` listing) and launch agent plists (`~/Library/LaunchAgents/`, `/Library/LaunchAgents/`). These are patterns, not exact names — vendors rename constantly.

## Junk patterns (safe to propose — app still works when launched manually)

| Pattern | Examples seen in the wild | What it is |
|---|---|---|
| Adobe background services | `com.adobe.GC.Invoker-*`, `AdobeResourceSynchronizer`, `com.adobe.ARMDC.*` | License pings and updaters; Creative Cloud works without them |
| Game launcher helpers | `com.epicgames.launcher`, `com.riot.riotclient.*`, `com.valvesoftware.steamclean`, OP.GG | Pre-warm/telemetry for games not currently running |
| Vendor update checkers | `com.canva.availability-check-agent`, `com.amazon.kpr.ncd` (Kindle), Microsoft AutoUpdate helpers, `MicrosoftSharePoint` | Phone-home checkers; apps update fine when opened |
| Hardware vendor helpers | `SanDiskSecurityHelper`, Seagate/WD dashboard agents, Logitech/Razer config daemons, printer utilities | Only needed while using that vendor's hardware feature |
| One-app convenience agents | `FigmaAgent` (local fonts for figma.com), video-editor helper stubs, office suite "fast start" stubs, Zoom/Webex pre-launchers | Marginal convenience, permanent background cost |
| Chat/social auto-starts | Discord, Slack, Teams set to launch at login (when user complains of slow boot) | Heavy Electron at boot; user can re-enable deliberately |

## Keep-list (looks like bloat, is deliberate infrastructure — never propose)

| Category | Examples | Why it stays |
|---|---|---|
| VPN clients | Tailscale, WireGuard, Mullvad, PIA, corporate VPNs | Network security; removal breaks connectivity silently |
| Mail bridges / local mail daemons | ProtonMail Bridge, fetchmail-style agents | Mail stops syncing without it |
| Cloud sync | Google Drive, Dropbox, OneDrive, Syncthing (the sync engine, not bundled updater junk) | Files silently stop syncing |
| Window managers / input tools | Magnet, Rectangle, Karabiner, AltTab, dictation and voice-input tools | Core workflow; user notices immediately |
| Password managers | 1Password helpers, Bitwarden, KeePassXC | Browser integration breaks |
| Time trackers / monitors the user installed | RescueTime, Rize, Usage, iStat Menus | Heavy but chosen — report the CPU cost, let the user decide; don't classify as junk |
| Anything security/auth/backup | antivirus the user chose, Time Machine helpers, MDM agents | Breaking these has consequences beyond performance |
| Local model stores of active tools | speech/ASR models under `~/.cache/<tool>` for a dictation app, embedding models for a local AI tool | Looks like a fat cache; clearing it breaks the tool until a multi-hundred-MB re-download |
| Audio HAL drivers of present hardware/apps | BlackHole, mic-vendor drivers (Rode etc.), an installed app's own audio plugin in `/Library/Audio/Plug-Ins/HAL/` | Removing breaks routing for gear/apps still in use — verify the owner is uninstalled before calling it an orphan |

## Classification rules

- An item on neither list with a recognizable app name: classify by the table *category* it resembles (updater? launcher helper? sync engine?).
- An unrecognizable item: identify before judging — `codesign -dvvv` on the plist's `Program` binary; the `Authority=Developer ID Application: <vendor>` line names who shipped it (a helper labeled `com.starstechnologies.*` turned out to be a poker client's updater this way). Still unknown after that: leave it alone and flag it as "unknown — left untouched".
- Orphan check beats category: for every `/Library/LaunchDaemons` and `/Library/LaunchAgents` entry, read the plist's `Program` path, then verify the parent app still exists (`ls /Applications/<App>.app`, and the app's known install dirs), not by name-guessing. Parent uninstalled → orphan, safe to propose whatever the category; parent present → judge by the tables above.
- Substring hits are not identifications — short patterns false-positive across reverse-DNS names: a `wdc` (Western Digital) scan also matches `com.crowdcafe.windowmagnet`, an unrelated, actively-used app. Resolve every pattern hit to its owning app before classifying; delete only names captured and verified, never pattern output directly.
- System-domain items (`/Library/LaunchAgents`, `/Library/LaunchDaemons`) need admin rights — removal only through the SKILL.md consented-elevation path (one osascript admin dialog), never raw sudo; without that grant, mention only.
- The keep-list always wins a conflict between the two tables.
