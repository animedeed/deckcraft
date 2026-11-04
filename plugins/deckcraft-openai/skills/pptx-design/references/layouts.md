# 32 layouts

Each layout lists:
- **focus** — where it sits;
- **grid** — columns out of 12;
- **header** — system A–F from `composition.md`, §6;
- **motion** — which Morph techniques from `pptx-morph/references/techniques.md` (numbers in parentheses) work well with it;
- **density.**

`Slide(layout=…)` takes the layout name. `lint` uses these names to check variety: any 8 consecutive scenes need ≥ 6 different layouts; a series of steps in one layout counts as one scene. Coordinates of the basic archetypes are in `layouts-basic.md`.

## Openings and sections

1. **cover** — title slide.
   - Display title in columns 1–7, the presentation motif in 8–12 (wheel, ring, world graph) bleeding off the edge.
   - Header E; course context as a small line above the title.
   - Motion: camera (1), "Pinwheel" entrance of the motif (36).
2. **chapter** — section slide.
   - Section number 300+ pt as texture (D), h1 title, one line of "what's ahead".
   - Motion: card → background (6); the section style is the same as the whole presentation's.
3. **statement** — statement.
   - One h1 / display phrase at 60% width, left or centered, with the source at 13 pt below. Header E.
   - A breather slide.
4. **agenda-rail** — route.
   - Step pills (a rail) horizontally or vertically, the current one expanded. Header F.
   - Motion: rail (40), section map → header (5).
5. **route-world** — world map.
   - A world graph or diagram of the whole course, camera on the wide shot, current node highlighted. Header E/C.
   - Motion: camera (1), parallax (2).

## Numbers

6. **hero-number** — hero number.
   - One number at 96–140 pt on a third of the slide, hanging caption, context at 13 pt; on the right a small diagram or nothing. Header B/E.
   - Motion: the number appears with an effect (51); a correction is a strike-through and a new value.
7. **kpi-row** — 3–4 numbers.
   - A row of stats across 3/4 columns, one highlighted with the accent, a conclusion under the row. Header A/B.
   - Motion: in-slide growth (51), bars from zero (19).
8. **ring-pair** — share / quality.
   - A large progress ring (columns 1–5) + a small comparison ring + a list on the right. Header B.
   - Motion: ring with circular fill (21), re-sorting (20).
9. **doc-units** — a quantity in document sheets.
   - The value is shown as sheets with a folded corner (3.3 = three sheets + a strip), comparing two rows, the number alongside. Header B.
   - Motion: sheets appear left to right (in-slide growth, technique 51), pictograms (54).
10. **dot-field** — each dot = one observation.
    - A dot grid on 60% of the slide, caption "one dot = N", conclusion on the right. Header B.
    - Motion: grid → groups (25), → scatter (24), → histogram (26), collapse (27).

## Comparison and choice

11. **split-compare** — before / after.
    - Two equal halves (6+6), identical structure, verdict at the bottom. Header A.
    - Motion: screen split (43).
12. **matrix** — solutions × properties.
    - A table of dots or check marks, our row at the bottom. Header A.
    - Motion: spotlight across rows (14, 15).
13. **ranking** — who's better.
    - Horizontal bars in descending order, the worst in a status color, conclusion on the side. Header B.
    - Motion: from zero → re-sorting (19, 20).
14. **scatter-verdict** — two dimensions.
    - Scatter plot across 5–7 columns, our dot in the accent and larger, an indicator or number on the right. Header B.
    - Motion: burst from the origin (29).
15. **intervals** — fair comparison.
    - Confidence-interval whiskers around zero, labels at the ends. Header A.
    - Motion: intervals from zero (28).

## Processes and diagrams

16. **pipeline** — pipeline.
    - 4–6 nodes in a row, links with flows, the active one marked by a marker frame, 2–3 explanations below. Header A/C.
    - Motion: marker (11), flow (12), camera.
17. **wheel** — a cycle or steps around a circle.
    - Wheel / flower in columns 1–7 at full height, header and step card on the right. Header C.
    - Motion: flower pointer beyond the screen edge (phase 3), pinwheel (36).
18. **layer-stack** — layered architecture.
    - List of plates ↔ isometric stack, layer labels. Header C.
    - Motion: isometry (17).
19. **network** — graph of links.
    - Nodes and edges, the source of the change in focus, affected nodes marked. Header C/E.
    - Motion: network growth (16), pulse (10), ripples (13).
20. **annotated** — diagram with callouts.
    - Diagram across 8 columns, 3–5 callouts around the edges, leader lines. Header B.
    - Motion: spotlight (14), callouts one by one (`anim_*`).
21. **nested-zoom** — inside a node.
    - Node → close-up → its internal diagram. Header E.
    - Motion: nesting doll (3).
22. **timeline** — stages over time.
    - Horizontal scale (or vertical with narrow text), a "now" marker, events labeled at the scale. Header A/F.
    - Motion: ribbon + camera (4), pulse on the marker.

## Code and files

23. **code-walk** — code with explanations.
    - Code panel in columns 1–7 with highlighted lines, explanations in 8–12 opposite their lines. Header A.
    - Motion: the highlight moves (marker 11).
24. **terminal** — a run.
    - Terminal with a looping cursor, output, "what this means" on the right. Header A.
    - Motion: cursor blink, `anim_*` for output lines.
25. **file-tree** — structure.
    - File tree on the left, "what lives where and why" on the right, current files highlighted. Header A.
    - Motion: tree node expansion (18).

## Cards and navigation

26. **bento** — grid of mixed sizes.
    - Main card 6×2, the rest 3×1. Header B.
    - Motion: card expansion (39).
27. **carousel** — strip of examples.
    - Front card large, neighbors smaller and paler. Header C.
    - Motion: carousel (42).
28. **fan-stack** — presenting options.
    - Cards in a fan or stack, the chosen one slides out. Header B.
    - Motion: fan (41), flip (46).
29. **tabs-accordion** — sections of one object.
    - Tabs or an accordion, a slider under the active one. Header A.
    - Motion: tabs (44), accordion (45).
30. **qa-cards** — defense questions.
    - 3 question cards; the answer is a flip or an expansion. Header A/B.
    - Motion: in-slide flip (46), expansion (39).

## Finale

31. **mistake** — a typical mistake.
    - "Wrong / right" in two columns, a `bad`/`good` status plate with a label. Header B.
    - Motion: strike-through and new value, shape morph (32).
32. **recap** — summary, rhyming with the title slide.
    - The same motif or world as on the title slide, the result highlighted, 3 conclusions, contacts or next step. Header E.
    - Motion: camera pull-back (1), puzzle assembly (34).

## Choosing layouts for a section (example: a practical-class lecture)
`chapter → hero-number → pipeline (series) → code-walk → dot-field → ranking → mistake → qa-cards`.

Eight scenes, eight different layouts, alternating density: breather → diagram → dense → data → breather (conclusion) → dense → breather.

_Russian original: layouts.ru.md_
