---
name: story-post-pipeline
description: Split a completed draft episode into post-sized markdown files, extract fixed-schema JSON records for each post, save those JSON files under reports/extractions/, and rebuild the story SQLite card database. Use when a draft episode is ready to be turned into operational retrieval data for LLM continuity work.
---

# Story Post Pipeline

Use this skill when a draft episode is finished enough to convert into `posts/`, extraction JSON, and SQLite refresh in one workflow.

Treat the workflow as three explicit phases:

1. `split`
2. `extract`
3. `ingest`

Do not skip the intermediate JSON files. They are the reviewable source for later re-imports and schema changes.

## Repository Conventions

- Read from `drafts/`
- Write post files to `posts/`
- Write extraction JSON to `reports/extractions/`
- Rebuild SQLite at `reports/story_master.sqlite3`

Prefer episode-scoped extraction folders:

- `reports/extractions/episode-04/part-01.json`
- `reports/extractions/episode-04/part-02.json`

If the episode slug is unclear, derive it from the destination post filenames and keep the naming stable.

## Workflow

### 1. Split

Split the completed draft into orthodox web-novel post units.

Rules:

- Preserve original prose verbatim unless the user explicitly asks for rewriting.
- Split on scene or pacing boundaries when possible.
- Prefer stable filenames such as `posts/episode-04-part-01.md`.
- Keep source metadata lines such as `Date`, `Location`, `Person`, `Assignment`, `Segment` when they help later extraction.

Before writing split files, inspect adjacent `posts/` filenames so numbering stays consistent.

### 2. Extract

For each new post file, create one JSON file using the fixed schema in [references/extraction-schema.md](references/extraction-schema.md).

Rules:

- Extract only what is explicit in the text.
- Keep uncertain material out of confirmed facts.
- Put unresolved but text-grounded items into `threads`.
- Do not invent foreshadowing; only emit `foreshadow_candidate` when the text itself marks something as suggestive or unresolved.
- Keep summaries short and factual.
- Use canonical names when obvious, otherwise preserve the surface form from the post.

### 3. Ingest

After JSON files are written, rebuild the SQLite DB.

Use:

```powershell
python .\scripts\build_story_db.py --db reports/story_master.sqlite3 --include canon,drafts,posts
python .\scripts\story_workflow.py sync
```

The current SQLite pipeline rebuilds from markdown, not from extraction JSON. The JSON files still matter because they serve as the stable extraction audit trail and future ingest source.

## Output Contract

Unless the user asks otherwise, finish with:

- created or updated `posts/` files
- created extraction JSON paths
- DB rebuild status
- any extraction ambiguities that should be reviewed by a human

## Scope Discipline

- Do not silently rewrite story content during splitting.
- Do not mix `plot` intentions into confirmed `post` facts.
- Do not store interpretation-heavy themes or author intent as hard facts.
- Do not delete existing extraction JSON for unrelated episodes.

## Resources

- [references/extraction-schema.md](references/extraction-schema.md): fixed JSON structure and field meanings.
