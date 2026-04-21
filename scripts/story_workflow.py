#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
from typing import Iterable, Tuple


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def slugify_filename(text: str) -> str:
    value = text.strip().lower()
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^\w\-]", "", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "memo"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    counter = 2
    while True:
        candidate = path.with_name(f"{stem}-{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def build_memo_content(title: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""# {title}

- 日時: {now}
- 種別: memo
- 優先度: medium
- 関連人物:
- 関連勢力:
- 関連時期:
- 伏線:
- 状態: draft

## メモ

-

## 仮説

-

## 未確定

-
"""


def cmd_memo(args: argparse.Namespace) -> int:
    root = repo_root()
    drafts_dir = (root / args.dir).resolve()
    drafts_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    slug = slugify_filename(args.title)
    base = drafts_dir / f"memo-{stamp}-{slug}.md"
    target = unique_path(base)
    target.write_text(build_memo_content(args.title), encoding="utf-8")
    print(f"created: {target}")
    return 0


def run_build_story_db(root: Path, db_rel: str, include: str) -> int:
    cmd = [
        sys.executable,
        str(root / "scripts" / "build_story_db.py"),
        "--db",
        db_rel,
        "--include",
        include,
    ]
    completed = subprocess.run(cmd, cwd=str(root), check=False)
    return int(completed.returncode)


def fetch_one(cur: sqlite3.Cursor, sql: str, params: Iterable[object] = ()) -> int:
    row = cur.execute(sql, tuple(params)).fetchone()
    return int(row[0]) if row is not None else 0


def print_sync_report(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    print("[counts]")
    for table_name in (
        "source_cards",
        "source_segments",
        "entity_cards",
        "entity_mentions",
        "event_cards",
        "thread_cards",
    ):
        count = fetch_one(cur, f"SELECT COUNT(*) FROM {table_name}")
        print(f"{table_name}: {count}")

    print("\n[source kinds]")
    rows: Iterable[Tuple[str, int]] = cur.execute(
        """
        SELECT source_kind, COUNT(*)
        FROM source_cards
        GROUP BY source_kind
        ORDER BY source_kind
        """
    )
    for source_kind, source_count in rows:
        print(f"{source_kind}: {source_count}")

    print("\n[open threads]")
    rows = cur.execute(
        """
        SELECT thread_type, COUNT(*)
        FROM thread_cards
        WHERE status = 'open'
        GROUP BY thread_type
        ORDER BY thread_type
        """
    )
    for thread_type, thread_count in rows:
        print(f"{thread_type}: {thread_count}")

    print("\n[recent drafts]")
    rows = cur.execute(
        """
        SELECT source_path, title, substr(summary, 1, 70), modified_at
        FROM source_cards
        WHERE source_kind = 'drafts'
        ORDER BY modified_at DESC, source_path DESC
        LIMIT 10
        """
    )
    for source_path, title, summary, modified_at in rows:
        print(f"{source_path} [{title}] {summary} ({modified_at})")

    conn.close()


def cmd_sync(args: argparse.Namespace) -> int:
    root = repo_root()
    db_rel = args.db
    include = args.include
    db_path = (root / db_rel).resolve()

    rc = run_build_story_db(root, db_rel, include)
    if rc != 0:
        return rc
    if not db_path.exists():
        print(f"error: db not found: {db_path}", file=sys.stderr)
        return 2
    print_sync_report(db_path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="MD-first workflow helper: create memo and sync story DB."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    memo = sub.add_parser("memo", help="Create a drafts memo template.")
    memo.add_argument("--title", required=True, help="Memo title.")
    memo.add_argument(
        "--dir",
        default="drafts",
        help="Target directory relative to repo root (default: drafts).",
    )
    memo.set_defaults(func=cmd_memo)

    sync = sub.add_parser("sync", help="Rebuild DB and print summary.")
    sync.add_argument(
        "--db",
        default="reports/story_master.sqlite3",
        help="SQLite output path relative to repo root.",
    )
    sync.add_argument(
        "--include",
        default="canon,drafts,posts",
        help="Comma separated include roots for build_story_db.py.",
    )
    sync.set_defaults(func=cmd_sync)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
