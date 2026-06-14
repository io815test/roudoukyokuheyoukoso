---
name: character-profile-updater
description: Update character canon for this Labor Bureau fiction project from new decisions or draft material. Use when adding a new character, changing appearance, voice, motives, relationships, weaknesses, abilities, or when propagating a character decision into the character matrix and individual profile files.
---

# Character Profile Updater

Use this skill to move character decisions from conversation or drafts into canon without flattening nuance.

## Source Order

1. User's latest explicit decision.
2. Current draft passages that show the character in action.
3. `canon/00_人物比較マトリクス.md`
4. Existing individual profile under `canon/reference/characters/` if one exists.
5. Arc notes such as `drafts/reference/第二部_適正処理済_企画メモ.md`.

Latest explicit user decisions win over older drafts unless the user says otherwise.

## Update Targets

- Always update `canon/00_人物比較マトリクス.md` for recurring characters.
- Create or update an individual profile when the character has enough stable material to justify it.
- Update `canon/world-setting.md` only if adding a new profile file to the canon index.
- Do not bury character decisions only inside draft prose.

## What To Preserve

- exact relationship nuance
- voice and register
- contradictions that are intentional character tension
- uncertainty labels such as "未確定", "仮置き", or "可能性"

## Matrix Checklist

For each recurring character, consider:

- identification and affiliation
- one-line summary
- appearance
- personality and thinking core
- abilities
- weaknesses
- role relative to Labor Bureau
- relationship matrix entries
- speech style and example lines
- background notes

## Response Contract

When editing, finish with:

- files changed
- what character facts were added
- any uncertainties left for later

If a profile file is not created, say why.
