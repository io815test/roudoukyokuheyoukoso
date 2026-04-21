#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


HEADING_RE = re.compile(r"^(#{1,6})\s*(.+?)\s*$")
BULLET_KV_RE = re.compile(r"^\s*-\s*([^:：]{1,40})[:：]\s*(.+?)\s*$")
META_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 _-]{1,30})\s*:\s*(.+?)\s*$")
ISO_DATE_RE = re.compile(r"\b((?:19|20)\d{2})-(\d{2})-(\d{2})\b")
JP_DATE_RE = re.compile(r"((?:19|20)\d{2})年\s*(\d{1,2})月(?:\s*(\d{1,2})日)?")
YEAR_RE = re.compile(r"((?:19|20)\d{2})年")
RELATION_SECTION_RE = re.compile(r"^\s*(.+?)との関係\s*$")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
THREAD_MARKERS = (
    "未回収",
    "未解決",
    "未確定",
    "謎",
    "示唆",
    "匂わせ",
    "布石",
    "違和感",
    "保留",
    "気がかり",
    "不穏",
    "兆候",
)
TOPIC_KEYWORDS: Dict[str, Sequence[str]] = {
    "character": ("人物", "来歴", "関係", "心理", "隊員"),
    "military": ("小隊", "分隊", "司令部", "連隊", "任務", "作戦", "回収"),
    "magic": ("魔術", "術式", "触媒", "焼砂", "ロックニードル"),
    "enemy": ("魔獣", "ワレモノ", "マザリモノ", "王の獣"),
    "world": ("世界観", "隕石", "五隕", "戦線", "方面"),
    "equipment": ("武装", "主武装", "車両", "装備", "輸送機", "APC", "UH-60L"),
}
GENERIC_TITLES = {
    "概要",
    "要点",
    "状況",
    "役割",
    "基本情報",
    "来歴",
    "戦闘特性",
    "思想と行動原理",
    "この話の芯",
    "前話からの接続",
    "この場の役割",
    "描写ポイント",
    "会話の要点",
    "発見物",
    "重要な演出",
    "シーン概要",
    "この場でやること",
    "内面",
    "編成概要",
    "コールサイン運用",
    "暫定ロスター",
    "車両",
    "場所",
}
STOP_ENTITY_NAMES = {
    "Date",
    "Location",
    "Assignment",
    "Segment",
    "Person",
    "戦闘",
    "戦争",
    "規模",
    "所属",
    "通信",
    "中尉",
    "少尉",
    "大尉",
}
IGNORE_VALUES = {"名称未設定", "名称未定", "未設定", "未定", "不明", "なし"}
CHARACTER_KEYS = {
    "名前",
    "主要人物",
    "関係者",
    "登場人物",
    "関連人物",
    "人物",
    "小隊長",
    "小隊軍曹",
    "通信手兼副官",
    "衛生兵",
    "随伴魔術士官",
    "分隊長",
    "副分隊長",
    "小銃手",
    "軽機関銃手",
    "擲弾手",
    "重火器手",
    "弾薬手",
    "回収兼工兵要員",
}
ORG_KEYS = {"Assignment", "所属", "勢力", "組織", "部隊", "原隊"}
PLACE_KEYS = {"Location", "場所", "拠点", "方面", "戦線"}
WEAPON_KEYS = {"主武装", "近接武装", "補助近接武装", "武装", "兵装"}
VEHICLE_KEYS = {"車両", "輸送", "輸送機"}
RANK_SUFFIXES = ("少尉", "中尉", "大尉", "少佐", "中佐", "大佐", "軍曹", "曹長", "准尉", "兵長")


@dataclass
class Segment:
    segment_id: str
    ordinal: int
    heading: str
    heading_path: List[str]
    level: int
    content: str


@dataclass
class Document:
    source_id: str
    source_kind: str
    source_path: str
    title: str
    text: str
    summary: str
    episode_no: Optional[int]
    part_no: Optional[int]
    sequence_no: int
    meta: Dict[str, str]
    topics: List[str]
    segments: List[Segment]
    modified_at: str
    content_hash: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_id(prefix: str, *parts: object) -> str:
    payload = "||".join(str(part) for part in parts)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def markdown_to_plain(text: str) -> str:
    value = text.replace("**", "").replace("`", "").replace("---", " ")
    value = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", value)
    value = re.sub(r"^>\s*", "", value, flags=re.MULTILINE)
    return normalize_ws(value)


def derive_title(path: Path, text: str) -> str:
    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match and len(match.group(1)) == 1:
            return markdown_to_plain(match.group(2))
    return path.stem.replace("-", " ").strip()


def infer_topics(text: str) -> List[str]:
    topics: List[str] = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            topics.append(topic)
    return topics


def guess_episode_part(path: Path) -> Tuple[Optional[int], Optional[int], int]:
    path_str = path.as_posix()
    episode_no: Optional[int] = None
    part_no: Optional[int] = None
    sequence_no = 0
    episode_match = re.search(r"episode-(\d+)", path_str)
    if episode_match:
        episode_no = int(episode_match.group(1))
        sequence_no += episode_no * 100
    part_match = re.search(r"part-(\d+)", path_str)
    if part_match:
        part_no = int(part_match.group(1))
        sequence_no += part_no
    return episode_no, part_no, sequence_no


def extract_meta(lines: Sequence[str]) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    for line in lines[:12]:
        if line.strip() == "---":
            break
        match = META_RE.match(line)
        if match:
            meta[match.group(1).strip()] = markdown_to_plain(match.group(2))
    return meta


def extract_summary(text: str) -> str:
    lines = [markdown_to_plain(line) for line in text.splitlines()]
    lines = [
        line
        for line in lines
        if line
        and not line.startswith("#")
        and not META_RE.match(line)
        and line not in GENERIC_TITLES
    ]
    if not lines:
        return ""
    return normalize_ws(" ".join(lines[:3]))[:280]


def build_segments(source_path: str, text: str, title: str) -> List[Segment]:
    segments: List[Segment] = []
    current_heading = title
    current_level = 1
    current_content: List[str] = []
    heading_stack: List[str] = [title]
    ordinal = 1

    def flush() -> None:
        nonlocal ordinal
        content = "\n".join(current_content).strip()
        if not content:
            return
        segments.append(
            Segment(
                segment_id=stable_id("seg", source_path, ordinal, current_heading),
                ordinal=ordinal,
                heading=current_heading,
                heading_path=list(heading_stack),
                level=current_level,
                content=content,
            )
        )
        ordinal += 1

    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            flush()
            level = len(match.group(1))
            heading = markdown_to_plain(match.group(2))
            heading_stack = heading_stack[: level - 1] + [heading]
            current_heading = heading
            current_level = level
            current_content = []
            continue
        current_content.append(line)
    flush()
    return segments


def iter_markdown_files(root: Path, include_roots: Sequence[str]) -> Iterable[Tuple[str, Path]]:
    for include_root in include_roots:
        base = root / include_root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.md")):
            if path.is_file():
                yield include_root, path


def load_documents(root: Path, include_roots: Sequence[str]) -> List[Document]:
    documents: List[Document] = []
    for source_kind, path in iter_markdown_files(root, include_roots):
        text = path.read_text(encoding="utf-8")
        rel_path = path.relative_to(root).as_posix()
        title = derive_title(path, text)
        episode_no, part_no, sequence_no = guess_episode_part(path)
        meta = extract_meta(text.splitlines())
        segments = build_segments(rel_path, text, title)
        stat = path.stat()
        documents.append(
            Document(
                source_id=stable_id("src", rel_path),
                source_kind=source_kind,
                source_path=rel_path,
                title=title,
                text=text,
                summary=extract_summary(text),
                episode_no=episode_no,
                part_no=part_no,
                sequence_no=sequence_no,
                meta=meta,
                topics=infer_topics(text),
                segments=segments,
                modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                .replace(microsecond=0)
                .isoformat(),
                content_hash=hashlib.sha1(text.encode("utf-8")).hexdigest(),
            )
        )
    return documents


def split_listish(value: str) -> List[str]:
    cleaned = markdown_to_plain(value).replace("／", "/").replace("・", "、")
    parts = re.split(r"[、,/\n]|(?:\s{2,})", cleaned)
    result: List[str] = []
    for part in parts:
        item = normalize_entity_name(part)
        if item and item not in result:
            result.append(item)
    return result


def normalize_entity_name(name: str) -> str:
    value = markdown_to_plain(name)
    value = re.sub(r"^[\-*・\s]+", "", value)
    value = re.sub(r"\s*\(.+?\)\s*$", "", value)
    value = value.replace("　", "")
    if re.search(r"[一-龯ぁ-んァ-ヶ]", value):
        value = re.sub(r"\s+", "", value)
    for suffix in RANK_SUFFIXES:
        if value.endswith(suffix) and len(value) > len(suffix) + 1:
            value = value[: -len(suffix)]
            break
    value = value.strip(" ：:-")
    if value in IGNORE_VALUES:
        return ""
    return value


def is_entity_like(name: str) -> bool:
    value = normalize_entity_name(name)
    if not value or value in GENERIC_TITLES or value in STOP_ENTITY_NAMES or value in CHARACTER_KEYS:
        return False
    if len(value) < 2 or len(value) > 40:
        return False
    if re.fullmatch(r"(?:19|20)\d{2}年?", value):
        return False
    if any(char in value for char in ("「", "」", "。", "？", "!", "?")):
        return False
    if value.endswith(("話", "場", "概要", "役割", "要点")):
        return False
    if re.fullmatch(r"[0-9A-Za-z ._-]+", value):
        return any(char.isdigit() for char in value) or len(value) >= 4
    return bool(re.search(r"[一-龯ぁ-んァ-ヶA-Z]", value))


def infer_entity_type(name: str, context: str, key_hint: Optional[str] = None) -> str:
    value = normalize_entity_name(name)
    combined = f"{key_hint or ''} {context} {value}".lower()
    if value.endswith(("小隊", "分隊", "連隊", "司令部", "本部", "大隊", "班")):
        return "organization"
    if key_hint in CHARACTER_KEYS or any(token in combined for token in ("人物", "来歴", "隊員", "士官", "分隊長", "関係")):
        return "character"
    if key_hint in ORG_KEYS or any(token in combined for token in ("連隊", "小隊", "部隊", "司令部", "軍", "勢力", "regiment")):
        return "organization"
    if key_hint in PLACE_KEYS or any(token in combined for token in ("戦線", "方面", "基地", "location", "廃村", "村", "front", "lz")):
        return "place"
    if key_hint in VEHICLE_KEYS or any(token in combined for token in ("車両", "装甲", "輸送機", "helicopter", "apc", "mrap", "uh-60", "an-12")):
        return "vehicle"
    if key_hint in WEAPON_KEYS or any(token in combined for token in ("武装", "小銃", "ライフル", "散弾", "ランチャー", "斧", "術式", "弾頭")):
        if "術式" in combined:
            return "machine"
        return "weapon"
    if any(token in combined for token in ("魔術", "術式", "触媒", "機材", "記録媒体", "ドローン", "装置")):
        return "machine"
    return "term"


def extract_candidate_map(documents: Sequence[Document]) -> Dict[str, Dict[str, object]]:
    candidates: Dict[str, Dict[str, object]] = {}

    def add_candidate(
        raw_name: str,
        context: str,
        source_path: str,
        source_kind: str,
        key_hint: Optional[str] = None,
    ) -> None:
        name = normalize_entity_name(raw_name)
        if not is_entity_like(name):
            return
        record = candidates.setdefault(
            name,
            {
                "aliases": set(),
                "types": [],
                "sources": set(),
                "facts": [],
                "source_kinds": set(),
            },
        )
        if raw_name.strip() and raw_name.strip() != name:
            record["aliases"].add(raw_name.strip())
        record["types"].append(infer_entity_type(name, context, key_hint))
        record["sources"].add(source_path)
        record["source_kinds"].add(source_kind)
        snippet = normalize_ws(markdown_to_plain(context))[:160]
        if snippet and snippet not in record["facts"] and len(record["facts"]) < 5:
            record["facts"].append(snippet)

    for doc in documents:
        if doc.source_kind == "canon" and is_entity_like(doc.title):
            add_candidate(doc.title, f"{doc.title}\n{doc.summary}", doc.source_path, doc.source_kind)
        for key, value in doc.meta.items():
            for item in split_listish(value):
                add_candidate(item, f"{key}: {value}", doc.source_path, doc.source_kind, key)
        for segment in doc.segments:
            if doc.source_kind == "canon" and segment.heading not in GENERIC_TITLES:
                add_candidate(segment.heading, " > ".join(segment.heading_path), doc.source_path, doc.source_kind)
            for line in segment.content.splitlines():
                bullet_match = BULLET_KV_RE.match(line)
                if bullet_match:
                    key = markdown_to_plain(bullet_match.group(1))
                    value = bullet_match.group(2)
                    for item in split_listish(value):
                        add_candidate(item, line, doc.source_path, doc.source_kind, key)
                    continue
                for bold in BOLD_RE.findall(line):
                    add_candidate(bold, line, doc.source_path, doc.source_kind)
    return candidates


def choose_primary_type(type_list: Sequence[str]) -> str:
    priority = ["character", "organization", "place", "vehicle", "weapon", "machine", "term"]
    for entity_type in priority:
        if entity_type in type_list:
            return entity_type
    return "term"


def find_best_date(text: str) -> Tuple[Optional[str], Optional[str]]:
    iso_match = ISO_DATE_RE.search(text)
    if iso_match:
        date_text = "-".join(iso_match.groups())
        return date_text, date_text
    jp_match = JP_DATE_RE.search(text)
    if jp_match:
        year = int(jp_match.group(1))
        month = int(jp_match.group(2))
        day = int(jp_match.group(3) or 1)
        date_start = f"{year:04d}-{month:02d}-{day:02d}"
        date_text = f"{year}年{month}月"
        if jp_match.group(3):
            date_text += f"{day}日"
        return date_text, date_start
    year_match = YEAR_RE.search(text)
    if year_match:
        year = int(year_match.group(1))
        return f"{year}年", f"{year:04d}-01-01"
    return None, None


def build_relation_map(documents: Sequence[Document], entity_name_map: Dict[str, str]) -> Dict[str, List[Dict[str, str]]]:
    relation_map: Dict[str, List[Dict[str, str]]] = {}
    for doc in documents:
        for segment in doc.segments:
            relation_match = RELATION_SECTION_RE.match(segment.heading)
            if not relation_match:
                continue
            target_name = normalize_entity_name(relation_match.group(1))
            if target_name not in entity_name_map:
                continue
            parent_candidates = [part for part in segment.heading_path[:-1] if normalize_entity_name(part) in entity_name_map]
            if not parent_candidates:
                continue
            source_name = normalize_entity_name(parent_candidates[-1])
            if source_name == target_name:
                continue
            note = normalize_ws(markdown_to_plain(segment.content))[:140]
            relation_map.setdefault(source_name, []).append(
                {"target_name": target_name, "type": "related_to", "note": note}
            )
    return relation_map


def build_entity_records(documents: Sequence[Document]) -> List[Dict[str, object]]:
    candidates = extract_candidate_map(documents)
    entity_name_map = {name: stable_id("ent", name) for name in candidates.keys()}
    relation_map = build_relation_map(documents, entity_name_map)
    records: List[Dict[str, object]] = []
    for name in sorted(candidates.keys()):
        record = candidates[name]
        entity_type = choose_primary_type(record["types"])
        source_paths = sorted(record["sources"])
        records.append(
            {
                "entity_id": entity_name_map[name],
                "entity_type": entity_type,
                "canonical_name": name,
                "aliases_json": json.dumps(sorted(record["aliases"]), ensure_ascii=False),
                "summary": record["facts"][0] if record["facts"] else name,
                "facts_json": json.dumps(record["facts"][:5], ensure_ascii=False),
                "attributes_json": json.dumps({"source_kinds": sorted(record["source_kinds"])}, ensure_ascii=False),
                "relations_json": json.dumps(relation_map.get(name, []), ensure_ascii=False),
                "source_paths_json": json.dumps(source_paths, ensure_ascii=False),
                "first_source_path": source_paths[0] if source_paths else None,
                "latest_source_path": source_paths[-1] if source_paths else None,
                "mention_count": 0,
                "confidence": 0.8 if entity_type == "term" else 1.0,
            }
        )
    return records


def collect_mentions(
    documents: Sequence[Document],
    entity_records: Sequence[Dict[str, object]],
) -> Tuple[List[Dict[str, object]], Dict[str, List[Tuple[str, int]]]]:
    sorted_entities = sorted(
        ((str(record["canonical_name"]), str(record["entity_id"])) for record in entity_records),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    mentions: List[Dict[str, object]] = []
    source_entity_counts: Dict[str, List[Tuple[str, int]]] = {}
    for doc in documents:
        counts: Dict[str, int] = {}
        for segment in doc.segments:
            plain = markdown_to_plain(segment.content)
            for name, entity_id in sorted_entities:
                count = plain.count(name)
                if count <= 0:
                    continue
                counts[entity_id] = counts.get(entity_id, 0) + count
                mentions.append(
                    {
                        "mention_id": stable_id("men", doc.source_id, segment.segment_id, entity_id),
                        "entity_id": entity_id,
                        "source_id": doc.source_id,
                        "source_path": doc.source_path,
                        "segment_id": segment.segment_id,
                        "snippet": plain[:220],
                        "mention_count": count,
                    }
                )
        source_entity_counts[doc.source_id] = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return mentions, source_entity_counts


def infer_thread_type(text: str) -> str:
    if "謎" in text:
        return "mystery"
    if "匂わせ" in text or "布石" in text or "示唆" in text:
        return "foreshadow_candidate"
    return "unresolved"


def build_thread_records(
    documents: Sequence[Document],
    source_entity_counts: Dict[str, List[Tuple[str, int]]],
) -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []
    for doc in documents:
        top_entities = [entity_id for entity_id, _ in source_entity_counts.get(doc.source_id, [])[:6]]
        for segment in doc.segments:
            plain = markdown_to_plain(segment.content)
            if not any(marker in plain or marker in segment.heading for marker in THREAD_MARKERS):
                continue
            title = segment.heading if segment.heading not in GENERIC_TITLES else (plain[:40] or doc.title)
            records.append(
                {
                    "thread_id": stable_id("thr", doc.source_id, segment.segment_id),
                    "thread_type": infer_thread_type(f"{segment.heading} {plain}"),
                    "title": title,
                    "description": plain[:280],
                    "source_id": doc.source_id,
                    "source_path": doc.source_path,
                    "related_entities_json": json.dumps(top_entities, ensure_ascii=False),
                    "status": "open",
                    "evidence_text": plain[:320],
                }
            )
    return records


def build_event_records(
    documents: Sequence[Document],
    entity_records: Sequence[Dict[str, object]],
    source_entity_counts: Dict[str, List[Tuple[str, int]]],
) -> List[Dict[str, object]]:
    entity_type_by_id = {str(record["entity_id"]): str(record["entity_type"]) for record in entity_records}
    events: List[Dict[str, object]] = []
    for doc in documents:
        related_entities = [entity_id for entity_id, _ in source_entity_counts.get(doc.source_id, [])[:8]]
        related_objects = [
            entity_id
            for entity_id in related_entities
            if entity_type_by_id.get(entity_id) in {"vehicle", "weapon", "machine"}
        ][:6]
        date_text, date_start = find_best_date(" ".join([doc.meta.get("Date", ""), doc.text]))
        canonical_level = {"canon": "canon", "posts": "post", "drafts": "draft"}.get(doc.source_kind, doc.source_kind)
        if doc.source_kind == "posts":
            event_type = "post"
        elif doc.source_kind == "drafts" and "plot" in doc.source_path.lower():
            event_type = "plot"
        elif doc.source_kind == "drafts":
            event_type = "draft"
        else:
            event_type = "reference"
        events.append(
            {
                "event_id": stable_id("evt", doc.source_id),
                "event_type": event_type,
                "title": doc.title,
                "summary": (doc.summary or markdown_to_plain(doc.text)[:220])[:320],
                "source_kind": doc.source_kind,
                "source_id": doc.source_id,
                "source_path": doc.source_path,
                "date_text": date_text,
                "date_start": date_start,
                "sequence_no": doc.sequence_no,
                "canonical_level": canonical_level,
                "related_entities_json": json.dumps(related_entities, ensure_ascii=False),
                "related_objects_json": json.dumps(related_objects, ensure_ascii=False),
                "location_text": doc.meta.get("Location"),
                "consequences_json": json.dumps([], ensure_ascii=False),
                "tags_json": json.dumps(doc.topics, ensure_ascii=False),
            }
        )
    return events


def build_source_records(
    documents: Sequence[Document],
    source_entity_counts: Dict[str, List[Tuple[str, int]]],
    events: Sequence[Dict[str, object]],
    threads: Sequence[Dict[str, object]],
) -> List[Dict[str, object]]:
    event_counts: Dict[str, int] = {}
    for event in events:
        event_counts[str(event["source_id"])] = event_counts.get(str(event["source_id"]), 0) + 1
    thread_counts: Dict[str, int] = {}
    for thread in threads:
        thread_counts[str(thread["source_id"])] = thread_counts.get(str(thread["source_id"]), 0) + 1

    records: List[Dict[str, object]] = []
    for doc in documents:
        key_entities = [entity_id for entity_id, _ in source_entity_counts.get(doc.source_id, [])[:8]]
        records.append(
            {
                "source_id": doc.source_id,
                "source_kind": doc.source_kind,
                "source_path": doc.source_path,
                "title": doc.title,
                "episode_no": doc.episode_no,
                "part_no": doc.part_no,
                "sequence_no": doc.sequence_no,
                "summary": doc.summary,
                "meta_json": json.dumps(doc.meta, ensure_ascii=False),
                "topics_json": json.dumps(doc.topics, ensure_ascii=False),
                "key_entities_json": json.dumps(key_entities, ensure_ascii=False),
                "event_count": event_counts.get(doc.source_id, 0),
                "thread_count": thread_counts.get(doc.source_id, 0),
                "content_hash": doc.content_hash,
                "modified_at": doc.modified_at,
            }
        )
    return records


def build_segment_records(
    documents: Sequence[Document],
    source_entity_counts: Dict[str, List[Tuple[str, int]]],
) -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []
    for doc in documents:
        likely_entities = [entity_id for entity_id, _ in source_entity_counts.get(doc.source_id, [])[:12]]
        for segment in doc.segments:
            plain = markdown_to_plain(segment.content)
            markers = [marker for marker in THREAD_MARKERS if marker in plain or marker in segment.heading]
            records.append(
                {
                    "segment_id": segment.segment_id,
                    "source_id": doc.source_id,
                    "source_path": doc.source_path,
                    "ordinal": segment.ordinal,
                    "heading": segment.heading,
                    "heading_path": " > ".join(segment.heading_path),
                    "content_text": plain[:4000],
                    "summary": plain[:240],
                    "topics_json": json.dumps(infer_topics(f"{segment.heading}\n{plain}"), ensure_ascii=False),
                    "entities_json": json.dumps(likely_entities, ensure_ascii=False),
                    "thread_markers_json": json.dumps(markers, ensure_ascii=False),
                }
            )
    return records


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;

        CREATE TABLE source_cards (
            source_id TEXT PRIMARY KEY,
            source_kind TEXT NOT NULL,
            source_path TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            episode_no INTEGER,
            part_no INTEGER,
            sequence_no INTEGER NOT NULL DEFAULT 0,
            summary TEXT NOT NULL,
            meta_json TEXT NOT NULL,
            topics_json TEXT NOT NULL,
            key_entities_json TEXT NOT NULL,
            event_count INTEGER NOT NULL DEFAULT 0,
            thread_count INTEGER NOT NULL DEFAULT 0,
            content_hash TEXT NOT NULL,
            modified_at TEXT NOT NULL
        );

        CREATE TABLE source_segments (
            segment_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            source_path TEXT NOT NULL,
            ordinal INTEGER NOT NULL,
            heading TEXT NOT NULL,
            heading_path TEXT NOT NULL,
            content_text TEXT NOT NULL,
            summary TEXT NOT NULL,
            topics_json TEXT NOT NULL,
            entities_json TEXT NOT NULL,
            thread_markers_json TEXT NOT NULL,
            FOREIGN KEY(source_id) REFERENCES source_cards(source_id) ON DELETE CASCADE
        );

        CREATE TABLE entity_cards (
            entity_id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            canonical_name TEXT NOT NULL UNIQUE,
            aliases_json TEXT NOT NULL,
            summary TEXT NOT NULL,
            facts_json TEXT NOT NULL,
            attributes_json TEXT NOT NULL,
            relations_json TEXT NOT NULL,
            source_paths_json TEXT NOT NULL,
            first_source_path TEXT,
            latest_source_path TEXT,
            mention_count INTEGER NOT NULL DEFAULT 0,
            confidence REAL NOT NULL DEFAULT 1.0,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE entity_mentions (
            mention_id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            source_path TEXT NOT NULL,
            segment_id TEXT,
            snippet TEXT NOT NULL,
            mention_count INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(entity_id) REFERENCES entity_cards(entity_id) ON DELETE CASCADE,
            FOREIGN KEY(source_id) REFERENCES source_cards(source_id) ON DELETE CASCADE,
            FOREIGN KEY(segment_id) REFERENCES source_segments(segment_id) ON DELETE SET NULL
        );

        CREATE TABLE event_cards (
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
            related_entities_json TEXT NOT NULL,
            related_objects_json TEXT NOT NULL,
            location_text TEXT,
            consequences_json TEXT NOT NULL,
            tags_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(source_id) REFERENCES source_cards(source_id) ON DELETE CASCADE
        );

        CREATE TABLE thread_cards (
            thread_id TEXT PRIMARY KEY,
            thread_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            source_id TEXT NOT NULL,
            source_path TEXT NOT NULL,
            related_entities_json TEXT NOT NULL,
            status TEXT NOT NULL,
            evidence_text TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(source_id) REFERENCES source_cards(source_id) ON DELETE CASCADE
        );

        CREATE TABLE extraction_runs (
            run_id TEXT PRIMARY KEY,
            schema_version TEXT NOT NULL,
            include_roots_json TEXT NOT NULL,
            source_count INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            notes_json TEXT NOT NULL
        );

        CREATE INDEX idx_source_cards_kind_seq ON source_cards(source_kind, sequence_no, source_path);
        CREATE INDEX idx_entity_cards_type_name ON entity_cards(entity_type, canonical_name);
        CREATE INDEX idx_entity_mentions_source ON entity_mentions(source_id, entity_id);
        CREATE INDEX idx_event_cards_timeline ON event_cards(date_start, sequence_no, source_path);
        CREATE INDEX idx_thread_cards_status ON thread_cards(status, source_path);

        CREATE VIEW v_entity_lookup AS
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
        FROM entity_cards;

        CREATE VIEW v_open_threads AS
        SELECT
            thread_id,
            thread_type,
            title,
            description,
            source_path,
            related_entities_json,
            status,
            updated_at
        FROM thread_cards
        WHERE status = 'open';

        CREATE VIEW v_source_lookup AS
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
        FROM source_cards;

        CREATE VIEW v_event_timeline AS
        SELECT
            event_id,
            date_start,
            title,
            canonical_level,
            source_path,
            summary
        FROM event_cards
        WHERE date_start IS NOT NULL;
        """
    )


def insert_records(conn: sqlite3.Connection, table: str, records: Sequence[Dict[str, object]]) -> None:
    if not records:
        return
    columns = list(records[0].keys())
    placeholders = ", ".join("?" for _ in columns)
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
    conn.executemany(sql, ([record[column] for column in columns] for record in records))


def update_entity_counts(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        UPDATE entity_cards
        SET mention_count = COALESCE(
            (
                SELECT SUM(mention_count)
                FROM entity_mentions m
                WHERE m.entity_id = entity_cards.entity_id
            ),
            0
        )
        """
    )


def build_database(conn: sqlite3.Connection, root: Path, include_roots: Sequence[str]) -> None:
    started_at = now_iso()
    run_id = stable_id("run", started_at, ",".join(include_roots))
    conn.execute(
        """
        INSERT INTO extraction_runs (
            run_id, schema_version, include_roots_json, source_count, started_at, completed_at, notes_json
        ) VALUES (?, ?, ?, 0, ?, NULL, ?)
        """,
        (run_id, "story_cards_v1", json.dumps(list(include_roots), ensure_ascii=False), started_at, "{}"),
    )

    documents = load_documents(root, include_roots)
    entity_records = build_entity_records(documents)
    mentions, source_entity_counts = collect_mentions(documents, entity_records)
    thread_records = build_thread_records(documents, source_entity_counts)
    event_records = build_event_records(documents, entity_records, source_entity_counts)
    source_records = build_source_records(documents, source_entity_counts, event_records, thread_records)
    segment_records = build_segment_records(documents, source_entity_counts)
    timestamp = now_iso()

    for record in entity_records:
        record["updated_at"] = timestamp
    for record in event_records:
        record["updated_at"] = timestamp
    for record in thread_records:
        record["updated_at"] = timestamp

    insert_records(conn, "source_cards", source_records)
    insert_records(conn, "source_segments", segment_records)
    insert_records(conn, "entity_cards", entity_records)
    insert_records(conn, "entity_mentions", mentions)
    insert_records(conn, "event_cards", event_records)
    insert_records(conn, "thread_cards", thread_records)
    update_entity_counts(conn)
    conn.execute(
        """
        UPDATE extraction_runs
        SET source_count = ?, completed_at = ?, notes_json = ?
        WHERE run_id = ?
        """,
        (
            len(documents),
            now_iso(),
            json.dumps(
                {
                    "entity_count": len(entity_records),
                    "event_count": len(event_records),
                    "thread_count": len(thread_records),
                },
                ensure_ascii=False,
            ),
            run_id,
        ),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild story reference SQLite as LLM-friendly card storage."
    )
    parser.add_argument(
        "--db",
        default="reports/story_master.sqlite3",
        help="Output SQLite file path relative to repository root.",
    )
    parser.add_argument(
        "--include",
        default="canon,drafts,posts",
        help="Comma-separated roots to index (default: canon,drafts,posts).",
    )
    parser.add_argument(
        "--keep-db",
        action="store_true",
        help="Accepted for compatibility. The database is always rebuilt from scratch.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    db_path = (root / args.db).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    include_roots = [part.strip() for part in str(args.include).split(",") if part.strip()]
    if not include_roots:
        raise SystemExit("include roots must not be empty")

    tmp_fd, tmp_name = tempfile.mkstemp(suffix=".sqlite3", dir=str(db_path.parent))
    os.close(tmp_fd)
    Path(tmp_name).unlink(missing_ok=True)
    try:
        conn = sqlite3.connect(tmp_name)
        try:
            init_schema(conn)
            build_database(conn, root, include_roots)
            conn.commit()
        finally:
            conn.close()
        if db_path.exists():
            db_path.unlink()
        shutil.move(tmp_name, db_path)
    finally:
        Path(tmp_name).unlink(missing_ok=True)
        Path(f"{tmp_name}-journal").unlink(missing_ok=True)
        Path(f"{tmp_name}-wal").unlink(missing_ok=True)
        Path(f"{tmp_name}-shm").unlink(missing_ok=True)

    print(f"db={db_path}")
    print("schema=story_cards_v1")
    print(f"include={','.join(include_roots)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
