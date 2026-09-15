#!/usr/bin/env python3
"""Privacy scan: keeps personal data out of this public, pseudonymous repository.

Usage:
    python3 scripts/privacy_scan.py [--staged | --rev COMMIT] [--patterns PATH]

Default mode scans the working-tree content of every tracked file (git ls-files).
--staged scans the index (staged) content of every tracked file instead, so
"git add" followed by "--staged" checks exactly what the next commit records.
--rev COMMIT scans every file as recorded in that commit; the pre-push hook runs
it for each commit a push would publish. File names are scanned as well as
contents. Run it from anywhere inside the repository; paths are reported
relative to the repository root.

Output: one line per finding, "<file>:<line>: <pattern label>", where line 0
means the file name itself. The matched text is never printed. Exit 1 when
anything is found, 0 when clean, 2 when the scan could not run (not a git
repository, unreadable objects, broken private pattern).

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

HOME = os.path.expanduser("~")
DEFAULT_PATTERNS_PATH = os.path.join(HOME, ".config", "privacy-scan", "patterns.txt")

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

Pattern = tuple[str, "re.Pattern[str]"]
Entry = tuple[str, str, int, str]  # (mode, blob, stage, path)


def fail(message: str) -> None:
    """Stops the scan with exit code 2. Never pass pattern text or file content in here."""
    print(f"privacy_scan: error: {message}", file=sys.stderr)
    sys.exit(2)


def display_path(path: str) -> str:
    """Shows a path under the home folder as ~/..., so messages never carry the account name."""
    if path == HOME or path.startswith(HOME + os.sep):
        return "~" + path[len(HOME):]
    return path


def git(args: list[str], cwd: str, stdin: bytes = b"") -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, input=stdin, capture_output=True, check=False)


def repo_root() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        fail("not inside a git repository")
    return proc.stdout.strip()


def load_private_patterns(path: str) -> tuple[list[Pattern], str | None]:
    """Reads the private patterns file. Returns (patterns, warning-or-None).

    Messages built here name only the file path and a line number, never a line's text.
    """
    shown = display_path(path)
    try:
        with open(path, "rb") as handle:
            raw_lines = handle.read().decode("utf-8", errors="replace").split("\n")
    except OSError as exc:
        return [], (
            f"privacy_scan: warning: private patterns file not read ({shown}: {exc.strerror}); "
            "scanning with the generic patterns only"
        )
    patterns: list[Pattern] = []
    for number, raw in enumerate(raw_lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            regex = re.compile(line, re.IGNORECASE)
        except (re.error, OverflowError, RecursionError):
            fail(f"line {number} of {shown} is not a usable regular expression (its text is not shown)")
        if regex.search(""):
            fail(f"line {number} of {shown} matches empty text and would flag every line (its text is not shown)")
        patterns.append((f"private pattern (line {number})", regex))
    return patterns, None


def index_entries(root: str) -> list[Entry]:
    """Every index entry, in git's order. An unmerged path appears once per stage."""
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


def commit_entries(root: str, rev: str) -> list[Entry]:
    """Every file recorded in a commit, as (mode, blob, 0, path)."""
    proc = git(["ls-tree", "-r", "-z", "--full-tree", rev], root)
    if proc.returncode != 0:
        fail(f"git ls-tree failed for {rev}")
    entries = []
    for record in proc.stdout.split(b"\0"):
        if not record:
            continue
        meta, path = os.fsdecode(record).split("\t", 1)
        mode, _kind, blob = meta.split()
        entries.append((mode, blob, 0, path))
    return entries


def read_blobs(root: str, blobs: list[str]) -> dict[str, bytes]:
    """Reads every blob in one git process. Returns {blob sha: content}."""
    wanted = list(dict.fromkeys(blobs))
    if not wanted:
        return {}
    proc = git(["cat-file", "--batch"], root, stdin=("\n".join(wanted) + "\n").encode())
    if proc.returncode != 0:
        fail("git cat-file failed")
    contents: dict[str, bytes] = {}
    data, position = proc.stdout, 0
    for sha in wanted:
        header_end = data.index(b"\n", position)
        header = data[position:header_end].split()
        if len(header) != 3:  # "<sha> missing": the object is not in this repository
            fail(f"object {sha} is missing from the repository")
        size = int(header[2])
        position = header_end + 1
        contents[sha] = data[position:position + size]
        position += size + 1  # skip the newline git prints after each object
    return contents


def working_tree_content(root: str, path: str) -> bytes | None:
    """The working-tree bytes for a tracked path, or None when there is nothing on disk."""
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


def scan_name(path: str, patterns: list[Pattern]) -> int:
    """Prints "<path>:0: <label>" for every pattern the file name itself matches."""
    hits = 0
    for label, regex in patterns:
        if regex.search(path):
            print(f"{path}:0: {label}")
            hits += 1
    return hits


def scan_text(path: str, data: bytes, patterns: list[Pattern]) -> int:
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
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--staged",
        action="store_true",
        help="scan the index (staged) content of tracked files instead of the working tree",
    )
    source.add_argument(
        "--rev",
        metavar="COMMIT",
        help="scan every file as recorded in this commit instead of the working tree",
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

    # Submodule pointers (mode 160000) have no content of their own; everything else is a file
    # or a symlink whose stored text is the link target.
    entries = commit_entries(root, args.rev) if args.rev else index_entries(root)
    seen: set[str] = set()
    to_scan: list[Entry] = []
    for entry in entries:
        mode, _blob, stage, path = entry
        if path in seen or mode == "160000":
            continue
        seen.add(path)
        if args.staged and stage != 0:
            fail(f"{path} is unmerged; resolve it before scanning the index")
        to_scan.append(entry)

    from_objects = bool(args.staged or args.rev)
    blobs = read_blobs(root, [blob for _mode, blob, _stage, _path in to_scan]) if from_objects else {}

    hits = 0
    for _mode, blob, _stage, path in to_scan:
        hits += scan_name(path, patterns)
        data = blobs[blob] if from_objects else working_tree_content(root, path)
        if data is not None:
            hits += scan_text(path, data, patterns)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
