#!/usr/bin/env python3
"""Privacy scan: keeps personal data out of this public, pseudonymous repository.

Usage:
    python3 scripts/privacy_scan.py [--staged] [--patterns PATH]

Default mode scans the working-tree content of every tracked file (git ls-files).
--staged scans the index (staged) content of every tracked file instead, so
"git add" followed by "--staged" checks exactly what the next commit records.
Run it from anywhere inside the repository; paths are reported relative to the
repository root.

Output: one line per finding, "<file>:<line>: <pattern label>". The matched text
is never printed. Exit 1 when anything is found, 0 when clean, 2 when the scan
could not run (not a git repository, unreadable index, broken private pattern).

Generic patterns are built in below. Private patterns (the owner's names,
addresses, and anything else specific to them) live outside the repository in
~/.config/privacy-scan/patterns.txt (override with --patterns): one
case-insensitive regular expression per line, blank lines and "#" comments
ignored, matched against one line of text at a time. That file's contents are
never echoed, not even when a line is not a valid regular expression. When the
file is missing or unreadable the scan still runs with the generic patterns and
prints one warning line on stderr.

Standard library only.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

DEFAULT_PATTERNS_PATH = os.path.join(
    os.path.expanduser("~"), ".config", "privacy-scan", "patterns.txt"
)

# The character set of Google Drive IDs, JSON Web Tokens and most API keys.
B64 = r"[A-Za-z0-9_-]"

GENERIC_PATTERNS = [
    ("email address", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    # North American Numbering Plan shape: optional +1, then area code and exchange
    # that start with 2-9, separated by space, dot, dash or nothing. The lookarounds
    # keep it out of longer digit runs, hashes and identifiers.
    (
        "North American phone number",
        re.compile(
            r"(?<![\w-])(?:\+?1[ .-]?)?\(?[2-9]\d{2}\)?[ .-]?[2-9]\d{2}[ .-]?\d{4}(?![\w-])"
        ),
    ),
    # A home-folder path names the account. /Users/Shared is a system folder, not a person.
    ("/Users/<name> path", re.compile(r"/Users/(?!Shared(?![\w.-]))[\w.-]+")),
    # Google Sheet and Doc IDs are 44 random characters. A run of 40 or more that mixes
    # upper case, lower case and digits is treated as one; pure hex (git SHAs, checksums)
    # and word slugs (kebab-case or snake_case names) do not qualify.
    (
        "Google Sheet/Doc ID",
        re.compile(
            rf"(?<!{B64})(?={B64}{{40,}}(?!{B64}))(?={B64}*[A-Z])(?={B64}*[a-z])(?={B64}*\d){B64}+"
        ),
    ),
    ("Notion 32-hex ID", re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{32}(?![0-9A-Fa-f])")),
    ("cal.com link", re.compile(r"\bcal\.com/", re.IGNORECASE)),
    ("sk- secret key", re.compile(rf"\bsk-{B64}{{16,}}")),
    (
        "GitHub token (ghp_)",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})"),
    ),
    ("Google API key (AIza)", re.compile(rf"(?<!{B64})AIza{B64}{{35}}")),
    ("JSON Web Token (eyJhbGci)", re.compile(rf"\beyJhbGci{B64}{{10,}}")),
]


def fail(message: str) -> None:
    """Stops the scan with exit code 2. Never pass pattern text or file content in here."""
    print(f"privacy_scan: error: {message}", file=sys.stderr)
    sys.exit(2)


def git(args: list[str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=False)


def repo_root() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        fail("not inside a git repository")
    return proc.stdout.strip()


def load_private_patterns(path: str) -> tuple[list[tuple[str, re.Pattern]], str | None]:
    """Reads the private patterns file. Returns (patterns, warning-or-None).

    Messages built here name only the file path and a line number, never a line's text.
    """
    try:
        with open(path, "rb") as handle:
            raw_lines = handle.read().decode("utf-8", errors="replace").split("\n")
    except OSError as exc:
        return [], (
            f"privacy_scan: warning: private patterns file not read ({path}: {exc.strerror}); "
            "scanning with the generic patterns only"
        )
    patterns = []
    for number, raw in enumerate(raw_lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            regex = re.compile(line, re.IGNORECASE)
        except re.error:
            fail(f"line {number} of {path} is not a valid regular expression (its text is not shown)")
        if regex.search(""):
            fail(f"line {number} of {path} matches empty text and would flag every line (its text is not shown)")
        patterns.append((f"private pattern (line {number})", regex))
    return patterns, None


def tracked_entries(root: str) -> list[tuple[str, str, int, str]]:
    """Every index entry as (mode, blob, stage, path), in git's order."""
    proc = git(["ls-files", "--stage", "-z"], root)
    if proc.returncode != 0:
        fail("git ls-files failed")
    entries = []
    for record in proc.stdout.split(b"\0"):
        if not record:
            continue
        meta, path = os.fsdecode(record).split("\t", 1)
        mode, blob, stage = meta.split()
        entries.append((mode, blob, int(stage), path))
    return entries


def load_content(root: str, mode: str, blob: str, path: str, staged: bool) -> bytes | None:
    """The bytes to scan for one entry, or None when the entry has nothing to scan."""
    if mode == "160000":  # submodule pointer: no content of its own
        return None
    if staged:
        proc = git(["cat-file", "blob", blob], root)
        if proc.returncode != 0:
            fail(f"could not read the staged content of {path}")
        return proc.stdout
    full = os.path.join(root, path)
    if os.path.islink(full):
        # git stores the link target text, so that is what a push would publish.
        return os.fsencode(os.readlink(full))
    try:
        with open(full, "rb") as handle:
            return handle.read()
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError):
        return None  # deleted in the working tree: nothing to scan here
    except OSError as exc:
        fail(f"could not read {path}: {exc.strerror}")
        return None


def scan_text(path: str, data: bytes, patterns: list[tuple[str, re.Pattern]]) -> int:
    """Prints one "<path>:<line>: <label>" per (line, pattern) hit. Returns the hit count."""
    hits = 0
    text = data.decode("utf-8", errors="replace")
    for number, line in enumerate(text.split("\n"), 1):
        for label, regex in patterns:
            if regex.search(line):
                print(f"{path}:{number}: {label}")
                hits += 1
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan tracked files for personal data.")
    parser.add_argument(
        "--staged",
        action="store_true",
        help="scan the index (staged) content of tracked files instead of the working tree",
    )
    parser.add_argument(
        "--patterns",
        default=DEFAULT_PATTERNS_PATH,
        metavar="PATH",
        help="private patterns file (default: ~/.config/privacy-scan/patterns.txt)",
    )
    args = parser.parse_args(argv)

    root = repo_root()
    private_patterns, warning = load_private_patterns(args.patterns)
    if warning:
        print(warning, file=sys.stderr)
    patterns = GENERIC_PATTERNS + private_patterns

    hits = 0
    seen: set[str] = set()
    for mode, blob, stage, path in tracked_entries(root):
        if path in seen:  # an unmerged path lists one entry per stage
            continue
        seen.add(path)
        if args.staged and stage != 0:
            fail(f"{path} is unmerged; resolve it before scanning the index")
        data = load_content(root, mode, blob, path, args.staged)
        if data is None:
            continue
        hits += scan_text(path, data, patterns)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
