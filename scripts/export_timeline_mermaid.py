#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sqlite3
from typing import Iterable, List, Sequence, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export story timeline from SQLite to Mermaid timeline format."
    )
    parser.add_argument(
        "--db",
        default="reports/story_master.sqlite3",
        help="SQLite file path relative to repository root.",
    )
    parser.add_argument(
        "--out",
        default="reports/story_timeline.mmd",
        help="Output Mermaid file path relative to repository root.",
    )
    parser.add_argument(
        "--title",
        default="Story Timeline",
        help="Mermaid timeline title.",
    )
    parser.add_argument(
        "--levels",
        default="canon,post,draft",
        help="Comma-separated canonical levels to include.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Maximum number of rows to export.",
    )
    return parser.parse_args()


def normalize_text(text: str) -> str:
    value = text.replace("**", "").replace("`", "")
    value = re.sub(r"\s+", " ", value).strip()
    value = value.replace(":", " - ").replace("：", " - ")
    if not value:
        return "untitled"
    return value


def fetch_rows(
    conn: sqlite3.Connection, levels: Sequence[str], limit: int
) -> List[Tuple[str, str, str]]:
    placeholders = ", ".join("?" for _ in levels)
    sql = f"""
        SELECT date_start, title, canonical_level
        FROM v_event_timeline
        WHERE date_start IS NOT NULL
          AND canonical_level IN ({placeholders})
        ORDER BY date_start ASC, event_id ASC
        LIMIT ?
    """
    rows = conn.execute(sql, (*levels, int(limit))).fetchall()
    result: List[Tuple[str, str, str]] = []
    seen = set()
    for date_start, title, canonical_level in rows:
        ds = str(date_start)
        t = normalize_text(str(title or ""))
        level = str(canonical_level or "unknown")
        key = (ds, t, level)
        if key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def build_mermaid(title: str, rows: Iterable[Tuple[str, str, str]]) -> str:
    lines = ["timeline", f"    title {normalize_text(title)}"]
    for date_start, event_title, canonical_level in rows:
        lines.append(f"    {date_start} : {event_title} [{canonical_level}]")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    db_path = (root / args.db).resolve()
    out_path = (root / args.out).resolve()
    levels = [part.strip() for part in str(args.levels).split(",") if part.strip()]
    if not levels:
        raise SystemExit("levels must not be empty")
    if not db_path.exists():
        raise SystemExit(f"database not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        rows = fetch_rows(conn, levels, int(args.limit))
    finally:
        conn.close()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    mermaid = build_mermaid(str(args.title), rows)
    out_path.write_text(mermaid, encoding="utf-8")

    print(f"out={out_path}")
    print(f"rows={len(rows)}")
    print(f"levels={','.join(levels)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
