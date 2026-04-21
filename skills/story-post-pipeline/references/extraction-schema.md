# Extraction Schema

Use one JSON file per post.

## Path Rule

- source markdown: `posts/episode-04-part-01.md`
- extraction JSON: `reports/extractions/episode-04/part-01.json`

## JSON Shape

```json
{
  "source_path": "posts/episode-04-part-01.md",
  "post_id": "episode-04-part-01",
  "summary": "Short factual summary of this post.",
  "entities": [
    {
      "name": "榊恒一",
      "type": "character",
      "summary": "Optional one-line description for this post only.",
      "facts": [
        "現地判断を任される"
      ]
    }
  ],
  "events": [
    {
      "title": "回収任務のブリーフィング",
      "type": "mission",
      "summary": "任務内容と優先順位が説明される",
      "actors": ["榊恒一", "小隊長"],
      "location": "FOBアンヴィル"
    }
  ],
  "threads": [
    {
      "title": "墜落原因未確定",
      "type": "unresolved",
      "description": "事故か攻撃か断定できていない",
      "status": "open"
    }
  ]
}
```

## Field Rules

### `summary`

- 1 to 3 short sentences
- factual only

### `entities[].type`

Use one of:

- `character`
- `organization`
- `place`
- `vehicle`
- `weapon`
- `machine`
- `term`

### `events[].type`

Prefer short labels such as:

- `mission`
- `battle`
- `move`
- `briefing`
- `reveal`
- `injury`
- `recovery`

### `threads[].type`

Use one of:

- `unresolved`
- `mystery`
- `foreshadow_candidate`

Only use `foreshadow_candidate` when the text itself supports that reading.

## Exclusions

Do not emit these as structured fields unless the user explicitly extends the schema:

- theme
- symbolism
- author_intent
- hidden_emotion
- hard foreshadowing claims
