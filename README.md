# skills-public

Public Claude Code skills, organized by category. Each skill is a self-contained folder with a `SKILL.md` and optional `references/`.

## Skills

| Skill | What it does |
|---|---|
| [mac-system-doctor](tooling/skills/mac-system-doctor/SKILL.md) | Diagnoses why a Mac is slow, then applies safe, reversible cleanups — and only the ones you approve. Finds junk login items and launch agents, oversized regenerable caches, browser/Electron process bloat, and screen-compositing overload. Never touches personal data, never uses sudo, never force-kills anything. |

## Install

**As a plugin marketplace** (Claude Code):

```
/plugin marketplace add wowoweewa/skills-public
/plugin install tooling@skills-public
```

**Manually** — clone and symlink the skills you want:

```bash
git clone https://github.com/wowoweewa/skills-public.git
ln -s "$(pwd)/skills-public/tooling/skills/mac-system-doctor" ~/.claude/skills/mac-system-doctor
```

New sessions pick the skill up automatically. Trigger it by saying "run system doctor", "my Mac is slow", or "check my system health".

## Design rules every skill here follows

- **Diagnose first, read-only.** Reports rank causes by measured impact and state what was ruled out.
- **Consent before change.** Nothing is deleted, unloaded, or quit without explicit approval — one grouped question, every option showing its measured size.
- **Reversible fixes only.** Launch agents are moved to a backup folder, never deleted; caches are cleared with official tools; apps are quit gracefully or left alone.
- **Personal data is off-limits.** Photos, Messages, Mail, documents, browser profiles, and Keychain are never read or touched. No sudo, ever.

## License

[MIT](LICENSE)
