---
name: deck-review
description: "Designer-style critique of any .pptx: thumbnails, a motion sketch of every transition, measurements (text overflow, contrast, overlaps, Morph pairs, durations), a design checklist and critique dimensions, with a severity table and concrete fixes; fixes via /deck-remix. / Критика .pptx (своей или чужой) как у дизайнера: рендер и лист миниатюр, эскиз движения каждого перехода, замеры (переполнение текста, контраст, наложения, пары Morph, длительности), чек-лист pptx-design (фокус, иерархия, шапки, ритм, «вау» раздела, антишаблоны) и измерения критики Design (первое впечатление, читаемость, иерархия, единообразие, доступность) — с таблицей серьёзности и конкретными правками. Правки по согласию — через /deck-remix."
argument-hint: "[.pptx]"
---

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
Attach the thumbnail sheet and 1–2 motion strips showing the problem (SendUserFile, render).

_Russian original: SKILL.ru.md_
