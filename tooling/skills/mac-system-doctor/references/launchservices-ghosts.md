# LaunchServices ghost records — phantom "Support Ending for Intel-based Apps" warnings

Read only when the complaint is a recurring "Support Ending for Intel-based Apps" (or similar) notification naming an app that's already deleted.

Deleting an app's files doesn't delete macOS's opinion of it. LaunchServices keeps its own database, records outlive the files, and every macOS update rescan re-posts the warning from the record — not the disk. Diagnosing from the filesystem alone ("no Intel binaries anywhere, must be a stale banner") misses this, and Spotlight can't rule it out (it doesn't index /opt or /usr/local); dump the LS database before concluding.

## Probe (read-only)

```bash
LS=/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister
$LS -dump | grep -E "^path:" | grep -i "<AppName>"        # find every registered copy
$LS -dump | grep -A14 "<AppName>" | grep -E "path:|slices:" # ghost = path gone from disk, slices: x86_64 only
```

## Fix (after the SKILL.md step 4 consent gate)

`$LS -u "<dead path>"` for each ghost record, then `$LS -gc` to compact. User-level, no sudo. Verify by re-running the dump grep — the record must be gone.

Already-delivered banners will NOT disappear: the Notification Center database is Full-Disk-Access-protected, so no command can dismiss them — tell the user to Clear All in Notification Center once, and that no new ones can fire.

## Gotcha

- **`lsregister -kill` no longer exists.** Modern macOS removed the flag ("dangerous and no longer useful") — the working sequence is `-u <path>` per stale record then `-gc`. Never `-delete` (nukes the whole database and demands a reboot).
