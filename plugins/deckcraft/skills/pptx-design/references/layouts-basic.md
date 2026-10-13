# Layout catalog (archetypes)

Coordinates are inches on a 13.333 × 7.5 slide, columns follow the 12-column grid (`Grid.x/w`). Every slide states its archetype in `Slide(layout=…)`: `lint()` uses them to check variety (≥ 6 different ones per 8 consecutive slides).

Common header: section label `!!sec` (y 0.55), title `!!ttl` (y 0.9–1.0), folio `!!folio` at the bottom right. The header elements are persistent Morph anchors.

## 1. cover — title slide
```
┌──────────────────────────────────────────────┐
│ LABEL · CONTEXT                              │
│                                   ┌────────┐ │
│ Large headline                    │ motif  │ │
│ in two lines (display)            │ (cols  │ │
│                                   │ 9–12)  │ │
│ Lead subtitle, 2 lines            └────────┘ │
│                                              │
│ meta: data · metric                01 / 18   │
└──────────────────────────────────────────────┘
```
Text — columns 1–8, motif — 9–12.

## 2. route — route map (world + camera)
Stage nodes in world coordinates, links with flows. Overview → camera flight to the current stage. The first and last slides of the presentation “rhyme” through this layout.

## 3. statement — a single statement
A large phrase (h1–display) in columns 1–9, with one line of explanation below it. For section changes and the main takeaway.

## 4. split — text + visual
Columns 1–5: title, 3–5 bullets; 6–12: diagram, code, chart. Variants 4+8, 6+6.

## 5. pipeline — conveyor
A row of 4–6 nodes (`Kit.node`) across the full width (y ≈ 2.4–3.6), connectors `Kit.link` with `flow` streams. Below — 2–3 explanation cards. Morph: the active node changes color (technique 5), the loops move along.

## 6. metrics — numbers
3–4 `Kit.stat` in a row (columns of 3 or 4), with one takeaway line below. The big number — accent, the caption — ink2. The figures grow from a zero state.

## 7. compare — comparison
Two columns 6+6 (or 5+2+5 with a vertical rule), the same row structure. The verdict — at the bottom or by highlighting the winning column. Technique: split screen (10).

## 8. code — code and explanations
A code panel (`Kit.code`) in columns 1–7, on the right in 8–12 — explanations of the lines; highlighted lines `highlight=[…]`. Morph between two slides: the highlight moves across the lines.

## 9. terminal — run and output
`Kit.terminal` with a blinking cursor (`Loop("blink", target=…)`) + a comment on the output. For a “reproducible run”.

## 10. table — table built from shapes
`Kit.table` with a highlighted row (`highlight`). No more than 6–7 rows; more — split it.

## 11. chart — chart built from shapes
`Kit.bars` (horizontal, long labels) or `Kit.columns` (by category), labels at the bar ends. On the right or below — a takeaway in one or two lines. Zero state → values.

## 12. tree — file structure
`Kit.tree` on the left, on the right explanations of “what lives where and why”. Highlight the files of the current step.

## 13. grid — card matrix
2×2, 2×3, 3×2 `Kit.card` cards of equal size. Morph: one card expands (7), the rest shrink.

## 14. qa — defense questions
3 question cards; the answer appears after the transition (`anim_*`) or on the next slide the question expands into a panel with the answer (technique 7).

## 15. callout — common mistake / warning
`Kit.callout(tone="warn"|"bad")` + an example of “wrong way / right way” (two columns of code or text).

## 16. timeline — stages over time
A horizontal scale with ticks; a “moment” marker (pulse) divides “known before” and “known after”.

_Russian original: layouts-basic.ru.md_
