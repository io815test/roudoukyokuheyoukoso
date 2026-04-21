---
name: repository-survey
description: リポジトリの初期把握を短時間で行い、構成・実行フロー・変更リスクを整理するスキル。Use when asked to "リポジトリを把握して", "全体像を見て", "オンボーディング調査", "review project structure", or before large refactors/feature work where understanding layout and run commands is required.
---

# Repository Survey

## Overview

- Produce a concise repo briefing: purpose, structure, run/test commands, core workflows, and risk hotspots.
- Keep exploration lean: read high-signal files first and verify only essential commands.

## Output Contract

Return findings in this order:

1. `Project Purpose`
2. `Top-Level Map`
3. `How To Run`
4. `Core Workflows`
5. `Risk Hotspots`
6. `First Changes To Make`

Apply these constraints:

- Include absolute file paths for evidence files.
- Mark assumptions explicitly when evidence is missing.
- Prefer concise bullet points over narrative prose.

## Survey Workflow

1. `Inventory`
- Run top-level listing and full file list with fast search tooling.
- Identify likely stacks by lockfiles, manifests, and entrypoints.

2. `Read High-Signal Docs`
- Prioritize `AGENTS.md`, `README*`, `docs/`, CI files, and build manifests.
- Stop reading when repeated patterns confirm architecture.

3. `Trace Execution Paths`
- Locate operational entrypoints (`scripts/`, app main files, task runners).
- Extract minimal run/test/lint/build command set using `--help` when available.

4. `Validate Current State`
- Run non-destructive state checks (`git status --short --branch`).
- Run one representative low-cost workflow command when safe.

5. `Summarize Risks`
- Flag missing tests, stale docs, generated artifacts in git, manual setup traps, and unclear ownership.

## Heuristics

- Prefer `rg` / `rg --files` for speed.
- Read files incrementally; avoid bulk-loading large directories.
- Never run destructive git or filesystem commands during survey.
- If domain skills exist, recommend a minimal skill sequence for follow-up work.

## Quick Command Palette

```powershell
Get-ChildItem -Force | Select-Object Mode,Length,LastWriteTime,Name
rg --files
rg --files -g "README*" -g "AGENTS.md"
git status --short --branch
python .\scripts\*.py --help
```

## References

- Use `references/survey-template.md` for a ready-to-fill response outline.
