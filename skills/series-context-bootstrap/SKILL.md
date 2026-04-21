---
name: series-context-bootstrap
description: Rapidly reconstruct working context for a long-running fiction repository without rereading the whole project. Use when starting a new thread, resuming after a gap, preparing to draft or revise an episode, locating the minimum canon and recent chapters needed for a task, or producing a compact project briefing that can hand off cleanly to drafting or continuity-check workflows.
---

# Series Context Bootstrap

Use this skill to rebuild only the context needed for the current task.

Do not start by rereading the whole series. Read the smallest authoritative slice, summarize it into a reusable briefing, then hand off to the right next workflow.

## Workflow

1. Identify the task shape first using [references/task-modes.md](references/task-modes.md).
2. Read files in the minimum order described in [references/reading-order.md](references/reading-order.md).
3. Build a compact briefing using [references/briefing-format.md](references/briefing-format.md).
4. If the user wants drafting, hand off to [../serialized-fiction-draft-partner/SKILL.md](../serialized-fiction-draft-partner/SKILL.md).
5. If the user wants canon validation or if you detect unsupported assumptions, hand off to [../story-setting-consistency-check/SKILL.md](../story-setting-consistency-check/SKILL.md).

## Default Repository Assumptions

- `canon/world-setting.md` is the canon entrypoint or index.
- Numbered files under `canon/` are stronger sources for their topics than short summary mentions elsewhere.
- `posts/` contains released episode text and should be treated as the main recent-story record.
- `drafts/` contains forward-looking plans, draft episodes, and development notes.
- Read full episodes only when the current task depends on scene-level carryover, voice matching, or emotional residue.

## Output Contract

Unless the user asks for something looser, produce a short briefing with:

- task mode
- sources read
- world and conflict snapshot
- current timeline and character-state snapshot
- recent tone and carryover
- open threads and unresolved risks
- recommended next files
- recommended next skill or next action

Keep it compact enough that a later thread can reuse it directly.

## Scope Discipline

- Prefer indexed canon and summaries before full prose rereads.
- Treat briefing as a working map, not as a rewrite of project documents.
- Separate confirmed canon from inference and from episode-local speculation.
- Flag uncertainty explicitly instead of smoothing it over.
- When several files could answer the task, read the most authoritative and most recent first.
- If the briefing exposes a likely contradiction, stop pretending the context is settled and switch to the continuity-check skill.

## Handoff Rules

- Use this skill first for prompts such as:
  - "rebuild the context for a new thread"
  - "give me a quick story-state briefing"
  - "tell me what to read before drafting next"
  - "show what is still unresolved"
- Use `serialized-fiction-draft-partner` after the briefing when the user wants prose drafting or revision.
- Use `story-setting-consistency-check` after the briefing when the user wants validation, or when you detect canon drift during context building.

## Resources

- [references/task-modes.md](references/task-modes.md): classify the request before reading files.
- [references/reading-order.md](references/reading-order.md): choose the minimum useful file set.
- [references/briefing-format.md](references/briefing-format.md): structure the reusable context briefing.