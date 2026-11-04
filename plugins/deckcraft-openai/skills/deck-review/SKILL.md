---
name: deck-review
description: "Review PowerPoint content, layout, editability and motion with measured checks and visual previews. Use for presentation reviews without modifying the original."
---

## Codex / ChatGPT Work runtime
Read `../../RUNTIME.md` before running scripts. Resolve sibling paths from this installed skill directory, never the current working directory. Keep generated files in the task workspace, outside the installed plugin. Preserve user reference art and interactive behavior. Do not commit, publish, install software, or update the plugin as part of creating a deck unless the user authorizes that action.


# /deck-review — presentation critique

Paths are relative to the skill's base; engine `../pptx-morph/scripts`. You do not change the presentation — report only.

## 1. Gather the material
```
from morphkit.existing import Deck
from morphkit.qa import render, contact_sheet, xsd_check, lo_effects_check
from morphkit.motion import preview
d = Deck(path); slides = d.to_slides()
pngs = render(path, out/"png"); contact_sheet(pngs, out/"sheet.png")
preview(slides, d.theme, out/"motion", gif=False)        # frame strips of every transition
```
`to_slides()` is a sketch: scheme colors without tints, pictures as grey frames. For morphkit presentations use the real `Slide` objects.
Plus `d.report()` (pairs, transitions, effects), `xsd_check`, `lo_effects_check`.

## 2. Assess
Look at the thumbnails as an unfamiliar viewer, then point by point:
- **First impression** — what is visible in 2 seconds, are the topic and style clear.
- **Readability** — font size, line length, overflow, contrast (≥ 4.5:1 for text, ≥ 3:1 for large text).
- **Hierarchy** — one focus, three levels, a takeaway headline.
- **Consistency** — one navigation, one transition type between sections, style lock, grid.
- **Presentation rhythm** — density changes, a “wow” per section, the beginning and end rhyme (`../pptx-design/references/rhythm.md`).
- **Motion** — from the strips: each transition has a meaning, shapes do not fly across text, no identical techniques in a row,
  Morph ≤ 0.9 s, loops only on processes, no rejected techniques (`../pptx-morph/references/techniques.md`).
- **Anti-patterns** — `../pptx-design/references/design-system.md` §6.
If the Design plugin is installed (`design:design-critique`, `design:accessibility-review`) — use its structure.

## 3. Report
First 2–3 strengths (do not touch them when fixing). Then a table:
`severity (critical / noticeable / minor) · slide · what is visible · why it gets in the way · fix · tool`.
No more than 12 rows, critical ones on top. At the end: “Fix it? — /deck-remix will do items 1–N”.
Attach the thumbnail sheet and 1–2 motion strips showing the problem (inline image previews).

_Russian original: SKILL.ru.md_
