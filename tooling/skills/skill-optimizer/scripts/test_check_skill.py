#!/usr/bin/env python3
"""Tests for check_skill.py. Standard library only.

Usage:
    python3 scripts/test_check_skill.py        run every test
    python3 scripts/test_check_skill.py -v     name each test as it runs
    python3 scripts/test_check_skill.py -h     show this text

Each test builds a throwaway skill folder, runs the checker on it and reads
the findings. A change to check_skill.py starts with a failing test here.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SKILL_DIR = SCRIPTS.parent
CHECKER = SCRIPTS / "check_skill.py"
sys.path.insert(0, str(SCRIPTS))
sys.dont_write_bytecode = True  # keep a __pycache__ folder out of the skill

import check_skill as cs  # noqa: E402

LIMIT = 1024  # the frontmatter description field's own limit, the only hard cap on length

TRIGGERS = '"sort my files", "tidy this folder", "rename these files", "clean up downloads", "organize my desktop"'
GOOD_DESC = (
    f"Use when the user says {TRIGGERS}. Sorts files into dated folders. "
    "Does NOT trigger on backups (use backup-runner)."
)
GOOD_BODY = """# Demo Skill

Sorts files into dated folders.

## Steps

1. List the folder.
2. Move each file into a folder named for its month.

## Output Format

One line per file moved.

## Gotchas

- **Hidden files** are left where they are.

## Constraints

- Never delete a file.
"""


def skill_text(description: str = GOOD_DESC, body: str = GOOD_BODY) -> str:
    return f"---\nname: demo-skill\ndescription: {description}\n---\n\n{body}"


def desc_of_length(n: int) -> str:
    """A description that breaks no rule except, possibly, the length limit."""
    pad = n - len(GOOD_DESC) - 1
    assert pad >= 1, "requested length is shorter than the base description"
    desc = f"{GOOD_DESC} {'a' * pad}"
    assert len(desc) == n
    return desc


class CheckerCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "demo-skill"
        self.root.mkdir()
        cs.findings.clear()

    def tearDown(self) -> None:
        cs.findings.clear()
        self._tmp.cleanup()

    def write(self, rel: str, text: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def run_checker(self, skill_dir: Path | None = None) -> list[tuple[str, str, int, str]]:
        cs.findings.clear()
        cs.check_skill(skill_dir or self.root)
        return list(cs.findings)

    def fails(self, skill_dir: Path | None = None) -> list[str]:
        """FAIL findings as 'file name: message' strings."""
        return [f"{Path(path).name}: {msg}" for level, path, _line, msg in self.run_checker(skill_dir) if level == "FAIL"]

    def assert_fail(self, fragment: str) -> None:
        found = self.fails()
        self.assertTrue(any(fragment in f for f in found), f"no FAIL containing {fragment!r}; got {found}")

    def assert_no_fail(self, fragment: str = "") -> None:
        found = [f for f in self.fails() if fragment in f]
        self.assertEqual(found, [], f"unexpected FAIL: {found}")


class DescriptionLimit(CheckerCase):
    """No fixed length below the frontmatter field's limit (the 400 cap was withdrawn)."""

    def test_limit_constant_is_the_frontmatter_limit(self) -> None:
        self.assertEqual(cs.DESC_MAX, 1024)
        self.assertEqual(LIMIT, 1024)

    def test_description_of_401_characters_passes(self) -> None:
        self.write("SKILL.md", skill_text(desc_of_length(401)))
        self.assert_no_fail()

    def test_description_at_the_limit_passes(self) -> None:
        self.write("SKILL.md", skill_text(desc_of_length(LIMIT)))
        self.assert_no_fail()

    def test_description_one_over_the_limit_fails(self) -> None:
        self.write("SKILL.md", skill_text(desc_of_length(LIMIT + 1)))
        self.assert_fail("description is 1025 characters")

    def test_failure_message_names_the_frontmatter_limit(self) -> None:
        self.write("SKILL.md", skill_text(desc_of_length(LIMIT + 1)))
        messages = [f for f in self.fails() if "characters" in f]
        self.assertEqual(len(messages), 1, messages)
        self.assertIn("1024", messages[0])
        self.assertIn("frontmatter", messages[0])
        self.assertNotIn("400", messages[0])


class SiblingRouting(CheckerCase):
    def test_not_for_clause_counts_as_naming_a_sibling(self) -> None:
        desc = f"Use when the user says {TRIGGERS}. Sorts files into dated folders. Not for backups (backup-runner)."
        self.write("SKILL.md", skill_text(desc))
        warns = [msg for level, _p, _l, msg in self.run_checker() if level == "WARN" and "names no sibling" in msg]
        self.assertEqual(warns, [])


class PinnedModelVersion(CheckerCase):
    PINNED = "Run 12 used Opus 4.1 for the critic and passed.\n"

    def test_lessons_md_may_name_a_model_version(self) -> None:
        self.write("SKILL.md", skill_text())
        self.write("LESSONS.md", "# Lessons\n\n" + self.PINNED)
        self.assert_no_fail()

    def test_lessons_md_in_a_subfolder_is_exempt_too(self) -> None:
        self.write("SKILL.md", skill_text())
        self.write("references/LESSONS.md", "# Lessons\n\n- claude-sonnet-4 ran the fetch stage.\n")
        self.assert_no_fail()

    def test_skill_md_may_not_name_a_model_version(self) -> None:
        self.write("SKILL.md", skill_text(body=GOOD_BODY + "\n" + self.PINNED))
        self.assert_fail("SKILL.md: pinned model version")

    def test_other_files_may_not_name_a_model_version(self) -> None:
        self.write("SKILL.md", skill_text())
        self.write("references/notes.md", "# Notes\n\n" + self.PINNED)
        self.write("lessons-learned.md", "# Lessons learned\n\n" + self.PINNED)
        found = self.fails()
        self.assertTrue(any(f.startswith("notes.md: pinned model version") for f in found), found)
        self.assertTrue(any(f.startswith("lessons-learned.md: pinned model version") for f in found), found)

    def test_lessons_md_still_obeys_the_other_text_rules(self) -> None:
        self.write("SKILL.md", skill_text())
        self.write("LESSONS.md", "# Lessons\n\nStudies show shorter is better.\n")
        self.assert_fail("LESSONS.md: evidence phrase")


class ExistingRules(CheckerCase):
    def test_clean_skill_has_no_fail(self) -> None:
        self.write("SKILL.md", skill_text())
        self.assert_no_fail()

    def test_four_quoted_triggers_fail(self) -> None:
        four = 'Use when the user says "sort my files", "tidy this folder", "rename these files", "clean up downloads". Sorts files. Does NOT trigger on backups (use backup-runner).'
        self.write("SKILL.md", skill_text(four))
        self.assert_fail("carries 4 quoted trigger phrases; minimum is 5")

    def test_five_quoted_triggers_pass(self) -> None:
        self.write("SKILL.md", skill_text())
        self.assert_no_fail("quoted trigger phrases")

    def test_missing_use_when_fails(self) -> None:
        desc = f"Sorts files into dated folders. Triggers on {TRIGGERS}."
        self.write("SKILL.md", skill_text(desc))
        self.assert_fail('no "Use when" clause')

    def test_501_lines_fail_and_500_pass(self) -> None:
        base = skill_text()
        filler = "- one more line\n"
        short = base + filler * (500 - len(base.splitlines()))
        self.assertEqual(len(short.splitlines()), 500)
        self.write("SKILL.md", short)
        self.assert_no_fail("lines; cap is 500")
        self.write("SKILL.md", short + filler)
        self.assert_fail("SKILL.md is 501 lines; cap is 500")

    def test_missing_section_fails_and_names_it(self) -> None:
        body = GOOD_BODY.replace("## Gotchas\n\n- **Hidden files** are left where they are.\n\n", "")
        self.assertNotIn("Gotchas", body)
        self.write("SKILL.md", skill_text(body=body))
        self.assert_fail("missing required section: gotchas")
        self.assert_no_fail("missing required section: constraints")

    def test_missing_skill_md_fails(self) -> None:
        self.assert_fail("no SKILL.md")


class CommandLine(CheckerCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(CHECKER), *args], capture_output=True, text=True, timeout=60)

    def test_exit_0_and_pass_line_on_a_clean_skill(self) -> None:
        self.write("SKILL.md", skill_text())
        r = self.run_cli(str(self.root))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("Result: PASS - 0 FAIL", r.stdout)

    def test_exit_1_on_a_long_description(self) -> None:
        self.write("SKILL.md", skill_text(desc_of_length(LIMIT + 1)))
        r = self.run_cli(str(self.root))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn(f"FAIL {self.root.resolve() / 'SKILL.md'}:1 - description is {LIMIT + 1} characters", r.stdout)

    def test_help_exits_0(self) -> None:
        r = self.run_cli("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Usage:", r.stdout)


class OwnSkill(CheckerCase):
    """skill-optimizer obeys the rules it sets. Path checks that depend on where
    the skill is installed are left to a direct run of check_skill.py."""

    def setUp(self) -> None:
        super().setUp()
        self.own_md = SKILL_DIR / "SKILL.md"
        self.own_text = self.own_md.read_text(encoding="utf-8")

    def own_fails(self) -> list[str]:
        fields, body_start = cs.split_frontmatter(self.own_text)
        cs.findings.clear()
        cs.check_description(self.own_md, fields)
        cs.check_body(self.own_md, self.own_text, body_start)
        cs.check_text_rules(self.own_md, self.own_text)
        return [msg for level, _path, _line, msg in cs.findings if level == "FAIL"]

    def test_own_description_fits_the_limit(self) -> None:
        fields, _ = cs.split_frontmatter(self.own_text)
        self.assertLessEqual(len(fields["description"]), LIMIT)

    def test_own_skill_md_has_no_fail(self) -> None:
        self.assertEqual(self.own_fails(), [])

    def test_own_skill_md_states_no_400_cap(self) -> None:
        for old in ("400 characters", "400-character", "under 400", "at 400"):
            self.assertNotIn(old, self.own_text)
        self.assertIn("1,024 characters", self.own_text)
        self.assertIn("no fixed length", self.own_text.lower())

    def test_output_format_template_passes_the_checker(self) -> None:
        start = self.own_text.index("````markdown\n") + len("````markdown\n")
        end = self.own_text.index("\n````", start)
        template = self.own_text[start:end] + "\n"
        self.assertTrue(template.startswith("---\nname:"), template[:40])
        self.write("SKILL.md", template)
        self.assert_no_fail()

    def test_output_format_template_description_has_triggers_situation_and_routing_in_order(self) -> None:
        start = self.own_text.index("````markdown\n")
        line = next(l for l in self.own_text[start:].splitlines() if l.startswith("description:"))
        desc = line[len("description:"):].strip()
        self.assertTrue(desc.startswith("Use when the user says "), desc)
        self.assertGreaterEqual(len(cs.QUOTED.findall(desc)), 5)
        self.assertLess(desc.index("what the skill does"), desc.index("Does NOT trigger on"))
        self.assertIn("(use <", desc)


if __name__ == "__main__":
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(__doc__.strip())
        sys.exit(0)
    unittest.main()
