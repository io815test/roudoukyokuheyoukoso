#!/usr/bin/env python3
"""
各話のドラフトを走査し、話数ごとに出現したアイテム（武器・術式）を
reports/loadouts.json に出力する。

キャラクターへの紐付けは行わない。
誰が何を使うかは canon/05_characters.md を参照すること。

使い方:
    python scripts/extract_loadouts.py
    python scripts/extract_loadouts.py --drafts-dir drafts --out reports/loadouts.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# 既知アイテム辞書
# キー: 出力名, 値: ドラフト内での表記パターン（正規表現）
# ---------------------------------------------------------------------------
ITEMS: dict[str, str] = {
    # 実銃
    "ガリル":           r"ガリル",
    "AK-74":           r"AK-74",
    "ベネリM4":         r"ベネリ\s*M4",
    "MGL-140":         r"MGL-140",
    "M240":            r"M240",
    "Barrett M95":     r"Barrett\s*M95",
    "RPG":             r"RPG",
    # 近接・装備
    "ブリーチングアックス": r"ブリーチングアックス|手斧",
    "拳銃":             r"拳銃",
    "カランビット":      r"カランビット",
    "メリケンサック":    r"メリケンサック",
    # 術式
    "焼砂錐":           r"焼砂錐",
    "焼砂杭":           r"焼砂杭",
    "ロックニードル":    r"ロックニードル",
    "魔力付与":         r"魔力付与|魔力を(刃物|武器|斧|ガリル)",
    "ステイシス":        r"ステイシス",
}


def extract_episode(path: Path) -> list[str]:
    """ドラフト1ファイルを走査し、出現したアイテム名のリストを返す。"""
    text = path.read_text(encoding="utf-8")
    found = sorted(
        name for name, pat in ITEMS.items()
        if re.search(pat, text)
    )
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description="装備・術式の話数別出現リスト抽出")
    parser.add_argument("--drafts-dir", default="drafts")
    parser.add_argument("--out", default="reports/loadouts.json")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    drafts_dir = root / args.drafts_dir
    out_path = root / args.out

    episode_files = sorted(
        f for f in drafts_dir.glob("episode-[0-9]*.md")
        if "plot" not in f.name and "flow" not in f.name
    )

    loadouts: dict[str, list[str]] = {}
    for f in episode_files:
        key = f.stem
        loadouts[key] = extract_episode(f)
        print(f"  {key}: {len(loadouts[key])} アイテム")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(loadouts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n出力: {out_path}")


if __name__ == "__main__":
    main()
