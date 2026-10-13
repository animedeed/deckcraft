---
name: deck-remix
description: "Improves an existing .pptx without rebuilding it your own way: inventory, a list of edits with reasons, edits via morphkit.existing.Deck (transition speed, text re-flow, signals along lines, staggered entrances, graph edges without crossings), checks and before/after motion sketches. / Доработка существующей .pptx пользователя без пересборки «по-своему»: инвентарь (фигуры, пары Morph, переходы, эффекты), список правок с причинами, правки инструментами morphkit.existing.Deck (скорость переходов, разрыв пар изменённого текста, петли сигнала по линиям, ступенчатое появление, перестройка связей без пересечений, удаление служебных слайдов), проверка и эскиз движения до/после."
argument-hint: "[.pptx] [what to change / что поменять]"
---

# /deck-remix — editing an existing presentation

Profile rule 8: **do not replace what works in the user's deck with your own.** Change only what was asked for or what is broken.
Tool reference — `../pptx-morph/SKILL.md` §14; engine — `../pptx-morph/scripts`.

## 1. Inventory
```
from morphkit.existing import Deck
d = Deck(path)
print("\n".join(d.report()))                 # slides, transitions, !! pairs, effects
for i in range(1, len(d.slides)+1): d.shapes(i), d.transition(i)
```
Render the original (`qa.render` → `contact_sheet`) and make a motion sketch
`motion.preview(d.to_slides(), theme, out/"before")` — to see what already works.

## 2. Edit plan
Table: slide # · what is wrong (measurement) · fix · tool. Typical ones:
- slow transitions → `d.speed(max_morph_ms=900, max_fade_ms=600)`;
- changed text morphs letter by letter → `d.text_policy()`, `d.fix_char_modes()`;
- auto-generated service slides → `d.inline_service_slides()`;
- list-style entrance → `d.stagger(i, names, ...)`; shifting the timeline → `d.retime()`, `d.shift()`;
- graph “crooked along the edges” → `plan_edges_clean(...)` + `d.rewire(...)`; zero-length lines → `d.hide_zero_lines()`;
- a lifeless process → loops `d.flow_on(i, connectors)` (signal along lines), `d.ripple(i, target)`;
- new objects → `d.add(i, [O(...)])`, rearranging → `d.move`, `d.regroup`, `d.stack_under`.
Show the plan if there are more than five edits or they change how slides look; do small technical ones right away.

## 3. Save and check
`d.save(out)` (a new file, do not touch the original) → `xsd_check`, `lo_effects_check`, render, thumbnail sheet,
`motion.preview(Deck(out).to_slides(), ...)` for the changed transitions. Compare “before/after” from the thumbnails.
Answer: the file, the list of edits by slide, what to check in PowerPoint.

_Russian original: SKILL.ru.md_
