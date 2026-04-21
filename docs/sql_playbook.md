# SQL Playbook (LLM-Oriented)

LLMが長期シリーズの整合性確認や文脈再構築を行うときに使う、固定SQLテンプレート集。
原則として、まず `v_*_curated` を使い、必要時だけ生テーブルへ降りる。

## 1) 年表（低ノイズ）

```sql
SELECT
  event_id,
  date_start,
  title,
  canonical_level,
  category_codes,
  source_path,
  source_line_no
FROM v_timeline_curated
ORDER BY date_start ASC, event_id ASC
LIMIT 300;
```

## 2) 人物ファクトカード（canon優先）

```sql
SELECT
  entity_name,
  fact_type,
  fact_text,
  date_start,
  fact_origin,
  confidence,
  has_open_conflict,
  source_path,
  source_line_no
FROM v_character_facts_curated
WHERE entity_name = :entity_name
ORDER BY
  CASE fact_origin WHEN 'canon' THEN 0 ELSE 1 END,
  date_start,
  source_line_no;
```

## 3) 矛盾・要確認の監査結果

```sql
SELECT
  run_id,
  run_scope,
  candidate_path,
  gate_result,
  contradiction_count,
  needs_confirmation_count,
  canon_mismatch_count,
  ripple_risk_count
FROM v_consistency_gate
ORDER BY run_id DESC;
```

```sql
SELECT
  run_scope,
  label,
  severity,
  summary,
  source_path,
  source_line_no,
  canon_source_path,
  canon_line_no
FROM v_consistency_findings
WHERE status = 'open'
ORDER BY severity DESC, finding_id DESC
LIMIT 200;
```

## 4) 伏線の未回収確認

```sql
SELECT
  thread_id,
  title,
  thread_status,
  introduced_source_path,
  introduced_line_no,
  owner_entity_name
FROM v_foreshadow_status
WHERE thread_status IN ('planned', 'planted', 'active')
ORDER BY thread_id DESC;
```

## 5) 設定メモ検索（JSON-KV）

```sql
SELECT
  kv_id,
  topic,
  key_name,
  value_text,
  canonical_level,
  source_path,
  source_line_no
FROM v_story_kv
WHERE topic = :topic
ORDER BY kv_id DESC
LIMIT 200;
```

```sql
SELECT
  kv.kv_id,
  kv.topic,
  kv.key_name,
  kv.value_text,
  src.path AS source_path,
  kv.source_line_no
FROM t_story_kv kv
LEFT JOIN t_sources src ON src.source_id = kv.source_id
WHERE kv.kv_id IN (
  SELECT rowid
  FROM fts_story_kv
  WHERE fts_story_kv MATCH :query
  LIMIT 200
)
ORDER BY kv.kv_id DESC;
```

## 6) 勢力サマリー

```sql
SELECT
  faction_id,
  short_name,
  formal_name_ja,
  troop_strength,
  protagonist_affinity_level,
  tech_level,
  hq_location_name,
  primary_regional_command_name,
  current_member_count
FROM v_faction_overview
ORDER BY faction_id;
```

## 7) 推奨実行順（LLM）

1. `v_consistency_gate` / `v_consistency_findings` で危険箇所を把握。
2. `v_timeline_curated` で時系列の骨格を取得。
3. `v_character_facts_curated` で登場人物の確定情報を取得。
4. 必要に応じて `v_story_kv` / `fts_story_kv` で補助情報を掘る。
