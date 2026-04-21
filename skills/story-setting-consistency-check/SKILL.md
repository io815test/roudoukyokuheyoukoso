---
name: story-setting-consistency-check
description: Check new story material against established canon and flag contradictions, unsupported assumptions, and unresolved ambiguities. Use when comparing a draft scene, synopsis, character sheet, timeline, faction note, combat sequence, or worldbuilding addition against existing setting documents in long-running fiction projects.
---

# Story Setting Consistency Check

Use this skill as a continuity auditor. Read the canonical setting first, read the candidate text second, then report what is incompatible, what is merely uncertain, and what remains aligned.

## Canon Source Order

Choose canon in this order unless the user overrides it.

1. Files explicitly named by the user
2. Project canon files under `canon/`, `setting/`, `lore/`, `world/`, or `docs/`
3. Canon text supplied in the current conversation

For this workspace, check `canon/world-setting.md` first if it exists.
Treat it as the canon entrypoint or index, not automatically as the only authoritative text.
If it links to numbered canon files under `canon/`, follow the relevant linked files before judging continuity.
Do not assume specific filenames beyond what currently exists in the workspace.

If two canon sources disagree, do not resolve the conflict silently. Report the conflict as `canon mismatch` and ask which source should win.

## Workflow

1. Identify the canonical sources you will treat as authoritative.
2. If `canon/world-setting.md` is an index, resolve the relevant linked canon files from it.
3. Read only the canon sections relevant to the candidate text.
4. Extract concrete claims from the candidate text before judging it.
5. Compare those claims against canon using the checklist in [references/checklist.md](references/checklist.md).
6. Classify each issue with the narrowest accurate label.
7. Offer the smallest correction that preserves the author's intent when asked for fixes.

## Issue Labels

Use exactly these labels in reports.

- `Contradiction`: The new material directly conflicts with canon.
- `Needs confirmation`: Canon does not support the claim strongly enough to let it pass as fact.
- `Canon mismatch`: Two canonical sources conflict with each other.
- `Consistent`: The new material clearly fits canon.
- `Ripple risk`: A change is locally valid but likely affects other established material.

Do not call something a contradiction when canon is merely silent.

## Output Format

Prefer this compact structure.

### Verdict

State whether the candidate text is broadly consistent, inconsistent, or blocked by missing canon.

### Findings

List findings in severity order. For each finding include:

- label
- short explanation
- canon evidence
- candidate evidence
- smallest viable fix if useful

### Open Questions

List only the missing decisions that prevent a confident judgment.

### Safe Elements

Optionally note details that already fit canon well when that helps preserve intent during revisions.

## Evidence Rules

- Cite file paths and line references when checking files.
- If the canon is only in conversation, cite the section heading or a short quoted phrase.
- Prefer short quotations over paraphrase when the exact wording matters.
- Separate facts from inference. Say when you are inferring.
- If the index and the linked canon files differ in specificity, treat the linked file as the stronger source for that topic and report any disagreement as `Canon mismatch`.

## Scope Discipline

- Do not rewrite the whole draft unless asked.
- Do not expand canon on your own to patch holes.
- Do not flatten intentional ambiguity into hard fact.
- When several fixes are possible, present the least disruptive one first.

## Project Defaults For This Workspace

When working on the current project, pay extra attention to:

- timeline anchors such as `2002-04-03` and `2012`
- the distinction between meteorites, magical beasts, and silicon plants
- the limits and costs of magic
- modern-military logistics versus catalyst-magic technology
- rank, role, and personal history consistency for named characters

Load [references/checklist.md](references/checklist.md) when preparing the review.
