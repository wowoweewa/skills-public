---
name: skill-optimizer
description: Use when the user says "create a skill", "write a skill", "edit this skill", "improve this skill", "review this SKILL.md", "fix this skill description", "the skill isn't triggering", or any SKILL.md is written or changed. Checks it for triggering, sourced knowledge, gotchas and self-checks. Loads beside skill-creator even when only skill-creator is named (use it for scaffolding and evals).
---

# Skill Optimizer

Quality-assurance layer for SKILL.md authoring. Loads alongside `skill-creator` (which handles file scaffolding and validation) so the skill that ships triggers reliably, captures real failure patterns, earns every token it spends — and survives execution by a weaker model than the one that wrote it.

**What a skill is for.** A skill is expert context that lets the model perform above its default: the sourced research on what good looks like in the domain, what elite practitioners do, which folklore fails verification, and which failures have been observed. The model supplies the judgment. A skill raises the ceiling by adding knowledge the model lacks; it never limits the model with rules that tell it how to think. Process rules exist for mechanics only — paths, commands, checks, handoffs, shared vocabularies, legal gates.

## When this fires vs `skill-creator`

| Skill | Owns |
|---|---|
| `skill-creator` (Anthropic) | Mechanics — folder scaffolding, frontmatter validation, plugin registration, evals workflow |
| `skill-optimizer` (this) | Quality — description triggering, naming, conciseness, gotcha rigor, anti-patterns |

## The 5 Skill Killers — quick check

The five most common reasons skills fail. Avoid these and most quality issues take care of themselves.

| # | Killer | Fixed in |
|---|---|---|
| 1 | **Description doesn't trigger properly** — too vague, too narrow, or wrong person | Step 2 |
| 2 | **Over-defining the process** — railroading instead of guiding | Step 4 |
| 3 | **Stating the obvious, omitting the non-obvious** — tokens spent on what the model already knows, none on what it lacks | Step 5 |
| 4 | **Missing gotcha section** — not capturing failure patterns | Step 3 |
| 5 | **Monolithic blob** — everything in one file | Step 6 |

The killers cover the SKILL.md document itself; Process steps 7–10 cover execution reliability — the half most authors skip, and where skills actually fail in the field.

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

- **Third person only.** "Processes Excel files and generates reports." Never "I can help..." or "You can use this..." — a mixed point of view confuses skill selection and breaks discovery.
- **Lead with `Use when the user says "..."`** followed by **≥5 literal trigger phrases** users would actually type, including casual phrasings, abbreviations, and how real prompts come in.
- **Be LOUD, not quiet.** Claude tends to under-trigger skills. Loudness comes from literal phrases, not from length.
- **Carry what Claude needs to pick the skill, and only that.** Claude reads the description at the start of every session, before it can see the body. It carries: (1) the quoted phrases of the bullet above; (2) triggering situations that are not phrases and that Claude could not infer from the skill's name (`or pastes or links a job posting`; `any coding task inside a game project even when the word game never appears`; `run without being asked on every Google Doc Claude builds or edits`); (3) one short sentence of what the skill produces; (4) a routing clause for every sibling skill or built-in that could plausibly claim the same request, naming it (`Not for X (sibling-name)` or `Does NOT trigger on X (use sibling-name)`), plus any standing precedence (`prefer this over any built-in research harness`); (5) nothing else: no adjectives, no method, no file names or formats, no model tiers, no counts, no history, nothing the body says.
- **Test each clause, not the length.** Would Claude, seeing only the skill's name and the other clauses, pick the wrong skill or miss the trigger without this clause? Yes: it stays, whatever the length. No: it goes. There is no fixed length; the only hard limit is the frontmatter description field's 1,024 characters, which `check_skill.py` fails above.
- **Both what AND when.** All "when to use" info goes in the description, never the body.
- **Test every trigger against the siblings.** Before shipping, list every skill in the library and every agent that preloads this skill that could also claim each trigger phrase, and settle every collision with a routing clause naming that sibling. An agent that preloads a skill never repeats that skill's triggers — one phrase would otherwise spawn the agent and load the skill at once. (Observed: a routing test across eleven sibling skills found eighteen of twenty phrases claimed by two or more.)

**Knowledge.** The other limit on length is a library total, not a per-skill number. Claude Code lists every skill's name and description in each session inside one shared budget, 1% of the model's context window; when the listing overflows it drops whole descriptions, starting with the skills invoked least (source: code.claude.com/docs/en/skills, "Skill descriptions are cut short", read October 2026). A skill listed by name only cannot be matched to a request, so it stays least-invoked and stays dropped. (Observed, October 2026: the budget measured 30,000 characters on a model with a 1M-token window; 42 descriptions averaging 842 characters each passed a per-description check, nothing checked the total, and 21 of the 42 skills were listed by name only.) When a library's total exceeds the budget, raise `skillListingBudgetFraction` in `~/.claude/settings.json` (for example `0.02` for 2%, same source) or cut clauses that fail the test above; never drop a needed trigger or routing clause. Adding up the total is a library-level check for the library's own install or check script; `check_skill.py` reads one skill at a time and cannot.

✅ `Use when the user says "analyze this xlsx", "make a pivot table", "chart this spreadsheet", "clean up this workbook", "sum these columns", or attaches an .xlsx or .xlsm file. Builds pivot tables, charts and summaries from Excel files. Does NOT trigger on CSV-only requests (use csv-tools).`

❌ `A neuroscience-informed designer that builds courses...` — reads as a tagline; won't trigger reliably.

### 3. Body — required sections in this order

1. **Knowledge** (required for judgment skills — design, copy, research, analysis) — what the research says makes output good in this domain, one line per finding with its source and how it changes the output; the practitioner observations; the folklore that fails verification. This is the section that raises the ceiling. Name the research briefs it draws on so it can be refreshed when new research lands.
2. **Steps / Process** — numbered, concrete actions. Match freedom level to task fragility (see step 4).
3. **Output Format** — literal template. Show, don't describe.
4. **Gotchas** — every failure pattern observed. The highest-signal section; this IS the skill's value.
5. **Constraints** — what NOT to do. Sharp rules specific to THIS skill, not general behavior.

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

Judgment skills default to High. A constraint earns its place only with an observed, costly failure behind it; a literal template is for mechanical output (records, token files, reports a script parses), never for the creative deliverable itself.

### 5. Trim ruthlessly

**Default assumption: Claude is already very smart.** Ask of every paragraph: is this knowledge (a finding, a source, an observed failure, a why) or a thinking instruction? Keep knowledge, cut thinking instructions. Also cut the same principle stated twice — a rule repeated six times across a file reads as emphasis to the author and as noise to the model. (Observed: one design skill stated its central principle six times and its scope rule four times.)

- Cut generic advice ("write production-ready code") — it lives in CLAUDE.md and tells the model nothing new; repeat a CLAUDE.md rule only when it is specific to the skill
- Cut identity preambles ("Act as a senior strategist...") — legacy prompt-engineering pattern; tell the model what your *approach* does, not what *persona* to adopt

### 6. Stay under 500 lines

If approaching the limit:

- Split supplementary content into `references/<topic>.md` and link from SKILL.md
- Keep references **one level deep** — Claude may partially read deeply nested files (e.g., uses `head -100` for previews)
- Reference files >100 lines: include a table of contents at the top

### 7. Write for a weaker executor than you

Assume the model running the skill is less capable than the one authoring it. Everything a strong author "would just know" must be on the page — ambiguity, not missing knowledge, is where weak executors fail.

- **Scope: mechanics, not judgment.** Executor-proofing applies to paths, commands, checks, handoffs, and shared vocabularies. For a high-freedom skill a default is a labelled starting point ("when no brand exists, start here"), never a format the creative output must fill.
- **Mode skills state the mode rule first, with a default.** A skill with a build mode and a review mode names the deciding signal ("an existing file, URL, or screenshot means review; otherwise build") before anything else. (Observed: three skills with two modes each and no default.)
- **Every decision point gets a stated default** ("when unsure, do X"). Open choices ("select an appropriate depth") make weaker executors improvise — the top source of run-to-run variance.
- **Thresholds are numbers, not adjectives.** "Drop sources older than 5 years", not "prefer recent sources".
- **Commands are literal and complete** — flags, quoting, working directory. A prose gloss ("upload via the CLI") forces the executor to reconstruct the command and fail on the details.
- **No placeholder paths, and commands respect the user's standing rules.** An angle-bracketed stand-in for the skill's own directory forces path discovery on every run; write the literal path in the library's convention. A command that opens a browser, deletes, or sends must match what the user's CLAUDE.md allows without asking. (Observed: six placeholder path forms across one skill pair, and a render command carrying an open-in-browser flag against a never-open-unasked rule.)
- **Deterministic work goes in `scripts/`, not prose.** Counting, math, parsing, table assembly → bundled script; the model fills judgment fields only. (Observed: a reporting skill became reliable only when a script took over all arithmetic and the model was limited to writing 2–3 theme sentences.)
- **State the why in one clause for every non-obvious rule.** A model that knows why a rule exists handles the case the rule didn't anticipate; a naked MUST invites literal-minded compliance.
- **Show the wrong output next to the right one** for banned patterns — negative examples teach faster than positive ones.
- **Subagents can't read the skill file.** If a skill dispatches subagents, their prompts must carry everything they need pasted in — a prompt that names a section ("apply the source-priority rules") hands the subagent nothing.

### 8. Make the skill verify its own output

A rule without a check will be violated silently — not because the executor is careless, but because long outputs drift.

- **Every load-bearing rule gets a mechanical check** the skill runs before declaring done: grep the output for banned vocabulary, run the bundled validator, re-count against the source. (Observed: a formatter's "never use X terminology" rule kept being violated until the skill gained a final grep step.)
- **Checks gate the deliverable.** State the on-failure action (fix, then re-check) or the executor treats the check as advisory.
- **Steps agree with the Output Format.** Any instruction about output shape in Steps that differs from the template gets deleted; the template is the bottleneck. (Observed: three sibling skills each said "group by category" in a step while their template grouped by severity — two layouts, chosen at random per run.)
- **Templates and bundled assets pass their own checkers.** Run the skill's checker against its own Output Format template and sample assets before shipping. (Observed: a record template that failed the skill's own checker on a required line, so every literal-following run hit a FAIL it had to improvise around.)
- **Verification order: mechanical checks, then the human-visible check.** Run scripts first, then render and look; any fix re-runs both, or a page fixed after a failed check ships unseen.
- **Bundled scripts accept `-h/--help` and name the line and matched text on failure.** A script that treats `--help` as a filename, or reports "2 pattern(s)" with no location, sends a weak executor grepping.
- **A skill never run end-to-end is a draft.** One real run beats three review passes. (Observed: a screening skill survived multiple review passes, then its first live run exposed misread filing codes and fabricated catalysts.) Use `skill-creator`'s eval loop for the full treatment; the floor is one run on a real input or fixture.

### 9. Multi-file and multi-agent architecture

- **Contract rule:** every file the skill references must exist (`ls`-verify), and every promise SKILL.md makes about a reference ("the synthesizer covers X") must appear in that file. When you edit one side of a contract, grep for the other side. (Observed: the two worst defects in a mature suite were a roster recommending files that didn't exist and a prompt file missing a section its SKILL.md promised.)
- **Say it once, at the bottleneck.** A rule every output must obey lives at the narrowest point all outputs pass through (the final formatter/renderer) — never copied into upstream files. Copies drift; the next edit updates one and orphans the rest.
- **Shared vocabularies cross files verbatim.** Any value list passed between skills or to a subagent — surface types, severity tiers, finding tags, declaration syntax — is defined once and pasted; grep both sides on every edit. (Observed: one critic received three different surface-type lists from three callers and silently remapped; two checkers in one pipeline demanded two spellings of the same declaration.)
- **Deliberate mirrors name a source side.** When a subagent prompt copies a parent's principles so it is self-contained, the parent states which file is the source; edits go there first and get mirrored in the same commit. (Observed: a mirror that declared itself intentional drifted to a different item count within a month.)
- **Fan-out sizing:** every subagent needs a named consumer — say where its output lands in the synthesis. An agent whose output nothing reads is pure token burn.
- **Tier assignment:** mechanical stages (fetch, extract, reformat) on the cheapest tier; judgment stages (verdicts, synthesis, adversarial critique) on the strongest. Say so per stage, using tier aliases.
- **Partial failure:** fan-outs die mid-run (usage limits, crashes). State the quorum ("proceed if ≥N of M return", "missing critic X blocks synthesis") and the fallback (re-run that lens in the main loop, which survives limit exhaustion). A skill that assumes all agents return degrades silently after burning the tokens. A single dispatch needs the same fallback: if the one agent returns nothing, apply its prompt in the main loop and say so in the output.

### 10. Truth discipline (every number in every skill)

- **Every factual claim carries its source inline.** No source → drop the claim, don't hedge it. This includes design and copy guidance: a percentage, a "studies show", or a quoted expert in a skill body needs its source on the same line, or the number goes. (Observed: a skill describing itself as evidence-verified carried six unsourced figures.)
- **Never pad to a count.** If the skill asks for 10 and reality yields 3, ship 3 and say why — padding is where fabrication enters. (Observed: a screening skill invented plausible catalysts to fill its quota until the not-found fallback was made explicit.)
- **Every retrieval step states its not-found behavior:** write "not found", drop the item, or ask — never infer.
- **Name the save path.** If output has value past this session, state the exact location and format. (Observed: one skill's results evaporated with the session for weeks while its sister skill auto-saved.)

## Mechanical check

`scripts/check_skill.py` enforces every rule above that can be checked without judgment. Run it on every skill you create or edit, before declaring done:

```bash
python3 ~/.claude/skills/skill-optimizer/scripts/check_skill.py <skill-dir>
```

It fails on: a description over 1,024 characters (the frontmatter field's limit; step 2 sets no other length), under five quoted triggers, or without "Use when"; first or second person in the description; SKILL.md over 500 lines; a missing required section; a referenced file that does not exist; a table-of-contents entry with no heading; a placeholder path; a pinned model version (except in a run ledger named `LESSONS.md`); an evidence phrase with no source on the line; a bundled script that fails `--help`. It warns on: "Use when" arriving late, a description naming no sibling, a percentage with no source on the line, a browser-opening command, and a sentence repeated verbatim.

Zero FAIL is the gate. Every WARN is fixed or gets a one-line reason it stays. The rules the script cannot check (freedom level, knowledge versus thinking instruction, Steps agreeing with the template, vocabularies matching across files) stay on the checklist below. Whether each description clause earns its place, and a library's total against the listing budget, are judged by step 2.

## Output Format

Every new skill follows this template:

````markdown
---
name: <skill-name>
description: Use when the user says "<trigger 1>", "<trigger 2>", "<trigger 3>", "<trigger 4>", "<trigger 5>", or <triggering situation Claude could not infer from the name>. <One short sentence on what the skill does.> Does NOT trigger on <adjacent request> (use <sibling-skill>) or <another adjacent request> (use <another-sibling>).
---

# <Title Case Name>

<One-line summary of what fires when this skill triggers.>

## Context Required (optional — include only when needed)

Read these files before running:
- [Full paths]

## Knowledge (required for judgment skills)

- **<Finding>** — <source> — <how it changes the output>
- **<Folklore that fails verification>** — <source of the debunk>

Draws on: <the research briefs or references this section was built from>

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

- **One sentence = one skill.** If you find yourself writing two distinct trigger sets, that's two skills. Split them.
- **Examples beat descriptions.** Show one concrete input → output for any non-trivial step. Vague descriptions get interpreted differently every run; literal templates don't.
- **Brand-coupled names rot.** `ais-doc-format` locks the skill to an identity that may change. Name by the action, not the org.
- **Windows-style paths break Unix.** Use forward slashes always (`scripts/<name>.py`, never a backslash path).
- **Time-sensitive content rots.** Use a collapsible "old patterns" section instead of "before August 2025...".
- **Pinned model versions rot.** Frontmatter `model:` must be a tier alias (`opus` / `sonnet` / `haiku`) and prose must name the tier ("Opus"), never a version (a model ID with version numbers in it, or the tier name followed by a version number). Aliases auto-resolve to the latest of each tier, so a new model release needs zero edits — a pinned version silently keeps running an outdated model until someone catches it. One exemption: a run ledger named `LESSONS.md` has to record which model version ran, so the checker skips this rule in that file and nowhere else.
- **MCP tools without server prefix fail to resolve.** Use `ServerName:tool_name` (e.g., `BigQuery:bigquery_schema`).
- **Renames break symlinks silently.** Renaming or moving a skill folder orphans its `~/.claude/skills/` symlink — the skill vanishes from every new session with no error anywhere. If your library installs via symlinks, re-run the install/relink step in the same commit as any rename or move (observed: two renamed skills were dead for days unnoticed).
- **Name collisions with built-ins shadow skills.** Claude Code ships built-in skills and plugins add more; two skills with one name make invocation ambiguous. Before naming or renaming, check the current session's skill list for the name (observed: a built-in `deep-research` shadowed a personal skill of the same name).
- **Voodoo constants confuse the model.** A bare `TIMEOUT = 30` tells Claude nothing — comment why 30 (otherwise the model can't reason about it).

## Constraints

- **Editing existing skills:** read first, find the actual gap, edit minimally. Wholesale rewrites lose hard-won gotchas.
- **Location:** place new skills wherever your library's layout dictates, then make them discoverable from `~/.claude/skills/` (symlink or copy) so they auto-load in new sessions.
- **Checker changes:** a change to `scripts/check_skill.py` starts with a failing test in `scripts/test_check_skill.py` and ends with `python3 ~/.claude/skills/skill-optimizer/scripts/test_check_skill.py` passing — an untested checker rule can change without anyone noticing.

## Verification checklist (run before declaring done)

The first item covers every rule listed under Mechanical check. The rest are the rules the script cannot check; each names where the rule is stated and none is restated here.

- [ ] `scripts/check_skill.py <skill-dir>` reports zero FAIL; every WARN fixed or justified in one line
- [ ] Name: form and reserved words (step 1); no collision with a built-in, plugin, or library skill; not brand-coupled (Gotchas)
- [ ] After create/rename/move: the symlink or copy in `~/.claude/skills/` resolves and the skill appears in a fresh session's skill list (Constraints, Gotchas)
- [ ] Description: every clause passes the step 2 test, nothing else is in it, and every trigger is tested against siblings and preloading agents (step 2)
- [ ] Sections in the step 3 order; a judgment skill has its Knowledge section
- [ ] Freedom level matches task fragility (step 4)
- [ ] Every paragraph is knowledge or a mechanics instruction; nothing stated twice; no identity preamble (step 5)
- [ ] References one level deep (step 6)
- [ ] Executor-proofing: every bullet of step 7
- [ ] Self-verification: every bullet of step 8, including one end-to-end run on a real input or fixture
- [ ] Multi-file or multi-agent skill: every bullet of step 9
- [ ] Truth discipline: every bullet of step 10
- [ ] Every Gotcha checked against the skill; terminology consistent throughout
- [ ] Editing an existing skill: the diff is minimal (Constraints)
