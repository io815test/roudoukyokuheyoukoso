#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import build_story_db as core


JSON_COLUMNS: Dict[str, set[str]] = {
    "source_cards": {"meta_json", "topics_json", "key_entities_json"},
    "source_segments": {"topics_json", "entities_json", "thread_markers_json"},
    "entity_cards": {
        "aliases_json",
        "facts_json",
        "attributes_json",
        "relations_json",
        "source_paths_json",
    },
    "event_cards": {
        "related_entities_json",
        "related_objects_json",
        "consequences_json",
        "tags_json",
    },
    "thread_cards": {"related_entities_json"},
    "extraction_runs": {"include_roots_json", "notes_json"},
}


DDL = """
CREATE SCHEMA IF NOT EXISTS "{schema}";

DROP VIEW IF EXISTS "{schema}"."v_event_timeline" CASCADE;
DROP VIEW IF EXISTS "{schema}"."v_source_lookup" CASCADE;
DROP VIEW IF EXISTS "{schema}"."v_open_threads" CASCADE;
DROP VIEW IF EXISTS "{schema}"."v_entity_lookup" CASCADE;

DROP TABLE IF EXISTS "{schema}"."entity_mentions" CASCADE;
DROP TABLE IF EXISTS "{schema}"."thread_cards" CASCADE;
DROP TABLE IF EXISTS "{schema}"."event_cards" CASCADE;
DROP TABLE IF EXISTS "{schema}"."entity_cards" CASCADE;
DROP TABLE IF EXISTS "{schema}"."source_segments" CASCADE;
DROP TABLE IF EXISTS "{schema}"."source_cards" CASCADE;
DROP TABLE IF EXISTS "{schema}"."extraction_runs" CASCADE;

CREATE TABLE "{schema}"."source_cards" (
    source_id TEXT PRIMARY KEY,
    source_kind TEXT NOT NULL,
    source_path TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    episode_no INTEGER,
    part_no INTEGER,
    sequence_no INTEGER NOT NULL DEFAULT 0,
    summary TEXT NOT NULL,
    meta_json JSONB NOT NULL,
    topics_json JSONB NOT NULL,
    key_entities_json JSONB NOT NULL,
    event_count INTEGER NOT NULL DEFAULT 0,
    thread_count INTEGER NOT NULL DEFAULT 0,
    content_hash TEXT NOT NULL,
    modified_at TEXT NOT NULL
);

CREATE TABLE "{schema}"."source_segments" (
    segment_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_path TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    heading TEXT NOT NULL,
    heading_path TEXT NOT NULL,
    content_text TEXT NOT NULL,
    summary TEXT NOT NULL,
    topics_json JSONB NOT NULL,
    entities_json JSONB NOT NULL,
    thread_markers_json JSONB NOT NULL,
    FOREIGN KEY (source_id) REFERENCES "{schema}"."source_cards" (source_id) ON DELETE CASCADE
);

CREATE TABLE "{schema}"."entity_cards" (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    canonical_name TEXT NOT NULL UNIQUE,
    aliases_json JSONB NOT NULL,
    summary TEXT NOT NULL,
    facts_json JSONB NOT NULL,
    attributes_json JSONB NOT NULL,
    relations_json JSONB NOT NULL,
    source_paths_json JSONB NOT NULL,
    first_source_path TEXT,
    latest_source_path TEXT,
    mention_count INTEGER NOT NULL DEFAULT 0,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    updated_at TEXT NOT NULL
);

CREATE TABLE "{schema}"."entity_mentions" (
    mention_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_path TEXT NOT NULL,
    segment_id TEXT,
    snippet TEXT NOT NULL,
    mention_count INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (entity_id) REFERENCES "{schema}"."entity_cards" (entity_id) ON DELETE CASCADE,
    FOREIGN KEY (source_id) REFERENCES "{schema}"."source_cards" (source_id) ON DELETE CASCADE,
    FOREIGN KEY (segment_id) REFERENCES "{schema}"."source_segments" (segment_id) ON DELETE SET NULL
);

CREATE TABLE "{schema}"."event_cards" (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_path TEXT NOT NULL,
    date_text TEXT,
    date_start TEXT,
    sequence_no INTEGER NOT NULL DEFAULT 0,
    canonical_level TEXT NOT NULL,
    related_entities_json JSONB NOT NULL,
    related_objects_json JSONB NOT NULL,
    location_text TEXT,
    consequences_json JSONB NOT NULL,
    tags_json JSONB NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES "{schema}"."source_cards" (source_id) ON DELETE CASCADE
);

CREATE TABLE "{schema}"."thread_cards" (
    thread_id TEXT PRIMARY KEY,
    thread_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_path TEXT NOT NULL,
    related_entities_json JSONB NOT NULL,
    status TEXT NOT NULL,
    evidence_text TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES "{schema}"."source_cards" (source_id) ON DELETE CASCADE
);

CREATE TABLE "{schema}"."extraction_runs" (
    run_id TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    include_roots_json JSONB NOT NULL,
    source_count INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    notes_json JSONB NOT NULL
);

CREATE INDEX "idx_source_cards_kind_seq" ON "{schema}"."source_cards" (source_kind, sequence_no, source_path);
CREATE INDEX "idx_entity_cards_type_name" ON "{schema}"."entity_cards" (entity_type, canonical_name);
CREATE INDEX "idx_entity_mentions_source" ON "{schema}"."entity_mentions" (source_id, entity_id);
CREATE INDEX "idx_event_cards_timeline" ON "{schema}"."event_cards" (date_start, sequence_no, source_path);
CREATE INDEX "idx_thread_cards_status" ON "{schema}"."thread_cards" (status, source_path);

CREATE VIEW "{schema}"."v_entity_lookup" AS
SELECT
    entity_id,
    entity_type,
    canonical_name,
    summary,
    facts_json,
    relations_json,
    source_paths_json,
    mention_count,
    confidence
FROM "{schema}"."entity_cards";

CREATE VIEW "{schema}"."v_open_threads" AS
SELECT
    thread_id,
    thread_type,
    title,
    description,
    source_path,
    related_entities_json,
    status,
    updated_at
FROM "{schema}"."thread_cards"
WHERE status = 'open';

CREATE VIEW "{schema}"."v_source_lookup" AS
SELECT
    source_id,
    source_kind,
    source_path,
    title,
    summary,
    topics_json,
    key_entities_json,
    event_count,
    thread_count,
    modified_at
FROM "{schema}"."source_cards";

CREATE VIEW "{schema}"."v_event_timeline" AS
SELECT
    event_id,
    date_start,
    title,
    canonical_level,
    source_path,
    summary
FROM "{schema}"."event_cards"
WHERE date_start IS NOT NULL;
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export story cards as PostgreSQL SQL file.")
    parser.add_argument("--include", default="posts")
    parser.add_argument("--schema", default="story_cards")
    parser.add_argument("--out", default="reports/story_cards_posts.sql")
    return parser.parse_args()


def escape_sql_text(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_value(table: str, column: str, value: object) -> str:
    if value is None:
        return "NULL"
    if column in JSON_COLUMNS.get(table, set()):
        if isinstance(value, str):
            payload = value
        else:
            payload = json.dumps(value, ensure_ascii=False)
        return f"{escape_sql_text(payload)}::jsonb"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return escape_sql_text(str(value))


def rows_to_insert_sql(schema: str, table: str, records: Sequence[Dict[str, object]]) -> Iterable[str]:
    if not records:
        return
    columns = list(records[0].keys())
    col_sql = ", ".join(f'"{col}"' for col in columns)
    yield f'INSERT INTO "{schema}"."{table}" ({col_sql}) VALUES'
    tuples: List[str] = []
    for record in records:
        values = ", ".join(sql_value(table, col, record[col]) for col in columns)
        tuples.append(f"({values})")
    yield ",\n".join(tuples) + ";"


def build_records(include_roots: Sequence[str]) -> Dict[str, List[Dict[str, object]]]:
    root = core.repo_root()
    started_at = core.now_iso()
    run_id = core.stable_id("run", started_at, ",".join(include_roots))

    documents = core.load_documents(root, include_roots)
    entity_records = core.build_entity_records(documents)
    mentions, source_entity_counts = core.collect_mentions(documents, entity_records)
    thread_records = core.build_thread_records(documents, source_entity_counts)
    event_records = core.build_event_records(documents, entity_records, source_entity_counts)
    source_records = core.build_source_records(documents, source_entity_counts, event_records, thread_records)
    segment_records = core.build_segment_records(documents, source_entity_counts)
    timestamp = core.now_iso()

    for record in entity_records:
        record["updated_at"] = timestamp
    for record in event_records:
        record["updated_at"] = timestamp
    for record in thread_records:
        record["updated_at"] = timestamp

    source_mention_count: Dict[str, int] = {}
    for mention in mentions:
        entity_id = str(mention["entity_id"])
        source_mention_count[entity_id] = source_mention_count.get(entity_id, 0) + int(mention["mention_count"])
    for entity in entity_records:
        entity["mention_count"] = source_mention_count.get(str(entity["entity_id"]), 0)

    extraction_runs = [
        {
            "run_id": run_id,
            "schema_version": "story_cards_v1",
            "include_roots_json": json.dumps(list(include_roots), ensure_ascii=False),
            "source_count": len(documents),
            "started_at": started_at,
            "completed_at": core.now_iso(),
            "notes_json": json.dumps(
                {
                    "entity_count": len(entity_records),
                    "event_count": len(event_records),
                    "thread_count": len(thread_records),
                },
                ensure_ascii=False,
            ),
        }
    ]

    return {
        "source_cards": source_records,
        "source_segments": segment_records,
        "entity_cards": entity_records,
        "entity_mentions": mentions,
        "event_cards": event_records,
        "thread_cards": thread_records,
        "extraction_runs": extraction_runs,
    }


def main() -> int:
    args = parse_args()
    include_roots = [part.strip() for part in str(args.include).split(",") if part.strip()]
    if not include_roots:
        raise SystemExit("include roots must not be empty")

    root = core.repo_root()
    out_path = (root / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    records_by_table = build_records(include_roots)

    chunks: List[str] = ["BEGIN;"]
    chunks.append(DDL.format(schema=args.schema))
    for table in (
        "source_cards",
        "source_segments",
        "entity_cards",
        "entity_mentions",
        "event_cards",
        "thread_cards",
        "extraction_runs",
    ):
        chunks.extend(rows_to_insert_sql(args.schema, table, records_by_table[table]))
    chunks.append("COMMIT;")

    out_path.write_text("\n\n".join(chunks) + "\n", encoding="utf-8")

    print(f"out={out_path}")
    print(f"schema={args.schema}")
    print(f"include={','.join(include_roots)}")
    print(f"source_count={len(records_by_table['source_cards'])}")
    print(f"entity_count={len(records_by_table['entity_cards'])}")
    print(f"event_count={len(records_by_table['event_cards'])}")
    print(f"thread_count={len(records_by_table['thread_cards'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
