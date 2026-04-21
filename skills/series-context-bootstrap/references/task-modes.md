# Task Modes

Classify the request before loading files.

## 1. Bootstrap Only

Use when the user wants a fast orientation, repo map, current status, or reading plan.

Typical prompts:

- "rebuild the context for this series"
- "summarize the current story state"
- "tell me what to read to catch up"

Read only enough to build a briefing.

## 2. Bootstrap To Draft

Use when the user wants to draft, revise, or continue an episode but the current thread lacks context.

After the briefing, switch to `../serialized-fiction-draft-partner/SKILL.md`.

Bias toward:

- current arc role
- latest published episode
- any current draft or plot file
- local prose temperature

## 3. Bootstrap To Continuity Check

Use when the user wants validation, contradiction detection, or canon safety before writing.

After the briefing, switch to `../story-setting-consistency-check/SKILL.md`.

Bias toward:

- canon files named in the request
- relevant numbered canon files
- the candidate draft or note to be checked

## 4. Bootstrap To Planning

Use when the user wants to decide what happens next rather than draft full prose yet.

Bias toward:

- current arc flow docs
- unresolved threads from recent posts
- any draft plot notes in `drafts/`

Produce a briefing that ends with the most likely next decision points, not with prose advice.