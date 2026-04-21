#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Sequence

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild story card database in PostgreSQL from markdown sources."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="01251203")
    parser.add_argument("--dbname", default="mydb")
    parser.add_argument(
        "--schema",
        default="story_cards",
        help="Target schema name in PostgreSQL.",
    )
    parser.add_argument(
        "--include",
        default="posts",
        help="Comma-separated roots to index (default: posts).",
    )
    return parser.parse_args()


def init_schema(conn: psycopg.Connection, schema: str) -> None:
    with conn.cursor() as cur:
        cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))

        cur.execute(sql.SQL("DROP VIEW IF EXISTS {} CASCADE").format(sql.Identifier(schema, "v_event_timeline")))
        cur.execute(sql.SQL("DROP VIEW IF EXISTS {} CASCADE").format(sql.Identifier(schema, "v_source_lookup")))
        cur.execute(sql.SQL("DROP VIEW IF EXISTS {} CASCADE").format(sql.Identifier(schema, "v_open_threads")))
        cur.execute(sql.SQL("DROP VIEW IF EXISTS {} CASCADE").format(sql.Identifier(schema, "v_entity_lookup")))

        cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(schema, "entity_mentions")))
        cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(schema, "thread_cards")))
        cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(schema, "event_cards")))
        cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(schema, "entity_cards")))
        cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(schema, "source_segments")))
        cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(schema, "source_cards")))
        cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(sql.Identifier(schema, "extraction_runs")))

        cur.execute(
            sql.SQL(
                """
                CREATE TABLE {} (
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
                )
                """
            ).format(sql.Identifier(schema, "source_cards"))
        )
        cur.execute(
            sql.SQL(
                """
                CREATE TABLE {} (
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
                    FOREIGN KEY (source_id) REFERENCES {} (source_id) ON DELETE CASCADE
                )
                """
            ).format(sql.Identifier(schema, "source_segments"), sql.Identifier(schema, "source_cards"))
        )
        cur.execute(
            sql.SQL(
                """
                CREATE TABLE {} (
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
                )
                """
            ).format(sql.Identifier(schema, "entity_cards"))
        )
        cur.execute(
            sql.SQL(
                """
                CREATE TABLE {} (
                    mention_id TEXT PRIMARY KEY,
                    entity_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    segment_id TEXT,
                    snippet TEXT NOT NULL,
                    mention_count INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY (entity_id) REFERENCES {} (entity_id) ON DELETE CASCADE,
                    FOREIGN KEY (source_id) REFERENCES {} (source_id) ON DELETE CASCADE,
                    FOREIGN KEY (segment_id) REFERENCES {} (segment_id) ON DELETE SET NULL
                )
                """
            ).format(
                sql.Identifier(schema, "entity_mentions"),
                sql.Identifier(schema, "entity_cards"),
                sql.Identifier(schema, "source_cards"),
                sql.Identifier(schema, "source_segments"),
            )
        )
        cur.execute(
            sql.SQL(
                """
                CREATE TABLE {} (
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
                    FOREIGN KEY (source_id) REFERENCES {} (source_id) ON DELETE CASCADE
                )
                """
            ).format(sql.Identifier(schema, "event_cards"), sql.Identifier(schema, "source_cards"))
        )
        cur.execute(
            sql.SQL(
                """
                CREATE TABLE {} (
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
                    FOREIGN KEY (source_id) REFERENCES {} (source_id) ON DELETE CASCADE
                )
                """
            ).format(sql.Identifier(schema, "thread_cards"), sql.Identifier(schema, "source_cards"))
        )
        cur.execute(
            sql.SQL(
                """
                CREATE TABLE {} (
                    run_id TEXT PRIMARY KEY,
                    schema_version TEXT NOT NULL,
                    include_roots_json JSONB NOT NULL,
                    source_count INTEGER NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    notes_json JSONB NOT NULL
                )
                """
            ).format(sql.Identifier(schema, "extraction_runs"))
        )

        cur.execute(
            sql.SQL("CREATE INDEX {} ON {} (source_kind, sequence_no, source_path)").format(
                sql.Identifier("idx_source_cards_kind_seq"),
                sql.Identifier(schema, "source_cards"),
            )
        )
        cur.execute(
            sql.SQL("CREATE INDEX {} ON {} (entity_type, canonical_name)").format(
                sql.Identifier("idx_entity_cards_type_name"),
                sql.Identifier(schema, "entity_cards"),
            )
        )
        cur.execute(
            sql.SQL("CREATE INDEX {} ON {} (source_id, entity_id)").format(
                sql.Identifier("idx_entity_mentions_source"),
                sql.Identifier(schema, "entity_mentions"),
            )
        )
        cur.execute(
            sql.SQL("CREATE INDEX {} ON {} (date_start, sequence_no, source_path)").format(
                sql.Identifier("idx_event_cards_timeline"),
                sql.Identifier(schema, "event_cards"),
            )
        )
        cur.execute(
            sql.SQL("CREATE INDEX {} ON {} (status, source_path)").format(
                sql.Identifier("idx_thread_cards_status"),
                sql.Identifier(schema, "thread_cards"),
            )
        )

        cur.execute(
            sql.SQL(
                """
                CREATE VIEW {} AS
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
                FROM {}
                """
            ).format(sql.Identifier(schema, "v_entity_lookup"), sql.Identifier(schema, "entity_cards"))
        )
        cur.execute(
            sql.SQL(
                """
                CREATE VIEW {} AS
                SELECT
                    thread_id,
                    thread_type,
                    title,
                    description,
                    source_path,
                    related_entities_json,
                    status,
                    updated_at
                FROM {}
                WHERE status = 'open'
                """
            ).format(sql.Identifier(schema, "v_open_threads"), sql.Identifier(schema, "thread_cards"))
        )
        cur.execute(
            sql.SQL(
                """
                CREATE VIEW {} AS
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
                FROM {}
                """
            ).format(sql.Identifier(schema, "v_source_lookup"), sql.Identifier(schema, "source_cards"))
        )
        cur.execute(
            sql.SQL(
                """
                CREATE VIEW {} AS
                SELECT
                    event_id,
                    date_start,
                    title,
                    canonical_level,
                    source_path,
                    summary
                FROM {}
                WHERE date_start IS NOT NULL
                """
            ).format(sql.Identifier(schema, "v_event_timeline"), sql.Identifier(schema, "event_cards"))
        )


def _convert_value(table: str, column: str, value: object) -> object:
    if column not in JSON_COLUMNS.get(table, set()):
        return value
    if isinstance(value, str):
        return Jsonb(json.loads(value))
    return Jsonb(value)


def insert_records(conn: psycopg.Connection, schema: str, table: str, records: Sequence[Dict[str, object]]) -> None:
    if not records:
        return
    columns = list(records[0].keys())
    statement = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(schema, table),
        sql.SQL(", ").join(sql.Identifier(column) for column in columns),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )
    rows: List[List[object]] = []
    for record in records:
        row = [_convert_value(table, column, record[column]) for column in columns]
        rows.append(row)
    with conn.cursor() as cur:
        cur.executemany(statement, rows)


def update_entity_counts(conn: psycopg.Connection, schema: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL(
                """
                UPDATE {} e
                SET mention_count = COALESCE(
                    (
                        SELECT SUM(m.mention_count)
                        FROM {} m
                        WHERE m.entity_id = e.entity_id
                    ),
                    0
                )
                """
            ).format(sql.Identifier(schema, "entity_cards"), sql.Identifier(schema, "entity_mentions"))
        )


def build_database(conn: psycopg.Connection, schema: str, root: Path, include_roots: Sequence[str]) -> None:
    started_at = core.now_iso()
    run_id = core.stable_id("run", started_at, ",".join(include_roots))
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL(
                """
                INSERT INTO {} (
                    run_id, schema_version, include_roots_json, source_count, started_at, completed_at, notes_json
                ) VALUES (%s, %s, %s, 0, %s, NULL, %s)
                """
            ).format(sql.Identifier(schema, "extraction_runs")),
            (run_id, "story_cards_v1", Jsonb(list(include_roots)), started_at, Jsonb({})),
        )

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

    insert_records(conn, schema, "source_cards", source_records)
    insert_records(conn, schema, "source_segments", segment_records)
    insert_records(conn, schema, "entity_cards", entity_records)
    insert_records(conn, schema, "entity_mentions", mentions)
    insert_records(conn, schema, "event_cards", event_records)
    insert_records(conn, schema, "thread_cards", thread_records)
    update_entity_counts(conn, schema)

    with conn.cursor() as cur:
        cur.execute(
            sql.SQL(
                """
                UPDATE {}
                SET source_count = %s, completed_at = %s, notes_json = %s
                WHERE run_id = %s
                """
            ).format(sql.Identifier(schema, "extraction_runs")),
            (
                len(documents),
                core.now_iso(),
                Jsonb(
                    {
                        "entity_count": len(entity_records),
                        "event_count": len(event_records),
                        "thread_count": len(thread_records),
                    }
                ),
                run_id,
            ),
        )

    print(f"schema={schema}")
    print(f"include={','.join(include_roots)}")
    print(f"source_count={len(documents)}")
    print(f"entity_count={len(entity_records)}")
    print(f"event_count={len(event_records)}")
    print(f"thread_count={len(thread_records)}")


def main() -> int:
    args = parse_args()
    include_roots = [part.strip() for part in str(args.include).split(",") if part.strip()]
    if not include_roots:
        raise SystemExit("include roots must not be empty")

    root = core.repo_root()
    conninfo = (
        f"host={args.host} port={args.port} dbname={args.dbname} "
        f"user={args.user} password={args.password}"
    )
    with psycopg.connect(conninfo, autocommit=False) as conn:
        init_schema(conn, args.schema)
        build_database(conn, args.schema, root, include_roots)
        conn.commit()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
