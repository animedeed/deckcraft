---
name: deck-remix
description: "Edit an existing PowerPoint with morphkit while preserving its design, artwork, animation and useful content. Inspect before changing; verify before and after."
---

## Codex / ChatGPT Work runtime
Read `../../RUNTIME.md` before running scripts. Resolve sibling paths from this installed skill directory, never the current working directory. Keep generated files in the task workspace, outside the installed plugin. Preserve user reference art and interactive behavior. Do not commit, publish, install software, or update the plugin as part of creating a deck unless the user authorizes that action.


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
