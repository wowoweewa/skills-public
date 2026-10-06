#!/usr/bin/env python3
"""Mechanical checks for a skill directory (SKILL.md plus bundled files).

Usage:
    python3 check_skill.py <skill-dir> [<skill-dir> ...]

Prints one line per finding:  FAIL <file>:<line> - <message>   or   WARN ...
Exit code 1 when any FAIL is present, else 0.

FAIL means fix before shipping. WARN means a judgment call: resolve it or say
in one line why it stays. Every check enforces a rule that skill-optimizer's
SKILL.md already states; this script exists because rules without a check get
violated silently.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REQUIRED_SECTIONS = {
    "steps": re.compile(r"^##\s+(Steps|Process|Workflow)\b", re.I | re.M),
    "output format": re.compile(r"^##\s+Output Format\b", re.I | re.M),
    "gotchas": re.compile(r"^##\s+Gotchas\b", re.I | re.M),
    "constraints": re.compile(r"^##\s+Constraints\b", re.I | re.M),
}

# Description rules
# Why 400: Claude Code lists every skill's name and description in each session
# inside one budget, 1% of the context window (measured at 30,000 characters on
# a 1M-token model), and when the listing overflows it drops whole descriptions,
# least-invoked skills first (code.claude.com/docs/en/skills, "Skill
# descriptions are cut short"). Measured October 2026: 42 descriptions averaging
# 842 characters under the old cap of 1024 left 21 skills listed by name only;
# at 400 each the same 42 need about 18,300 characters, inside the roughly
# 19,500 left after built-in entries once unused plugin sources are off.
DESC_MAX = 400
MIN_TRIGGERS = 5
USE_WHEN_LEAD_CHARS = 250  # "Use when" should appear this early; later = tail gets truncated first
FIRST_SECOND_PERSON = re.compile(r"\b(I can|I will|I help|I'll|you can use|you should|your skill)\b", re.I)
QUOTED = re.compile(r'"[^"\n]{3,}"')

# Body rules
PINNED_MODEL_EXEMPT = {"LESSONS.md"}  # a run ledger must record which model version ran
PLACEHOLDER_PATH = re.compile(r"<this skill's directory>|<this skill>/|<skill[- ]dir(?:ectory)?>/", re.I)  # a bare <skill-dir> argument is fine; a path prefix is not
PINNED_MODEL = re.compile(r"claude-(?:opus|sonnet|haiku|fable|mythos)-\d|\b(?:Opus|Sonnet|Haiku|Fable)\s+\d(?:\.\d)?\b")
EVIDENCE_PHRASE = re.compile(r"\b(studies show|research shows|data shows|studies have shown|research has shown|it is proven)\b", re.I)
PERCENT = re.compile(r"(?<![\w.])\d{1,3}(?:\.\d+)?%")
SOURCE_HINT = re.compile(r"https?://|\b(?:19|20)\d{2}\b|\bobserved\b|\bsource\b|\bper\s+[A-Z]|\(inferred\)|\(confirmed\)|\bunverified\b|\bfolklore\b|\bban(?:ned)?\b|\bnot\s+verif", re.I)
BROWSER_OPEN = re.compile(r"--open\b|\bopen -a\b|\bopen https?://")
LOCAL_REF = re.compile(r"(?<![\w/~.])(references|scripts|assets|evals)/[\w\-.]+(?:/[\w\-.]+)*")
HOME_PATH = re.compile(r"~/(?:claude-skills|\.claude/skills|\.claude/agents|Projects)/[\w\-./]+")
HEADING = re.compile(r"^#{1,6}\s+(.*)$")
TOC_HEADING = re.compile(r"^#{1,6}\s+.*contents.*$", re.I)
TOC_ITEM = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(.*)$")
MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")

findings: list[tuple[str, str, int, str]] = []


def add(level: str, path: Path, line: int, msg: str) -> None:
    findings.append((level, str(path), line, msg))


def split_frontmatter(text: str) -> tuple[dict[str, str], int]:
    """Return (fields, body_start_line). Fields hold the raw single-line values."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, 0
    fields: dict[str, str] = {}
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return fields, i + 1
        m = re.match(r"^([\w-]+):\s*(.*)$", lines[i])
        if m:
            fields[m.group(1)] = m.group(2).strip()
    return fields, 0


def check_description(skill_md: Path, fields: dict[str, str]) -> None:
    desc = fields.get("description", "")
    if not fields.get("name"):
        add("FAIL", skill_md, 1, "frontmatter has no name")
    if not desc:
        add("FAIL", skill_md, 1, "frontmatter has no description")
        return
    if len(desc) > DESC_MAX:
        add(
            "FAIL",
            skill_md,
            1,
            f"description is {len(desc)} characters; cap is {DESC_MAX} (every description shares one listing budget, "
            "1% of the context window; over budget, the least-invoked skills are listed by name only and cannot be picked)",
        )
    if "Use when" not in desc:
        add("FAIL", skill_md, 1, 'description has no "Use when" clause')
    elif desc.find("Use when") > USE_WHEN_LEAD_CHARS:
        add("WARN", skill_md, 1, f'"Use when" appears after character {desc.find("Use when")}; lead with it')
    n = len(QUOTED.findall(desc))
    if n < MIN_TRIGGERS:
        add("FAIL", skill_md, 1, f"description carries {n} quoted trigger phrases; minimum is {MIN_TRIGGERS}")
    m = FIRST_SECOND_PERSON.search(QUOTED.sub("", desc))
    if m:
        add("FAIL", skill_md, 1, f'description uses first/second person ("{m.group(0)}"); third person only')
    if not re.search(r"does not trigger|does NOT trigger|defers? .* to|routes? .* to|use \w[\w-]* (?:for|instead)", desc, re.I):
        add("WARN", skill_md, 1, "description names no sibling for adjacent requests (add 'Does NOT trigger on X (use Y)')")


def check_body(skill_md: Path, text: str, body_start: int) -> None:
    lines = text.splitlines()
    if len(lines) > 500:
        add("FAIL", skill_md, len(lines), f"SKILL.md is {len(lines)} lines; cap is 500 (move depth to references/)")
    for label, rx in REQUIRED_SECTIONS.items():
        if not rx.search(text):
            add("FAIL", skill_md, 1, f"missing required section: {label}")
    seen: dict[str, int] = {}
    for i, line in enumerate(lines, 1):
        if i <= body_start:
            continue
        if PLACEHOLDER_PATH.search(line):
            add("FAIL", skill_md, i, "placeholder path; write the literal path the library convention uses")
        if BROWSER_OPEN.search(line):
            add("WARN", skill_md, i, "command opens a browser; render, give the path, and ask first")
        norm = re.sub(r"\s+", " ", line.strip().lower())
        if len(norm) > 60 and not norm.startswith(("|", "#", "```", "-", "*")):
            if norm in seen:
                add("WARN", skill_md, i, f"repeats line {seen[norm]} verbatim; say it once")
            else:
                seen[norm] = i


def check_text_rules(md: Path, text: str) -> None:
    for i, line in enumerate(text.splitlines(), 1):
        if md.name not in PINNED_MODEL_EXEMPT and PINNED_MODEL.search(line):
            add("FAIL", md, i, "pinned model version; use a tier alias (opus / sonnet / haiku)")
        if EVIDENCE_PHRASE.search(line) and not SOURCE_HINT.search(line):
            add("FAIL", md, i, 'evidence phrase ("studies show" or similar) with no source on the line')
        elif PERCENT.search(line) and not SOURCE_HINT.search(line) and not line.lstrip().startswith(("|", "```")):
            add("WARN", md, i, "percentage with no source on the line; name the source or delete the number")


def check_references(skill_dir: Path, md: Path, text: str) -> None:
    for i, line in enumerate(text.splitlines(), 1):
        for m in LOCAL_REF.finditer(line):
            token = m.group(0)
            if "<" in token or ">" in token or "*" in token:
                continue
            last = token.rsplit("/", 1)[-1]
            if "." not in last:
                continue  # a directory mention, not a file
            token = token.rstrip(".,;:)")
            if not (skill_dir / token).exists():
                add("FAIL", md, i, f"referenced file does not exist in this skill: {token} (if it belongs to another skill, write the full ~/claude-skills path)")
        for m in HOME_PATH.finditer(line):
            token = m.group(0).rstrip(".,;:)")
            if "<" in line[m.start():m.end() + 1]:
                continue
            p = Path(os.path.expanduser(token))
            if not p.exists():
                add("FAIL", md, i, f"referenced path does not exist: {token}")


STOPWORDS = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "by", "for", "with", "what", "when", "how", "is", "are", "vs", "not", "do", "its", "it"}


def slug(heading: str) -> str:
    h = re.sub(r"[^\w\s-]", "", heading.lower())
    return re.sub(r"\s+", "-", h.strip())


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS and len(w) > 1}


def check_toc(md: Path, text: str) -> None:
    """Every table-of-contents entry must land on a heading. Linked entries match by
    anchor against heading slugs; plain entries match by word overlap, so a short
    heading ("Verified GOATs") satisfies a descriptive entry ("The verified GOATs and
    what each contributed")."""
    lines = text.splitlines()
    if len(lines) <= 100:
        return
    headings = [HEADING.match(l).group(1).strip() for l in lines if HEADING.match(l)]
    slugs = [slug(re.sub(r"^\d+[.)]?\s*", "", h)) for h in headings]
    explicit_anchors = set(re.findall(r'id="([^"]+)"', text))
    toc_at = next((i for i, l in enumerate(lines) if TOC_HEADING.match(l)), None)
    if toc_at is None:
        if md.name != "SKILL.md":
            add("WARN", md, 1, f"{len(lines)}-line reference with no table of contents")
        return
    for j in range(toc_at + 1, len(lines)):
        l = lines[j]
        if HEADING.match(l) or l.strip() == "---":
            break
        m = TOC_ITEM.match(l)
        if not m:
            continue
        raw = m.group(1).strip()
        link = re.search(r"\[([^\]]+)\]\(#([^)]+)\)", raw)
        if link:
            anchor = link.group(2).lower()
            if anchor in explicit_anchors or any(anchor == sl or anchor in sl or (sl and sl in anchor) for sl in slugs):
                continue
            label = link.group(1)
        else:
            label = raw
        label = re.sub(r"^\d+[.)]?\s*", "", label).strip("*_` ")
        iw = words(label)
        if not iw:
            continue
        ok = False
        for h in headings:
            hw = words(re.sub(r"^\d+[.)]?\s*", "", h))
            if not hw:
                continue
            overlap = len(iw & hw) / min(len(iw), len(hw))
            if overlap >= 0.6:
                ok = True
                break
        if not ok:
            add("FAIL", md, j + 1, f'table of contents promises "{label}" but no heading carries it')


def check_scripts(skill_dir: Path) -> None:
    scripts = sorted((skill_dir / "scripts").glob("*.py")) if (skill_dir / "scripts").is_dir() else []
    for s in scripts:
        try:
            r = subprocess.run([sys.executable, str(s), "--help"], capture_output=True, text=True, timeout=20, cwd=str(skill_dir))
            if r.returncode != 0:
                add("FAIL", s, 1, f"`python3 {s.name} --help` exits {r.returncode}; scripts must document themselves")
        except subprocess.TimeoutExpired:
            add("FAIL", s, 1, f"`python3 {s.name} --help` hung for 20s")


def check_skill(skill_dir: Path) -> None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        add("FAIL", skill_dir, 0, "no SKILL.md")
        return
    text = skill_md.read_text(encoding="utf-8")
    fields, body_start = split_frontmatter(text)
    if body_start == 0:
        add("FAIL", skill_md, 1, "no YAML frontmatter block")
    check_description(skill_md, fields)
    check_body(skill_md, text, body_start)
    for md in sorted(skill_dir.rglob("*.md")):
        if "__pycache__" in md.parts or "workspace" in md.parts:
            continue
        t = md.read_text(encoding="utf-8", errors="replace")
        check_text_rules(md, t)
        check_references(skill_dir, md, t)
        check_toc(md, t)
    check_scripts(skill_dir)


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    for arg in argv:
        d = Path(os.path.expanduser(arg)).resolve()
        if not d.is_dir():
            add("FAIL", d, 0, "not a directory")
            continue
        check_skill(d)
    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]
    for level, path, line, msg in findings:
        print(f"{level} {path}:{line} - {msg}")
    print(f"\nResult: {'FAIL' if fails else 'PASS'} - {len(fails)} FAIL, {len(warns)} WARN")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
