#!/usr/bin/env python3
"""Tests for scripts/privacy_scan.py and the pre-push hook that runs it.

Run:  python3 scripts/test_privacy_scan.py

Every test builds a throwaway git repository under a temporary directory and runs
the scanner as a subprocess with a hermetic environment (temporary HOME, no global
or system git config), so the developer's own settings and private patterns file
never take part.

Every fixture value is invented. Values that the scanner must flag are assembled
from fragments at run time (see joined()) so that this file itself passes the scan
that the repository runs on every tracked file.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPTS_DIR)
SCANNER = os.path.join(SCRIPTS_DIR, "privacy_scan.py")
HOOK = os.path.join(REPO_DIR, ".githooks", "pre-push")


def joined(*parts: str) -> str:
    """Builds a fixture from fragments none of which is a hit on its own."""
    return "".join(parts)


# (pattern label printed by the scanner, invented value that must trigger it)
GENERIC_FIXTURES = [
    ("email address", joined("nobody@", "example.com")),
    ("North American phone number", joined("(403) 555", "-0123")),
    ("North American phone number", joined("+1-403-555", "-0199")),
    ("North American phone number", joined("40355", "50142")),
    ("/Users/<name> path", joined("/Users", "/nobody/Documents/notes.md")),
    ("Google Sheet/Doc ID", joined("1AbCdEfGhIjKlMnOpQrStUv", "WxYz0123456789AbCdEfGhIj")),
    ("Notion 32-hex ID", joined("0123456789abcdef", "fedcba9876543210")),
    ("cal.com link", joined("https://cal", ".com/nobody/30min")),
    ("sk- secret key", joined("sk-", "invented0000000000000000")),
    ("GitHub token (ghp_)", joined("ghp_", "A" * 36)),
    ("Google API key (AIza)", joined("AIza", "B" * 35)),
    ("JSON Web Token (eyJhbGci)", joined("eyJhbGci", "OiJIUzI1NiJ9.e30.invented")),
]

# Ordinary text that must never be flagged.
BENIGN_LINES = [
    "Released on 2026-09-15 at 12:34:56, version 3.221.5472 of the tool.",
    "/plugin install tooling@skills-public",
    "commit e8c33ea0f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8 on branch main",
    "night/add-a-privacy-scan-that-blocks-personal-data-from-the-public-repo",
    "SOME_VERY_LONG_UPPER_CASE_CONSTANT_NAME_WITH_MORE_THAN_40_CHARACTERS",
    "Shared items live in /Users/Shared and in ~/Library/Caches.",
    "ask-anyone-about-this-slug-it-is-not-a-key",
    "Tokens start with the prefix sk- and are never committed.",
    "Total heap 3221225472 bytes, epoch 1757900000.",
]


class PrivacyScanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="privacy-scan-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        self.repo = os.path.join(self.tmp, "repo")
        os.makedirs(self.home)
        os.makedirs(self.repo)
        self.env = {
            "PATH": os.environ["PATH"],
            "HOME": self.home,
            "LC_ALL": "C.UTF-8",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@invalid",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@invalid",
        }
        self.git("init", "-q", "-b", "main")
        # A comment-only private patterns file: no private hits, no missing-file warning.
        self.quiet_patterns = self.write_patterns("# nothing private here\n")

    # -- helpers -----------------------------------------------------------------

    def git(self, *args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args], cwd=cwd or self.repo, env=self.env, capture_output=True, text=True, check=True
        )

    def write(self, name: str, content: str, add: bool = True) -> str:
        path = os.path.join(self.repo, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        if add:
            self.git("add", "--", name)
        return path

    def write_patterns(self, content: str) -> str:
        path = os.path.join(self.tmp, "patterns.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        return path

    def scan(self, *args: str, patterns: str | None = "quiet", cwd: str | None = None) -> subprocess.CompletedProcess:
        command = [sys.executable, SCANNER, *args]
        if patterns == "quiet":
            command += ["--patterns", self.quiet_patterns]
        elif patterns is not None:
            command += ["--patterns", patterns]
        return subprocess.run(command, cwd=cwd or self.repo, env=self.env, capture_output=True, text=True, check=False)

    # -- generic patterns --------------------------------------------------------

    def test_each_generic_pattern_is_reported_without_its_value(self) -> None:
        for label, value in GENERIC_FIXTURES:
            with self.subTest(label=label):
                self.write("notes.md", f"first line is clean\nsee {value} here\n")
                result = self.scan()
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stdout, f"notes.md:2: {label}\n")
                self.assertEqual(result.stderr, "")
                self.assertNotIn(value, result.stdout + result.stderr)

    def test_generic_patterns_ignore_ordinary_text(self) -> None:
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location("privacy_scan", SCANNER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for line in BENIGN_LINES:
            for label, regex in module.GENERIC_PATTERNS:
                with self.subTest(line=line, label=label):
                    self.assertIsNone(regex.search(line))

    def test_clean_repository_exits_zero_with_no_output(self) -> None:
        self.write("README.md", "\n".join(BENIGN_LINES) + "\n")
        self.write("docs/guide.md", "Plain text only.\n")
        result = self.scan()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def test_untracked_files_are_not_scanned(self) -> None:
        self.write("clean.md", "nothing here\n")
        self.write("scratch.md", f"contact {GENERIC_FIXTURES[0][1]}\n", add=False)
        result = self.scan()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_file_names_are_scanned_and_reported_as_line_zero(self) -> None:
        name = f"docs/{GENERIC_FIXTURES[0][1]}.md"
        self.write(name, "clean contents\n")
        result = self.scan()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, f"{name}:0: email address\n")

    def test_runs_from_a_subdirectory_and_reports_root_relative_paths(self) -> None:
        self.write("docs/guide.md", f"{GENERIC_FIXTURES[0][1]}\n")
        self.write("top.md", f"{GENERIC_FIXTURES[0][1]}\n")
        result = self.scan(cwd=os.path.join(self.repo, "docs"))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "docs/guide.md:1: email address\ntop.md:1: email address\n")

    # -- private patterns --------------------------------------------------------

    def test_private_pattern_from_temporary_file_is_reported_by_line_number_only(self) -> None:
        patterns = self.write_patterns("# the owner's invented code name\n\nzorblatt-nobody\n")
        self.write("notes.md", "clean line\nZORBLATT-Nobody was here\n")
        result = self.scan(patterns=patterns)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "notes.md:2: private pattern (line 3)\n")
        self.assertEqual(result.stderr, "")
        self.assertNotIn("zorblatt", (result.stdout + result.stderr).lower())

    def test_missing_private_file_warns_once_and_still_scans(self) -> None:
        missing = os.path.join(self.tmp, "does-not-exist", "patterns.txt")
        self.write("notes.md", "clean line\n")
        result = self.scan(patterns=missing)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stdout, "")
        self.assertEqual(len(result.stderr.splitlines()), 1)
        self.assertIn("warning", result.stderr)

        self.write("notes.md", f"{GENERIC_FIXTURES[0][1]}\n")
        result = self.scan(patterns=missing)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "notes.md:1: email address\n")
        self.assertEqual(len(result.stderr.splitlines()), 1)

    def test_default_private_file_location_is_under_home(self) -> None:
        self.write("notes.md", "clean line\n")
        result = self.scan(patterns=None)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(len(result.stderr.splitlines()), 1)
        self.assertIn("~/.config/privacy-scan/patterns.txt", result.stderr)
        self.assertNotIn(self.home, result.stderr, "the warning must not reveal the home folder")

        config_dir = os.path.join(self.home, ".config", "privacy-scan")
        os.makedirs(config_dir)
        with open(os.path.join(config_dir, "patterns.txt"), "w", encoding="utf-8") as handle:
            handle.write("zorblatt\n")
        self.write("notes.md", "Zorblatt again\n")
        result = self.scan(patterns=None)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "notes.md:1: private pattern (line 1)\n")
        self.assertEqual(result.stderr, "")

    def test_invalid_private_regex_stops_the_scan_without_showing_it(self) -> None:
        patterns = self.write_patterns("fine\n(unclosed-zorblatt\n")
        self.write("notes.md", "clean line\n")
        result = self.scan(patterns=patterns)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("line 2", result.stderr)
        self.assertNotIn("zorblatt", result.stderr)

        patterns = self.write_patterns("zorblatt{1000000000000}\n")
        result = self.scan(patterns=patterns)
        self.assertEqual(result.returncode, 2)
        self.assertIn("line 1", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("zorblatt", result.stderr)

    # -- staged mode -------------------------------------------------------------

    def test_staged_scans_the_index_not_the_working_tree(self) -> None:
        self.write("notes.md", "clean at first\n")
        self.git("commit", "-q", "-m", "initial")

        # Hit staged, working tree cleaned again without re-adding.
        self.write("notes.md", f"{GENERIC_FIXTURES[0][1]}\n")
        self.write("notes.md", "clean again\n", add=False)
        self.assertEqual(self.scan("--staged").stdout, "notes.md:1: email address\n")
        self.assertEqual(self.scan().returncode, 0)

        # Index clean, working tree carries the hit.
        self.write("notes.md", "clean in the index\n")
        self.write("notes.md", f"{GENERIC_FIXTURES[0][1]}\n", add=False)
        self.assertEqual(self.scan("--staged").returncode, 0)
        self.assertEqual(self.scan().stdout, "notes.md:1: email address\n")

    def test_rev_scans_a_commit_as_recorded(self) -> None:
        self.write("notes.md", "clean at first\n")
        self.git("commit", "-q", "-m", "clean")
        self.write("notes.md", f"{GENERIC_FIXTURES[0][1]}\n")
        self.git("commit", "-q", "-m", "leak")
        self.write("notes.md", "clean again\n")
        self.git("commit", "-q", "-m", "fix")
        self.assertEqual(self.scan("--rev", "HEAD~2").returncode, 0)
        self.assertEqual(self.scan("--rev", "HEAD~1").stdout, "notes.md:1: email address\n")
        self.assertEqual(self.scan("--rev", "HEAD").returncode, 0)
        self.assertEqual(self.scan().returncode, 0)
        self.assertEqual(self.scan("--rev", "no-such-commit").returncode, 2)

    # -- pre-push hook -----------------------------------------------------------

    def test_pre_push_hook_refuses_a_push_on_a_hit(self) -> None:
        self.assertTrue(os.access(HOOK, os.X_OK), "pre-push hook must be executable")
        for source, target in ((SCANNER, "scripts/privacy_scan.py"), (HOOK, ".githooks/pre-push")):
            destination = os.path.join(self.repo, target)
            os.makedirs(os.path.dirname(destination))
            shutil.copy(source, destination)  # copy() keeps the executable bit
        self.git("add", "-A")
        self.git("config", "core.hooksPath", ".githooks")
        remote = os.path.join(self.tmp, "remote.git")
        self.git("init", "-q", "--bare", "-b", "main", remote, cwd=self.tmp)
        self.git("remote", "add", "origin", remote)

        self.write("notes.md", "clean\n")
        self.git("commit", "-q", "-m", "clean")
        clean_sha = self.git("rev-parse", "HEAD").stdout.strip()
        pushed = subprocess.run(
            ["git", "push", "-q", "origin", "main"], cwd=self.repo, env=self.env, capture_output=True, text=True
        )
        self.assertEqual(pushed.returncode, 0, pushed.stderr)

        # The hit is committed on another branch and removed by the next commit; main stays
        # checked out and clean. A working-tree scan would pass this push.
        self.git("checkout", "-q", "-b", "leaky")
        self.write("notes.md", f"{GENERIC_FIXTURES[0][1]}\n")
        self.git("commit", "-q", "-m", "leak")
        leak_sha = self.git("rev-parse", "HEAD").stdout.strip()
        self.write("notes.md", "clean again\n")
        self.git("commit", "-q", "-m", "fix")
        self.git("checkout", "-q", "main")
        refused = subprocess.run(
            ["git", "push", "-q", "origin", "leaky"], cwd=self.repo, env=self.env, capture_output=True, text=True
        )
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("push refused", refused.stderr)
        self.assertIn(leak_sha, refused.stderr, "the message must name the offending commit")
        self.assertIn("notes.md:1: email address", refused.stdout + refused.stderr)
        self.assertNotIn(GENERIC_FIXTURES[0][1], refused.stdout + refused.stderr)
        remote_refs = self.git("for-each-ref", "--format=%(refname)", cwd=remote).stdout.split()
        self.assertEqual(remote_refs, ["refs/heads/main"], "the refused push must not reach the remote")
        self.assertEqual(self.git("rev-parse", "main", cwd=remote).stdout.strip(), clean_sha)

        # A clean branch built on the same history still pushes.
        self.git("checkout", "-q", "-b", "tidy")
        self.write("more.md", "still clean\n")
        self.git("commit", "-q", "-m", "tidy")
        pushed = subprocess.run(
            ["git", "push", "-q", "origin", "tidy"], cwd=self.repo, env=self.env, capture_output=True, text=True
        )
        self.assertEqual(pushed.returncode, 0, pushed.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
