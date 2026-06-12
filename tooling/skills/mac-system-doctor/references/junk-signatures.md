# Junk Signatures — startup items safe to propose removing, and the keep-list

Match against login items (`System Events` listing) and launch agent plists (`~/Library/LaunchAgents/`, `/Library/LaunchAgents/`). These are patterns, not exact names — vendors rename constantly. When an item matches neither list, look up what it does before classifying; never guess from the filename alone.

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

## Classification rules

- An item on neither list with a recognizable app name: classify by the table *category* it resembles (updater? launcher helper? sync engine?).
- An unrecognizable item: leave it alone and flag it in the report as "unknown — left untouched".
- System-domain agents (`/Library/LaunchAgents`, `/Library/LaunchDaemons`) need admin rights — never modify; mention only.
- The keep-list always wins a conflict between the two tables.
