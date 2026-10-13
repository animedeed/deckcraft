# Morph technique catalog: 59 recipes

Each technique lists:
- **meaning** — when it explains rather than decorates;
- **recipe** — what is on slides N and N+1;
- **helper** — the engine function;
- **pitfalls**.

`R` — `morphkit.recipes`, `V` — `morphkit.vector`, `K` — `Kit`.

Verified examples:
- `scripts/gallery_vector.py` — vector and 3D;
- `scripts/examples/demo_deck.py` — a presentation from scratch from a brief: motif in roles, navigation, per-section motion languages.

**General rules.**
- One technique — one idea. Adjacent transitions use different techniques, except for series: wheel, spotlight, steps of one process.
- Durations: 0.5–0.8 s — a small edit, 1.0–1.6 s — scene rebuild, 1.6–2.2 s — camera flight. A helper intermediate slide (`auto=0`) — 0.4–0.6 s.
- Before building, write out the storyboard: what is on N, what is on N+1, which pairs, what gets parked.

## A. Camera and space

1. **Camera over a canvas.**
   - Meaning: wide shot → detail.
   - Recipe: world `world=True`, each slide has its own `Cam(cx, cy, z)` (section 7 of SKILL.md).
   - Pitfall: in a close-up do not keep the giant labels of the wide shot — fade them out.
2. **Parallax.**
   - Meaning: depth during a camera flight.
   - Recipe: background layer `meta={"parallax": 0.3}`.
3. **Matryoshka (infinite zoom).**
   - Meaning: “inside the node is a whole diagram”.
   - Recipe: N — a node of normal size; N+1 — camera z×8 on the node, the node has become a background frame, its diagram appears inside (objects without a pair); N+2 — a new world with the same frame acting as the border.
   - Pitfall: on N the inner diagram must already exist, tiny (small z), inside the node, otherwise it just appears rather than “zooming in”.
4. **Timeline.**
   - Meaning: events by year.
   - Recipe: a ribbon world 3–5 slides wide, the camera moves right; the current year large, neighbors smaller (scale by distance to the center).
5. **Section map → header.**
   - Recipe: section cards on the title slide; on a section's slide its card moves to the corner and shrinks into a label, the rest park behind the edge.
6. **Card becomes the background (morph-through).**
   - Meaning: “we go inside”.
   - Recipe: N — card `!!c`; N+1 — the same `!!c` at slide size (with a 0.3″ margin), its color is the new slide's background; the new slide's content without pairs appears.
   - Pitfall: remove or move away the card's text on N+1, otherwise it inflates.
7. **Section-boundary circle.** *Rejected by the default profile: changes style mid-presentation; only if the profile allows it.*
   - Recipe: `R.circle_wipe(id, cx, cy, color, grown=False/True)`. A circle in the new section's color grows from a “button” dot and floods the slide. The next slide already has a background of this color.
   - Pitfall: the source dot on N must be a noticeable element, otherwise the growth comes “from nowhere”.

## B. Diagrams and processes

8. **Drawing a line.**
   - Recipe: N — a line of length 0 at the start point; N+1 — full length.
9. **Drawing a polyline.**
   - Recipe: `R.draw_polyline(id, pts)` → objects + `Fx("entrance_wipe")` per segment in the direction of motion.
   - Pitfall: the segments are new objects without pairs (entrances on pairs are forbidden).
10. **Pulse along an edge.**
    - Recipe: a small circle `!!pulse` at the source on N, at the receiver on N+1. The edge is highlighted with a frame or a flow, not by recoloring.
11. **Step change — with a frame.**
    - Recipe: `K.marker(node)` — the `!!marker` pair moves to the new node. Recoloring between distant colors makes mud (section 9 of SKILL.md, item 6a).
12. **Data flow (loop).**
    - Recipe: `K.link` + `K.flow` (`references/loops.md`). Dots are hidden until start and do not flicker during the transition.
13. **Event here (loop).**
    - Recipe: `Loop("ripple")` — ripples on water at the node where something happened.
14. **Spotlight.**
    - Meaning: “look here” on a dense diagram or table.
    - Recipe: `R.spotlight(id, (x, y, w, h))` — the slide dimmed with one hole. On the adjacent slide the window moves and resizes. Morph morphs a shape with one hole (no more than one).
    - Layer: z=15 — above the content, below the headers.
    - Fallback: `R.spotlight4` (four rectangles).
15. **Sliding window over a table.**
    - Recipe: a series of spotlights: whole table → group of rows → our row. The conclusion appears at the last step (`anim_*`).
16. **Network growth.**
    - Recipe: N — all nodes at the source center with size 0; N+1 — in their places, edges from length 0. Second step: flow loops.
17. **List → architecture layers.**
    - Recipe: plates in a list → `V.rot3d(**R.ISO_TOP_UP, depth=8)` as a stack with a y step (`references/vector.md`).
18. **Node expands into a card.**
    - Recipe: node `!!n` stretches into a panel with details; neighboring nodes shrink into pills along the edge.

## C. Data

19. **Bars from zero.**
    - Recipe: `K.bars/columns(zero=True)` → values; `R.ranked_bars(zero=True)` → values.
20. **Re-sorting.**
    - Meaning: “who is better”.
    - Recipe: `R.ranked_bars(order="given")` → `order="desc"`. Names are by entity, so the bars move to their new places.
21. **Progress ring.**
    - Recipe: `objs, fx = R.ring_fill(id, cx, cy, r, frac)` — an arc already at the right length from 12 o'clock + a “Wheel” entrance with one spoke: the ring fills around when the slide is entered.
    - Pitfall: do not grow the arc's adjustment handle with Morph — PowerPoint draws an intermediate wedge (“triangle”).
22. **Gauge indicator.** *Removed per user feedback (ugly semicircular fill).*
23. **Odometer.** *Removed per user feedback: on entering and leaving the slide the masks fade together with the digit columns — “phantom” numbers are visible. Numbers appear with an effect (`R.reveal(..., "entrance_faded_zoom")`).*
24. **Grid → scatter.**
    - Meaning: “each dot is an observation, here is where it is on the chart”.
    - Recipe: `R.dots(id, R.grid(...))` → `R.dots(id, R.scatter(...))`.
25. **Field → groups.**
    - Meaning: train / val / test, classes, segments.
    - Recipe: `R.groups(sizes, boxes, step)`. Dot order is preserved, so the first `sizes[0]` go to the first group. Group colors are close or from one role.
26. **Field → histogram.**
    - Recipe: `R.histogram(values, bins, ...)` — dots line up in stacks of their bins.
27. **Collapse 99 → 15.**
    - Recipe: the extra dots — size 0 in place; the remaining ones gather into a dense block (`R.grid(keep, ...)`). Next to it the number 99 → 15 (the old one fades, the new one appears).
28. **Intervals from zero.**
    - Recipe: confidence interval whiskers of length 0 on the zero line → they open up; the estimate dot moves to the value.
29. **Dots bursting from the origin.**
    - Recipe: `R.pile(n, x0, y0)` → `R.scatter(...)`.
30. **Pie piece by piece.**
    - Recipe: `V.sector` sectors — whole ring → one sector pushes outward (offset along the bisector) → label.
31. **Matrix by rows.**
    - Recipe: cell dots; the “our option” row appears after Morph via `anim_*`.

## D. Shapes and vector (`references/vector.md`)

32. **Shape morph.**
    - Recipe: `V.resample(g, n)` on both shapes: circle → star → drop. No more than one hole.
33. **Fragmentation and burst.**
    - Recipe: `V.fragment` → pieces in place → `R.explode(parts, k)`.
34. **Puzzle assembly.**
    - Recipe: the reverse of 33: the pieces from the burst assemble into a whole, the last one as an accent.
35. **Wheel / flower.** *Half-steps and “wheel to the corner” were rejected by the user (jumps, rotation not visible). The right role for the flower is the topic pointer, half behind the screen edge (phase 3, `pptx-design`).*
    - Recipe: `V.petal` petals in a frame on the axis (`pivot`); rotating by a step puts the active one at 12 o'clock. The active one pushes out — a different outline with the same number of points.
    - A step larger than 45° is split into half-steps (`auto=0`) so the labels do not cut the chord.
36. **“Spinner” entrance from the center.**
    - Recipe: `Fx("entrance_spinner")` on petals in a frame on the axis — they spin out from a common center. Delays 0.08–0.12 s.
37. **Orbit.**
    - Recipe: a satellite in a frame on the sun's axis; rotating the frame carries it along an arc. Step < 180°.
38. **Living background.**
    - Recipe: 2–3 large blurred blobs (freeforms, `fa=0.15–0.3`) slowly change position and shape on every slide of the section. Morph duration 1.6–2 s.
    - Pitfall: check text contrast against the lightest spot.

## E. Cards and navigation

39. **Card expansion.**
    - Recipe: a card from a row stretches into a panel, neighbors shrink into pills.
40. **Step rail.**
    - Recipe: `K.rail(steps, active)`. The current pill is expanded.
41. **Fan / stack.**
    - Recipe: cards in a stack → in a fan, `rot = (i − k)·2–4°`.
42. **Carousel.**
    - Recipe: `R.carousel(n, active, ...)` — places on an ellipse (front large, back smaller and paler). A step by one position — Morph along the chord; with n < 6 add half-steps.
43. **Split screen.**
    - Recipe: two panels parked behind the edges, a divider of length 0 → the panels slide in, the divider grows.
44. **Tabs with a slider.**
    - Recipe: a row of tabs; the underline slider `!!tab` moves under the new tab and changes width; the content changes with a fade.
45. **Accordion.**
    - Recipe: section strips; the open section grows in height, the others shift; the open one's text appears.
46. **Card flip.**
    - Recipe: `R.flip_fx(front, back)` — within the slide: a horizontal “Swivel” exit of the front and a “Swivel” entrance of the back. No helper slides needed.
47. **Tilt toward the viewer.**
    - Recipe: `V.rot3d(x=15–25, camera="perspectiveFront")` on the selected card, the others flat — focus without enlarging.

## F. Text

48. **Header flows.**
    - Recipe: `!!ttl` with new text. Short edits — `mode="byWord"`.
49. **Character-level edit.** *Restricted by the profile: the mode applies to ALL texts on the slide, letters fly off into the page number and neighboring captions. Allowed only if there is a single text on the slide; otherwise the edit is a strikethrough of the old value and the appearance of the new one.*
    - Meaning: “one number changed”.
    - Recipe: `mode="byChar"`: “12 years” → “10 years” — all letters stay except one digit. A frame on the edit type next to it.
    - Pitfall: the mode applies to the whole slide — other objects with text also morph by character.
50. **Kinetic typography.**
    - Recipe: one or two huge words (display 80–140 pt) swap places, scale and color to the rhythm of speech; neighboring words park behind the edges.
    - Measure: one such episode per presentation — for a thesis or conclusion.

## How to invent a new technique (protocol)

1. State **what changes in meaning**: appeared, moved, grew, split, matched, disappeared.
2. Find the **persistent object** — the Morph pair that carries continuity (“this is the same document, the same dot”).
3. Break the motion down into what Morph does well: position, size, rotation around the frame center, adjustment handles, cropping, 3D rotation, morphing a freeform with an equal number of points, close colors. Everything else — via workarounds:
   - arc — a frame on the axis;
   - mask — a shape with one hole or solid masks;
   - long rotation — half-steps;
   - new content — `anim_*` / `Fx` after the transition;
   - process — a loop.
4. Write the recipe into this catalog with a helper if the code is non-trivial, and add a slide to the gallery with a “what to check” note.
5. Verify by showing it in PowerPoint and record the conclusion in the “Findings from showings” section of the project's `WORKLOG.md`.


## G. Growth and continuity without helper slides (after user feedback)

51. **Growth within the slide.**
    - Meaning: numbers, bars, dots “grow” on entrance.
    - Recipe: `R.reveal(names, effect, stagger)`. Bars — `entrance_wipe {direction: left}`, columns — `{direction: down}`, dots and labels — `entrance_fade`, numbers — `entrance_faded_zoom`, sheets — `entrance_rise_up` from left to right. The show stays one click, going back works normally.
52. **The world recedes into the background.**
    - Recipe: `R.backdrop(world, k=0.3)` — the same graph with transparent fills and lines and quiet text. Names are kept, so Morph mutes the world rather than removing it. Usually with a camera shift or pull-back.
53. **Signal along a line.**
    - Recipe: `R.flow_along(line, cam)` — a flow strictly along the connector's geometry (for a world — with the camera), `trim` stops short of the labels.
54. **Document sheets.**
    - Recipe: `R.doc_arc(id, n, …)` — a ribbon of dog-eared sheets in an arc, the selected sheet with an accent outline. `R.doc_pictograms(id, 3.3, …)` — a value in sheets (whole ones + a strip for the fractional part). Appearance — `R.reveal(..., "entrance_rise_up")` from left to right.


## H. Hero transformations (phase 3; gallery `scripts/gallery_hero.py`, theme “Ink”)

55. **Mandala flower of multi-layer petals** (reference — the user's video: Merge Shapes → Fragment).
    - Recipe: `R.mandala(id, center, petals, length, width, turn, scale)`. A petal is `V.bud`: nested lenses with a common vertex at the center → crescent stripes (light/gray gradient) + a dark core. Each petal is a group lying on top of the previous one; an edging along the rim.
    - Entrance — `R.mandala_spin_in` (“Spinner” per petal from the center).
    - The shape is the same at any `scale`: Morph changes only the frame (rotation and size), without shape morphing.
56. **Flower as a topic pointer behind the screen edge.**
    - Recipe: the flower's center at the left edge (half off screen), `turn` such that the topic's petal faces right; a stationary pointer `R.pointer_lens` — an outline with an amber highlight. Topic change = rotating the flower by a step (< 180°), the topic number and name fade out/in.
    - Pitfall: do not drag the flower around the corners — it stays put and only rotates.
57. **Petal → panel.**
    - Recipe: the lens pointer (`pointer_lens`, n points) morphs into the content panel (`panel_from_lens`, the same n points); the flower moves further behind the edge and shrinks. The reverse — the panel folds back into a petal.
58. **Documents → graph nodes** (carriers of continuity).
    - Recipe: the same sheet objects (`R.doc_arc`, names `!!doc{i}`) on the next slide shrink and spread around a circle as nodes; edges grow from the center; the signal — `R.flow_along` along an edge.
59. **Fragments → cards and a “liquid” section change.**
    - The diagram's fragments (`V.fragment`, `V.resample(…, 120)`) morph into grid cards (`V.resample(V.rect(…), 120)`), the label — by which circles the piece belongs to.
    - The section is changed by large “drops” (freeforms of 200 points each) that flow and grow — a new section without a style change.

## Rejected techniques (from the user's showing notes)

| Technique | What went wrong | Replace with |
|---|---|---|
| Native transition (cube, etc.) on every section change | “very unnecessary”, “cheapens the whole presentation” | section change via transformation (camera, pointer, map → header); native ones only on request, short |
| Outline of 34–48 evenly spaced points | petal tips and corners cut off into flats, facets visible on curves | `resample` keeps corners and gives ≥ 120 points; when writing to pptx, curves are smoothed with a spline (`smooth_ring`); lint “coarse outline” |
| Flower layers as crescent stripes with a background-colored outline | “tears” and white seams between parts | whole petals in a stack (`bud(nested=True)`), a thin dark edging along the rim — as in the reference video |
| Barrel bottom as a straight line | the barrel is flat, the hoops do not follow the volume | staves and hoops along the cylinder's ellipse (`rim(y, t)`) |
| A one-off native transition mid-presentation (one cube, one curtain, one zoom-in) | “as if shoved in once”: the viewer expects the same change at every section | an accent is a system: one type at all section boundaries (`combine.transition_pattern`), the “final” one (curtain) only at the end; the zoom-in looked best of all |
| Talk map → header with cards parked behind the edge | during the transition outlines fly in different directions and run over the header | `agenda(state="bar")`: all sections side by side at the top, only the highlight moves |
| Scanner light beam and pulsing on the found word | the beam cuts off abruptly and competes with the word; the pulsing is irritating | a soft halo of nested ovals + a wavy line, attention is held by an arc with a running dot |
| Wave across layers skipping a layer | a jump: the link between adjacent layers is not visible | layers light up in turn on one slide, the signal goes through all layers |
| Odometer | phantom digits on entering and leaving the slide; “9” and “0” on different lines | the number appears with an effect |
| Semicircular gauge | the fill is ugly | `ring_fill` ring or a hero number |
| Ring via a Morph adjustment handle | intermediate “wedge” | `ring_fill` (“Wheel” entrance) |
| Helper auto-slides | cannot go back | `reveal` within the slide |
| Character mode on the whole slide | letters fly off into the page number, “before” → “after” | strikethrough + new value |
| Morphing different text | letter mush | profile `text_policy="fade"` (default) |
| Wheel to the corner and back, 45° half-steps | jumps, rotation not visible | flower pointer behind the screen edge (phase 3) |
| Full-screen boundary circle | a new style mid-presentation | a section boundary in the presentation's style |
| Portal (motif disc to full screen) | a single “special” transition mid-presentation feels foreign; the arc of the huge disc shows through a frame when shrinking | one transition type between sections for the whole presentation (pointer rotation, card → header) |
| Motif collapsed into a dot (“seed”) | the motif suddenly becomes tiny — strange | the next section's pointer or the backdrop |
| Backdrop → pointer with rotation | the huge motif spins, moves and shrinks all at once | the backdrop is pre-rotated for the next section (`backdrop(next_k=…)`): returning = only a shift |
| Pair outlines in the dot color creeping over each other | outlines merge with the dots and cross between rows | a thinner outline of a different tone, tight to the pair, a gap between rows |
| Own simplified graph instead of the user's graph | looks cheaper | “existing presentation” mode: take the user's objects |
| Plates and bars instead of document sheets | the “model” look was lost | `doc_arc`, `doc_pictograms` |
| Transitions of 1.5–2 s | slow | Morph ≤ 0.9 s, camera ≤ 1.2 s, fade ≤ 0.6 s |

_Russian original: techniques.ru.md_
