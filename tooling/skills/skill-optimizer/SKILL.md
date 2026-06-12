---
name: skill-optimizer
description: Quality-assurance companion to `skill-creator` — load this skill alongside `skill-creator` whenever the user is authoring, editing, or improving any SKILL.md file. Make sure to use this skill even when skill-creator is the only one explicitly named, because it adds opinionated quality criteria that skill-creator deliberately leaves open. Use when the user says "create a skill", "build a new skill", "make a skill", "write a skill", "edit this skill", "improve this skill", "rewrite this skill", "fix this skill description", "the skill isn't triggering", or any request involving authoring or modifying a SKILL.md file. Adds: third-person descriptions, ≥5 trigger phrases, gotcha rigor, freedom-matching, 5 Skill Killers check, verification checklist.
---

# Skill Optimizer

Quality-assurance layer for SKILL.md authoring. Loads alongside `skill-creator` (which handles file scaffolding and validation) so the skill that ships triggers reliably, captures real failure patterns, and earns every token it spends.

## When this fires vs `skill-creator`

| Skill | Owns |
|---|---|
| `skill-creator` (Anthropic) | Mechanics — folder scaffolding, frontmatter validation, plugin registration, evals workflow |
| `skill-optimizer` (this) | Quality — description triggering, naming, conciseness, gotcha rigor, anti-patterns |

Use both: `skill-creator` for the scaffolding and iteration loop, this skill for content quality.

## The 5 Skill Killers — quick check

The five most common reasons skills fail. Avoid these and most quality issues take care of themselves.

| # | Killer | Fix |
|---|---|---|
| 1 | **Description doesn't trigger properly** — too vague, too narrow, or wrong person | Specific, loud, third-person, `Use when...` format |
| 2 | **Over-defining the process** — railroading instead of guiding | Set degrees of freedom — tight for fragile, loose for creative |
| 3 | **Stating the obvious** — wasting tokens on what Claude already knows | Challenge every paragraph: "Does Claude really need this?" |
| 4 | **Missing gotcha section** — not capturing failure patterns | Document every failure you've seen. This IS the skill's value |
| 5 | **Monolithic blob** — everything in one file | SKILL.md under 500 lines. Move references to separate files |

The Process section below is the detailed how-to for avoiding each killer.

## Process

### 1. Name — three forms acceptable, pick one per library

Three forms work — choose one and stay consistent:

- **Noun phrase** (`pdf-processing`, `skill-optimizer`) — preferred
- **Gerund** (`processing-pdfs`) — acceptable
- **Action-oriented** (`process-pdfs`) — acceptable

Format rules:

- lowercase letters
- numbers
- hyphens only
- max 64 characters

Cannot contain reserved words (`anthropic`, `claude`). Avoid vague names or redundant `-skill` suffixes.

Whatever form a library already standardizes on, keep it — don't introduce a second naming form into an existing collection.

### 2. Description — write as a trigger, not a summary

The description is the **most critical line** in the skill — it's the primary mechanism Claude uses to decide whether to fire the skill. Write it for the model asking *"when should I fire?"*

- **Third person only.** "Processes Excel files and generates reports." Never "I can help..." or "You can use this..." — first/second person breaks discovery.
- **Lead with `Use when the user says "..."`** followed by **≥5 literal trigger phrases** users would actually type, including casual phrasings, abbreviations, and how real prompts come in.
- **Be LOUD, not quiet.** Claude tends to under-trigger skills. End with one concrete sentence on what the skill *does*, not what it *is*.
- **Stay under 1024 characters.** The frontmatter `description` field caps at 1024 — loudness past the cap gets truncated, and the truncated tail is usually the trigger phrases.
- **Both what AND when.** All "when to use" info goes in the description, never the body.

✅ `Processes Excel files, creates pivot tables, generates charts. Use when the user says "analyze this xlsx", "make a pivot table", "chart this spreadsheet", or works with .xlsx/.xlsm files.`

❌ `A neuroscience-informed designer that builds courses...` — reads as a tagline; won't trigger reliably.

### 3. Body — required sections in this order

1. **Steps / Process** — numbered, concrete actions. Match freedom level to task fragility (see step 4).
2. **Output Format** — literal template. Show, don't describe.
3. **Gotchas** — every failure pattern observed. The highest-signal section; this IS the skill's value.
4. **Constraints** — what NOT to do. Sharp rules specific to THIS skill, not general behavior.

Optional, include only when relevant:
- **Context Required** — files the skill needs to read at session start (full paths, since the agent doesn't remember prior sessions).

### 4. Match instruction tightness to task fragility

"Freedom" (Anthropic's term) = how much latitude the skill gives the model in *how* to execute. High freedom = prose, model picks the approach. Low freedom = exact steps, model follows the sequence.

| Freedom | Use when | Example |
|---|---|---|
| **High** (prose instructions) | Multiple approaches valid; decisions depend on context | Code review |
| **Medium** (pseudocode, parameterized scripts) | A preferred pattern exists; configuration matters | Report generation |
| **Low** (exact script, few parameters) | Operations are fragile; consistency is critical | DB migrations |

Robot-on-a-path analogy: narrow bridge with cliffs → guardrails (low freedom). Open field → general direction (high freedom). Wrong level either wastes tokens or over-constrains the model.

### 5. Trim ruthlessly

**Default assumption: Claude is already very smart.** Challenge every paragraph: does it tell the model something it doesn't already know?

- Cut generic advice ("write production-ready code") — duplicates CLAUDE.md
- Cut identity preambles ("Act as a senior strategist...") — legacy prompt-engineering pattern; tell the model what your *approach* does, not what *persona* to adopt

### 6. Stay under 500 lines

If approaching the limit:

- Split supplementary content into `references/<topic>.md` and link from SKILL.md
- Keep references **one level deep** — Claude may partially read deeply nested files (e.g., uses `head -100` for previews)
- Reference files >100 lines: include a table of contents at the top

## Output Format

Every new skill follows this template:

````markdown
---
name: <skill-name>
description: <Third-person description.> Use when the user says "<trigger 1>", "<trigger 2>", "<trigger 3>", "<trigger 4>", "<trigger 5>", or <triggering context>. <One sentence on what the skill does.>
---

# <Title Case Name>

<One-line summary of what fires when this skill triggers.>

## Context Required (optional — include only when needed)

Read these files before running:
- [Full paths]

## Steps

1. <First concrete step — specific, actionable, not "analyze the situation">
2. <Next step with clear inputs and outputs>
3. <Continue until the deliverable is complete>

## Output Format

<Literal template with headers, structure, and length constraints. Show, don't describe.>

## Gotchas

- **<Failure pattern>** — "I know you'll want to do X, don't, here's why."
- **<Failure pattern>** — common assumption the model makes incorrectly
- **<Failure pattern>** — edge case that trips up the workflow

## Constraints

- <Sharp rule specific to THIS skill — not general behavior>
- <What can go wrong in THIS workflow specifically?>
````

## Gotchas

- **Quiet descriptions don't trigger.** Tagline-style descriptions ("A neuroscience-informed designer that...") don't fire reliably. Lead with literal phrases users would say.
- **First/second person breaks discovery.** "I can help" or "You can use" in the description — inconsistent point-of-view confuses Claude's skill selection. Always third person.
- **Generic principles waste tokens.** "Write production-ready code" lives in CLAUDE.md and tells Claude nothing new. A skill should contain non-obvious, failure-pattern-derived knowledge.
- **One sentence = one skill.** If you find yourself writing two distinct trigger sets, that's two skills. Split them.
- **Examples beat descriptions.** Show one concrete input → output for any non-trivial step. Vague descriptions get interpreted differently every run; literal templates don't.
- **Brand-coupled names rot.** `ais-doc-format` locks the skill to an identity that may change. Name by the action, not the org.
- **Don't rewrite an existing skill from scratch.** Read first, find the actual gap, edit minimally. Wholesale rewrites lose hard-won gotchas.
- **Windows-style paths break Unix.** Use forward slashes always (`scripts/file.py`, not `scripts\file.py`).
- **Time-sensitive content rots.** Use a collapsible "old patterns" section instead of "before August 2025...".
- **Pinned model versions rot.** Frontmatter `model:` must be a tier alias (`opus` / `sonnet` / `haiku`) and prose must name the tier ("Opus"), never a version (`claude-opus-4-7`, "Opus 4.7"). Aliases auto-resolve to the latest of each tier, so a new model release needs zero edits — a pinned version silently keeps running an outdated model until someone catches it.
- **MCP tools without server prefix fail to resolve.** Use `ServerName:tool_name` (e.g., `BigQuery:bigquery_schema`).
- **Renames break symlinks silently.** Renaming or moving a skill folder orphans its `~/.claude/skills/` symlink — the skill vanishes from every new session with no error anywhere. If your library installs via symlinks, re-run the install/relink step in the same commit as any rename or move (observed: two renamed skills were dead for days unnoticed).
- **Name collisions with built-ins shadow skills.** Claude Code ships built-in skills and plugins add more; two skills with one name make invocation ambiguous. Before naming or renaming, check the current session's skill list for the name (observed: a built-in `deep-research` shadowed a personal skill of the same name).
- **Voodoo constants confuse the model.** A bare `TIMEOUT = 30` tells Claude nothing — comment why 30 (otherwise the model can't reason about it).

## Constraints

- **Skill names:** noun phrase preferred, gerund or action-oriented acceptable. No `-skill` suffix, no `anthropic`/`claude` (reserved). Stay consistent within a library.
- **Description:** third-person, leads with `Use when the user says "..."`, includes ≥5 literal trigger phrases, includes both what + when.
- **Length:** SKILL.md max 500 lines. Split into `references/` if longer; references one level deep only.
- **Body sections:** every skill MUST have Steps/Process, Output Format, Gotchas, Constraints in that order. Context Required is optional.
- **No duplication of CLAUDE.md:** do not repeat rules from CLAUDE.md unless they're skill-specific.
- **Editing existing skills:** read first, identify the gap, edit minimally — never rewrite wholesale.
- **Location:** place new skills wherever your library's layout dictates, then make them discoverable from `~/.claude/skills/` (symlink or copy) so they auto-load in new sessions.

## Verification checklist (run before declaring done)

- [ ] Description in third person; leads with `Use when the user says "..."`; ≥5 literal trigger phrases
- [ ] Description includes both what the skill does AND when to use it; under 1024 characters
- [ ] Name doesn't collide with a built-in, plugin, or existing library skill (check the session skill list)
- [ ] After create/rename/move: the skill is discoverable from `~/.claude/skills/` (symlink/copy resolves) and appears in a fresh session's skill list
- [ ] Name follows noun-phrase / gerund / action-oriented form; not vague, generic, brand-coupled, or reserved
- [ ] Body has Steps/Process, Output Format, Gotchas, Constraints (in that order); Context Required only if relevant
- [ ] Steps' freedom level matches task fragility (high for creative, low for fragile)
- [ ] Output Format shows a literal template, not a description
- [ ] Gotchas captures observed failure patterns, not generic warnings
- [ ] No identity preambles ("Act as...")
- [ ] No content duplicating CLAUDE.md
- [ ] Under 500 lines; references one level deep; >100-line refs have a table of contents
- [ ] No Windows-style paths, no time-sensitive content, consistent terminology
- [ ] Model references use tier aliases (`opus`/`sonnet`/`haiku`) or bare tier names — never pinned versions (`claude-opus-4-7`, "Opus 4.7"), which rot every release
- [ ] If editing an existing skill: read first, edit minimally
