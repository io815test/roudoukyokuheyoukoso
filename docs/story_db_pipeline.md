# Story DB Pipeline

This repository is markdown-first.  
`scripts/build_story_db.py` rebuilds `reports/story_master.sqlite3` as an LLM-friendly card store from `canon/`, `drafts/`, and `posts/`.

## What It Builds

- `source_cards`
  - one card per markdown file
- `source_segments`
  - heading-based segments for retrieval
- `entity_cards`
  - characters, organizations, places, vehicles, weapons, and other recurring terms
- `entity_mentions`
  - source/segment evidence for entity mentions
- `event_cards`
  - one lightweight timeline card per source document
- `thread_cards`
  - unresolved items, foreshadow candidates, and watch points
- `extraction_runs`
  - rebuild log with schema version and counts

Views:

- `v_entity_lookup`
- `v_open_threads`
- `v_source_lookup`
- `v_event_timeline`

## Run

```bash
python scripts/build_story_db.py
python scripts/build_story_db.py --db reports/story_master.sqlite3 --include canon,drafts,posts
```

`--keep-db` is accepted for compatibility, but the database is always rebuilt from scratch.

## MD-First Quick Ops

```bash
python scripts/story_workflow.py memo --title "敵生態の新仮説"
python scripts/story_workflow.py sync
python scripts/export_timeline_mermaid.py --out reports/story_timeline.mmd --levels canon,post,draft --limit 200
```

`sync` prints:

- table counts
- source kind counts
- open thread counts
- recent draft cards

## Typical Usage

1. Update files under `canon/`, `drafts/`, or `posts/`.
2. Rebuild with `python scripts/build_story_db.py`.
3. Query `entity_cards` or `v_entity_lookup` when the model needs a quick refresher on a person, faction, weapon, or place.
4. Query `thread_cards` or `v_open_threads` for unresolved continuity items.
5. Query `source_cards` or `source_segments` to jump back to the originating markdown.
6. Query `event_cards` or `v_event_timeline` for date-ordered reference.

## Notes

- The schema intentionally favors denormalized cards over strict normalization.
- Extraction is heuristic and deterministic; ambiguous items are expected.
- Treat markdown as the source of truth and the SQLite DB as a retrieval cache for humans and LLMs.
