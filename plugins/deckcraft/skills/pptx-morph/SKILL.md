---
name: "pptx-morph"
description: "PowerPoint Morph engine (morphkit) with web export (one HTML file: real Morph, 81 effects, live scenes, sheet transitions, drawn elements, buttons, presenter view): world canvas with a camera, 54 Morph techniques, motif roles, process grammar, 12 palettes with reasons, in-slide loops, 198 native animations and 53 transitions, vector shapes and pseudo-3D, QA (lint, XSD, render, motion preview). Used by the deck-* commands. / Сборка .pptx с переходом «Трансформация» (Morph) движком morphkit: мир-холст с камерой, 54 приёма Morph с помощниками (прожектор, поле точек, кольца с заливкой по кругу, листы-документы, мир на фоне, сигнал по линиям, карусель, переворот), сквозной мотив в ролях (обложка, указатель за краем, фон, диаграмма, портал, прогресс), грамматика процесса (носитель через глаголы split/encode/relate/score/flag) и 12 палитр с причиной выбора, профиль презентации с правилами из показов (текст не переливается, без служебных слайдов, быстрые переходы, замок стиля), петли «до конца слайда» (потоки точек, пульс, круги на воде, вращение, мигание), библиотека 198 нативных анимаций PowerPoint и 53 переходов с правилами стыка с Morph, векторная графика (булевы операции над фигурами, лепестки и радиальные сборки, вращение вокруг оси, перелив форм, разлёт фрагментов, градиенты, 3D-поворот и изометрия), компоненты технических презентаций (код, терминал, схемы, таблицы и графики из фигур), стилевые превью, заметки-конспект, проверка с замерами (lint, XSD, рендер) и инструменты разбора референсов. Дизайн-решения (композиция, шапки, макеты, ритм) — в скилле pptx-design; использовать оба для любой презентации с плавными переходами, анимированными процессами и учебными разборами."
---

# Presentations with Morph and live diagrams

Works best together with Anthropic's pptx skill (plugin `document-skills@anthropic-agent-skills`): if it is installed, read its SKILL.md first (`validate.py` validation, rendering via `soffice.py`, schemas for `xsd_check`). Without it the XSD check is skipped with a hint and rendering goes through the system `soffice` — tell the user so. The build is done **from a single scene description** with the `scripts/morphkit` engine (Python + python-pptx). The only deliverables are `.pptx` files. Rendering to PNG is only for your own visual check.

Core idea: **Morph carries state between slides; loops bring the state alive on a slide.** Morph shows *how* the diagram changes (step → step, overview → detail). Loops show *what* happens inside it while the slide is on screen: data flows, a node works, a cursor waits. They live on different layers and must not be mixed (section 9).

## Presentation profile rules (lessons from the user's shows — always follow)
`morphkit.profile.DeckProfile` stores them for the presentation (`deck_profile.json`). `build_pptx(..., profile=)` and `lint(..., profile=)` apply them.
1. **Changed text does not morph.** If the text of a Morph pair has changed, the engine breaks the pair: the old one fades out, the new one appears. Morphing text is only for identical text or with `meta={"morph_text": True}`.
2. **"By word / by character" mode** — only if the slide has a single text. Otherwise letters fly into neighbouring captions and the page number.
3. **No service auto-slides.** They make paging backwards impossible. Growth from zero is done with entrance effects inside the slide (`recipes.reveal`, `ring_fill`).
4. **Fast:** Morph ≤ 0.9 s, camera flight ≤ 1.2 s, fade ≤ 0.6 s; animations start 0.1–0.15 s after the transition.
5. **Style lock:** one set of layouts, techniques and backgrounds per presentation. A slide in a new style in the middle of the presentation is an error. The same caption twice on a slide is an error.
6. **The world does not disappear, it recedes into the background** (`recipes.backdrop`); **the signal travels strictly along lines** (`recipes.flow_along`).
7. **Rejected techniques** (odometer, needle gauge, ring via adjustment handle, half-steps, wheel into the corner, boundary circle) — in `references/techniques.md`, "Rejected". The default profile forbids them.
8. **Do not replace what already works for the user with your own.** A presentation is refined in "existing presentation" mode, not rebuilt "your own way".

## 0. How Morph actually works (official rules)
- A pair of objects on slides N and N+1 is defined by **the same name with the `!!` prefix** (`!!card1`). An object with `!!` is never matched with an object without `!!`. Unpaired objects simply fade in or fade out.
- Morph animates position, size, rotation, flip, fill and line colour, transparency, **shape adjustment values** (adj: arc angle, corner rounding), **picture cropping** and text size.
- Modes: `byObject` (default), `byWord`, `byChar` — set for the whole slide (`<p159:morph option="byWord"/>`). In by-word/by-character mode identical words flow over, new ones fade in.
- **Do not morph:** charts and tables (cross-fade only), shapes with two or more "holes". Freeforms morph well only if they have a similar number of points and the same winding direction. That is why charts and tables that must move are built **from shapes** (section 10).
- Versions: PowerPoint 365/2019+ (Win 1903+, Mac 16.23+). PowerPoint 2016 only plays it back; older versions show a fade (Fallback). Tell the user if you do not know what it will be shown on.

## 1. Process
1. **Brief, rhythm, composition and storyboard** — per the `pptx-design` skill; presentation concept (recurring motif, process carrier, palette with a reason) — `references/concepts.md`. 2. **Three style previews**, the user chooses (sections 2–6). 3. **Build** with morphkit (section 12). 4. **Measured checks** (section 15) and **critique from thumbnails** (the `pptx-design` checklist, §5). 5. Answer: which techniques on which transitions, where the loops are, what to check in PowerPoint.
Do not skip the previews if the style is not given explicitly: taste is easier to choose with the eyes than with words.

## 2–6. Design — in the pptx-design skill
"How it should look" decisions are made **before code** per the `pptx-design` skill (`../pptx-design/SKILL.md`):
- brief and visual thesis, palette by roles and contrast, fonts with Cyrillic, grid, density, anti-patterns — `pptx-design/references/design-system.md`;
- slide composition and **header systems without monotony** — `composition.md`;
- 32 layouts — `layouts.md`, coordinates of the basic ones — `layouts-basic.md`;
- presentation rhythm, a "wow" per section, motion language, storyboard table — `rhythm.md`;
- choosing a form for data — `infographics.md`;
- analysis of examples the user sends — `references-protocol.md` (tools `scripts/refs_frames.py` and `scripts/refs_deck.py`).

What the engine needs from this:
- **Colour roles** in the slide description (`fill="accent"`, `col="ink2"`). Themes and `Theme.contrast_report()` — in `morphkit/theme.py`. `lint()` checks the contrast of every text against the background beneath it, including inside freeforms.
- **Fonts** with a metric-compatible substitute (Calibri↔Carlito, Arial↔Liberation Sans, Times New Roman↔Liberation Serif, Courier New↔Liberation Mono): line-wrap checks are exact only for these.
- **Three style previews:** `morphkit.preview.build_previews(brief, [theme1, theme2, theme3], out)` → mini-presentations and a comparison sheet. The user makes the choice. No service captions on the slides.
- **Storyboard → `Slide` fields:** `layout=` (layout name from `pptx-design/references/layouts.md`) and `technique=` (the technique of the transition TO the slide; for a series — "… (series)"). From these `lint()` checks variety: ≥ 6 different layouts per 8 scenes, a run of one layout in a row counts as one scene; a technique is not repeated on two consecutive transitions.
- **Morph durations:** 0.5–0.8 s — an edit, 1.0–1.6 s — a rebuild, 1.6–2.2 s — a camera flight; a service half-step (`auto=0`) — 0.4–0.6 s.
- **Numbers grow from zero — inside the slide:** entrance effects (`recipes.reveal`, `ring_fill`), no service slides (profile rule 3).
- **Recurring anchors:** section label `!!sec` (may move together with the header system), title `!!ttl`, folio `!!folio`, progress `!!s0…`, backing panel `!!panel`.

## 7. World canvas and camera (the main technique)
The whole "universe" (graph, map, diagram) is defined once in **world coordinates** (`O(..., world=True)`). Each slide is a camera position `Cam(cx, cy, z)`:
```
x = (X − cx)·z + W/2;  y = (Y − cy)·z + H/2;  w = W_obj·z;  h = H_obj·z;  font size = font size·z;  line width = line width·z
```
Morph interpolates x, y, w, h linearly — this is affine in X for a shared z(t), so all objects move as **one camera**, without "drifting apart".
- **Parallax:** a background layer with a weakened camera (`meta={"parallax": 0.35}`): the distance moves more slowly, depth appears.
- Small text in an overview shot is acceptable as texture (`meta={"texture": True}`); check legibility only in close-ups.
- On "stage" slides (numbers, tables) **do not keep the whole world**: leave a background. Otherwise giant captions fly past. The world fades out in place, the scene fades in.
- Objects may sit far beyond the slide edge (up to ±2000 inches) — this is fine.

## 8. Catalogue of Morph techniques (recipes)
Below are the basic 19 techniques. **The full catalogue of 50 recipes** (camera and space, diagrams, data, shapes, cards, text), the `morphkit.recipes` helpers (spotlight, dot field, in-slide growth, ring with circular fill, world in the background, signal along a line, document sheets, carousel, re-sorting, polyline, flip), the "Rejected techniques" table and the "how to invent a new technique" protocol — in `references/techniques.md`.
| # | Technique | How to do it |
|---|---|---|
| 1 | Camera over the canvas | section 7; the camera flies from the overview to a node |
| 2 | Parallax | a background layer with a weakened camera |
| 3 | Line drawing | line: on slide N length 0 (w = h = 0 at the start point), on N+1 — full |
| 4 | Pulse along an edge | a small circle `!!pulse` on N at the source node, on N+1 — at the receiver, the edge recoloured |
| 5 | Node state change | the same object: fill/border colour, size, caption — "was grey, became wine-red" |
| 6 | Text flows over | title `!!ttl` with new text; for an edit inside a phrase — `mode="byWord"`/`"byChar"` |
| 7 | Card expansion | card `!!m1` from a row stretches into a large panel; neighbours shrink into "pills" |
| 8 | Rail/pills | the section's steps are pills in the header (`Kit.rail`); the current one is expanded, the rest are small |
| 9 | Fan/stack | N: cards in a stack (or tiny, `fa=0`, inside the source node); N+1: fanned out, `rot = (i − k)·2°` |
| 10 | Screen split | two panels parked beyond the edges, a divider line of length 0 in the centre → the panels slide in, the line grows |
| 11 | Magnifier / window | a copy of the picture with a different crop (`crop`) and magnification moves over the original |
| 12 | Spotlight | `recipes.spotlight`: the dimming is a shape with one hole (Morph morphs shapes with at most one hole); the window moves and resizes. Fallback — `spotlight4` from 4 rectangles |
| 13 | Progress ring | `arc` (blockArc): adj1 = 0, adj2 = p·359.9°·60000, adj3 = thickness; rotation 270° so that it starts at the top |
| 14 | Growing bars | `Kit.bars/columns(zero=True)` on a service slide → values on the main one; the label rides with the end |
| 15 | Dot scatter | marker dots sit at the origin → fly to their positions |
| 16 | Grid collapse | a grid of N dots; the extra ones shrink to 0 in place (99 → 15) |
| 17 | Intervals from zero | confidence-interval "whiskers": length 0 on the zero line → they open up |
| 18 | Carousel | card A slides away and shrinks to the left, B slides in from the right (it was parked beyond the edge) |
| 19 | Matrix | cell dots; the "our option" row appears after Morph via `anim_*` one by one |

Parking: do not delete what leaves, keep it beyond the edge. Directions are consistent: what has been covered — to the left (x ≈ −width − 0.5″), the future — on the right (x > slide width), secondary things — down, old titles — up.
Also: zoom navigation over the section map (the section card becomes the header); rebuilding a grid of cards `!!card1..k` (4 → 1, 2 → 3); permanent anchors (page number, progress dots, background circle in a new corner).

## 8a. Vector and 3D (`morphkit.vector`)
`custGeom` freeforms from boolean operations — the programmatic analogue of "Merge Shapes": union, intersect, subtract, combine, fragment, sectors. There are petals and lenses, radial assemblies, shape morphing, gradients and 3D rotation. Reference — `references/vector.md`, gallery — `scripts/gallery_vector.py`. Four "wow"-level techniques:
1. **Frame on the axis (pivot).** The shape is drawn in a square frame centred on the rotation axis, so `rot` and its morphing rotate it **along an arc around the axis**: wheel, clock face, carousel, orbit, flower petals. The "Spinner" entrance spins such objects out from a common centre. The rotation step per transition is less than 180°; a full turn is split into steps.
2. **Shape morphing.** Both shapes of a pair get `resample(g, n)`: equal number of points, one winding, one start point, no more than one hole.
3. **Fragmentation and scatter.** Whole shapes → pieces in place (an almost invisible transition) → the pieces drift apart; the reverse is assembly.
4. **3D.** A card flip is two Morphs in a row via a service slide (face 0° → 90°, back 270° → 0°). Isometric stack: a list of tiles folds into layers. LibreOffice does not show 3D — check only in PowerPoint.

## 9. Loops and regular animations on top of Morph
Regular PowerPoint animations (entrance, emphasis, motion path) live **on the slide timeline** and start after the transition. Any effect can be repeated "until end of slide" (`repeatCount="indefinite"`). This gives live diagrams: a dot keeps travelling from server to client and starts over.

**Five loops** (`Loop(kind=…)`, details and XML — `references/loops.md`):
| Loop | What you see | How it works |
|---|---|---|
| `flow` | dots run along a polyline: server → client, stage → stage | motion path (`animMotion`, presetClass `path`) with repeat; n dots with start offset period/n |
| `pulse` | a node "breathes" | "Grow/Shrink" (emph 6, `animScale`) with auto-reverse |
| `ripple` | ripples on water from a node | a copy ring: growth + fade (`animScale` + `animEffect fade out`) |
| `spin` | a gear is working | "Spin" (emph 8, `animRot` 360°) |
| `blink` | a terminal cursor is waiting | "Blink" (emph 35, discrete visibility) |

**Rules for combining with Morph (mandatory):**
1. **Different layers.** A loop object (`loop_…`) is never a Morph pair. Motion paths shift where the object is drawn, while Morph takes its static position: the pair would jerk. The engine forbids `!!` on `loop_…`.
2. **Diagram — pairs, motion — loops.** Nodes and arrows are `!!` objects (they move with Morph). Flow dots are created anew on each slide at the new coordinates (`Kit.link` returns a centre-to-centre path). During the transition the old dots fade out; after it, the new ones run along the already rebuilt diagram.
3. **The queue hides under the node.** Dots wait to start at the beginning of the path. The path runs from the centre of the source to the centre of the receiver, the dots lie below the nodes (`z` 5 vs 10): waiting and return are hidden, the dot "comes out" of the server and "goes into" the client.
4. **Timing.** In PowerPoint the slide timeline starts **after** the transition ends (verified by recording a show): delays do not include the Morph duration. Loops — after 150 ms, `anim_*` — 150 ms + i·380 ms. A start later than 0.3 s after the transition looks like a "freeze". Period 1.6–3 s; 2–4 dots; dot 0.10–0.16″.
4a. **Carriers are hidden until they start.** Every flow dot and `ripple` ring gets an "Appear" entrance effect (entr 1) at the moment of its start. An object with an entrance is invisible until then, including during Morph, so the dot queue does not flicker during the transition.
5. **Moderation.** No more than two loop systems per slide; a loop only where it explains a process (data flow, training cycle, waiting), not as decoration. Do not loop text.
6. **Stopping.** Loops run until the end of the slide; on transition their unpaired carriers fade out together with Morph.
6a. **Change the highlight with a frame, not by recolouring.** Morph between distant colours (orange → dark blue) passes through muddy intermediate shades. Show the active step with a moving marker frame (`Kit.marker`, pair `!!marker`), and do not change the node colour.
7. **Checking without PowerPoint:** XSD (section 15) + import into LibreOffice (`--convert-to odp`): `content.xml` must contain `smil:repeatCount="indefinite"` and recognised presets (`ooo-emphasis-spin`, `-blink`, `-grow-and-shrink`, motion-path). Watch the motion itself in PowerPoint (F5).

## 9b. Animation and transition library (`Fx`, `TRANSITIONS`)
Besides loops, the engine can put **any of the 198 native PowerPoint effects** on the slide timeline: 52 entrances, 30 emphases, 64 paths, 52 exits. This is XML captured from PowerPoint 16 and retargeted to the shape. The transition to a slide can be **any of 53**: Morph, ISO transitions, p14 (vortex, gallery, cube…), p15 (curtains, origami…). Full reference with a selection table — `references/motion-library.md`; to see everything with your own eyes — `scripts/gallery.py`.
```python
Slide(objs, transition="cube", fx=[
    Fx("entrance_spinner", "!!flower", dur=0.9),                    # "Spinner" for a new object
    Fx("entrance_fade", "cap", start="after", delay=0.1),           # after the previous one
    Fx("emphasis_grow_shrink", "kpi", options={"size": 115}, rev=True, start="after"),
    Fx("path_circle", "sat", dur=6, repeat=True, path_size=(3, 3)),
])
```
**Rules for joining with Morph** (`lint` checks them):
1. A Morph pair takes the geometry of the static slide; the result of animations is not taken into account.
2. **Entrance** — only for new objects. On an object paired with the previous slide it hides the object during the transition, and it appears a second time.
3. **Exit and path** — only for objects without a pair on the next slide, otherwise the object jumps back. Movement between slides is done by Morph itself.
4. Morphing keeps continuity ("this is the same object"). An effect adds an event inside a state ("here is a new one", "here is the main thing"). Do not duplicate one with the other.
5. A native transition marks a chapter boundary or a change of world; 1–3 kinds per presentation, each with its own meaning.
6. 3D model effects (`*_3d_*`) do not play on shapes. Do a 3D flip and rotation of a shape via Morph (section 8).

## 10. Components for technical and teaching presentations
`morphkit.components.Kit(theme)` — methods return lists of `O` with consistent names (the same id on adjacent slides = a Morph pair): `label`, `title` (font size auto-fit by metrics), `text`, `folio`, `rail`, `progress`, `card`, `stat`, `callout`, `node`, `link` (+ a path for `flow`), `flow`, `code` (Python highlighting, without conflicting with the markup), `terminal` (cursor for `blink`), `tree` (file tree), `table`, `bars`, `columns` (with a zero state), `bg_grid`. Tables and charts built from shapes morph, unlike built-in charts. Description — `references/components.md`.

## 11. XML fragments (the engine writes them itself — `morphkit/anim.py`)
**Transition** (in every `ppt/slides/slideN.xml`, N ≥ 2, right after `</p:clrMapOvr>`). `{adv}` = `advTm="100"` on a service slide that must advance by itself:
```xml
<mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"><mc:Choice xmlns:p159="http://schemas.microsoft.com/office/powerpoint/2015/09/main" Requires="p159"><p:transition xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main" spd="slow" p14:dur="1400" {adv}><p159:morph option="byObject"/></p:transition></mc:Choice><mc:Fallback><p:transition spd="slow" {adv}><p:fade/></p:transition></mc:Fallback></mc:AlternateContent>
```
**Shape adjustments:** clear `a:prstGeom/a:avLst` and write `<a:gd name=… fmla="val N"/>`. **The name comes from the preset:** for `roundRect`, `foldedCorner`, `chevron` — `adj`, for `blockArc` — `adj1`, `adj2`, `adj3`. XSD lets a wrong name through, but PowerPoint considers the file corrupted and throws out the shapes. For `roundRect` adj = radius / min(w, h) · 100000 — recompute it so that the rounding does not change as the card grows (the engine does this from `radius`).
**Transparency:** `<a:alpha val="40000"/>` inside the `a:srgbClr` of the fill or line (`fa=`, `la=`).
**Other transitions** — the same skeleton: an ISO element (`<p:push dir="r"/>`) in `mc:Choice Requires="p14"` (for the sake of `p14:dur`), and in `Fallback` — the same element without a duration. p14/p15 transitions: `<p14:vortex dir="r"/>`, `<p15:prstTrans prst="curtains"/>` in `mc:Choice Requires="p14|p15"` with both namespaces declared, in `Fallback` — `p:fade`.
**Appearance after Morph** (`anim_*`): `p:timing` → `tmRoot` → `mainSeq` → a single `par` with conditions `delay="indefinite"` + `evt="onBegin"`; for each object — a `par` with `delay` = 150 ms + i·380 ms (the timeline starts after the transition); inside, `presetID="42" presetClass="entr"`: `p:set style.visibility=visible`, `p:animEffect filter="fade"` 500 ms, `p:anim ppt_y` from `#ppt_y+.04` to `#ppt_y` with `decel="100000"`. Loops and `Fx` effects — in the same `par`, `nodeType="withEffect"`, with `repeatCount="indefinite"` on the effect node for repeating ones. Text with an effect needs `<p:bldP spid grpId="0" animBg="1"/>` in `p:bldLst`.
**Text:** turn off autofit in the frame (`a:noAutofit`), put line breaks explicitly, check the width with the substitute font's metrics (`lint`).
**Font:** one `a:latin` and right after it `a:cs`; a duplicate or the wrong order of `a:rPr` children is a schema error. LibreOffice forgives it, but PowerPoint "repairs" the file and throws out all slide content.
**Built-in shape style** (`p:style` from python-pptx): remove it — it adds a shadow and theme colours. Everything is set explicitly.
Rewrite the zip one file at a time via `zipfile`, without changing the order of parts.

## 12. Build: morphkit
```
scripts/morphkit/
  theme.py       themes (colour roles, fonts, scale, grid, density), contrast()
  model.py       O (object), Slide, Cam, Loop, text mini-markup, resolve() (camera, name uniqueness)
  components.py  Kit — the components from section 10
  anim.py        XML for transitions (53), appearances, loops and Fx effects on one timeline
  presets.py     Fx, registry of 198 shape animations (data/, MIT), TRANSITIONS, describe(), keys()
  vector.py      freeforms (shapely): boolean operations, petals, frame on the axis, resample, gradient, rot3d
  recipes.py     technique helpers: spotlight, dots + layouts, reveal, ring_fill, backdrop, flow_along, doc_arc, doc_pictograms, carousel, ranked_bars, draw_polyline, flip_fx, explode, circle_wipe
  profile.py     DeckProfile — presentation rules (text, speed, style lock, prohibitions), DEFAULT
  existing.py    Deck — "existing presentation" mode: speed, timing, service slides, text policy, effects, loops
  motif.py       recurring motif in roles: Flower, Orbit, MotifTrack (hero, pointer, backdrop, progress, data, portal, seed)
  process.py     process grammar: Carrier + verbs split/encode/relate/score/flag/filter/aggregate…, plan()
  palette.py     12 palettes with theme tags and a reason: suggest(text, k=3), check_catalog()
  build.py       build_pptx(slides, theme, out): shapes, text, notes, PowerPoint theme, Morph, animation timeline
  qa.py          lint() (incl. overlapping texts), fit_text() (line wrapping by metrics), xsd_check(), lo_effects_check(),
                 render() (PNG for checking), contact_sheet()
  preview.py     build_previews() — style previews
scripts/gallery.py         galleries of all transitions and animations (a visual reference + an engine test)
scripts/gallery_vector.py  gallery of vector techniques and 3D (with "what to check" notes)
scripts/gallery_concepts.py motif roles (flower, orbit) and process verbs (phrase → tokens → vectors → arcs → bars → flag)
scripts/gallery_hero.py    hero transformations: flower pointer beyond the edge, petal → panel, documents → graph, fragments → cards, "drops"
scripts/refs_frames.py     frames of a video reference at scene changes + thumbnail sheet (ffmpeg)
scripts/refs_deck.py       structure of a reference presentation: transitions, pairs, objects, effects with delays
```
Example:
```python
import sys; sys.path.insert(0, "<skill>/scripts")
from morphkit import LAB, Slide, Loop, build_pptx
from morphkit.components import Kit
from morphkit.qa import lint, print_issues, xsd_check
k = Kit(LAB)
srv, cli = k.node("srv", 1.5, 3, 2.4, 1.2, "Server"), k.node("cli", 9.4, 3, 2.4, 1.2, "Client")
wire, path = k.link("wire", srv[0], cli[0])
s = Slide(k.label("Data flow") + k.title("The server sends data") + srv + cli + wire,
          loops=[k.flow(path, n=3, period=2.4), Loop("pulse", target="!!srv", period=1.6, scale=1.05)],
          layout="pipeline", technique="camera", notes="[≈40 s] What happens in the diagram…")
print_issues(lint([s], LAB)); build_pptx([s], LAB, "deck.pptx"); assert not xsd_check("deck.pptx")
```
- Slides are the output of state-generator functions (`route(active)`, `pipeline(step)`): adjacent slides differ by a parameter, and the names match automatically.
- Text mini-markup: `plain {a:accent} {a2:second} {b:bold} {m:muted} {c:code} {x:strikethrough} {r:bad} {g:good}`. Nesting is not supported. Code is passed as ready-made runs (`Kit.code`), so that `{…}` in Python is not confused with the markup.
- **Take numbers on slides programmatically** from result files (json/csv), do not type them in by hand.

## 13. Lecture notes
In `reading` mode (lectures, walkthroughs) the slide holds the structure and key numbers, and **the notes are the detailed lecture text**: what we do, why, how, what will be asked at the defence, the typical mistake. Format: `[≈60 s]` time estimate, then 80–180 words of connected text. Service slides — "advances by itself". Notes do not duplicate the slide verbatim.

## 14. Working with an existing presentation (`morphkit.existing.Deck`)
If the user already has a good presentation, **it is not redrawn**: shapes, graph, documents, composition and texts stay shape for shape. Motion and timing change — via general operations:
```python
from morphkit.existing import Deck
d = Deck("deck.pptx")                       # python-pptx: all XML is preserved
d.inline_service_slides()                   # "zero" auto-slides -> growth inside the next slide (arcs — "Wheel",
                                            #   bars — "Appear", moved objects — a path from the former place)
d.speed(camera={13: 1100})                  # Morph ≤ 0.9 s (profile), individual slides get their own limit
d.fix_char_modes()                          # "by word/character" with many texts -> "by object"
d.text_policy()                             # card backings are separated from text; changed text fades out/in
d.retime(first_ms=150)                      # all timelines: start 0.15 s after the transition, intervals preserved
d.to_slides()                               # presentation sketch (O with scheme colours) for motion.preview — analysing others' presentations
d.remove(range(1, 28), ["!!packet1"])     # extra shapes (and their text layers) — gone
d.hide_zero_lines()                         # zero-length lines are not visible as a "dot" before growing (0×0 dots stay)
d.stagger(2, d.names(2, "!!fan"), "entrance_rise_up")         # entrance one by one from left to right
d.stagger(5, [["!!r0", "!!c00", "!!c01"], ["!!r1", "!!c10"]]) # a list inside a list — the group enters together (a row)
d.shift(5, 1100)                            # the slide's native animations — later, timeline start fits the new entrance
d.ripple(15, "!!node", color="F5A300")      # ripples around the MAIN dot (the ring lies beneath it)
d.flow_on(16, ["!!edge1", "!!edge2"])       # signal along connectors from a shared node: dots under the cards,
                                            #   the path ends at the card edge — they do not fly over text
d.regroup(23, "!!dot", cols=5, step=0.5)    # surviving dots gather into a dense block (99 → 15)
# graph without crossings: "document → node" links rebuilt (minimum-length matching + second links only
# where they cross nothing), geometry is recomputed on EVERY slide with these shapes (the camera stays intact)
plan = plan_edges_clean(docs, dots, group_of, max_per_source=2, obstacles=cards, fixed=fan)
d.rewire({"!!e0_0": ("!!doc0", "!!dot3_1"), ...})            # from the card edge to the dot centre
d.add(10, R.dots("pr", field, size=0.1))    # new engine objects in someone else's presentation (Morph pairs by name)
d.stack_under(6, [["!!m1", "!!m1~txt"], ["!!m2", "!!m2~txt"]])  # each next one — under the previous
d.stagger(6, cards, "entrance_fly", options={"direction": "left"})  # "dealing": they slide out from under the neighbour
d.move(11, "anim_note", y=2.5); d.line_style_like(2, names, ln_template)
d.fx(5, [Fx("emphasis_bold_flash", "!!row4")])                # any library effect
d.save("deck_v4.pptx"); print(d.log, d.report())
```
- Slide numbers start at 1. Call removing operations (`inline_service_slides`) first.
- Before editing — analyse the presentation's structure: `scripts/refs_deck.py deck.pptx --objects` (names, pairs, effects with delays).
- **Rework, not layering.** First the analysis: what is good in the presentation (keep), what gets in the way (remove: extra
  "buttons", placeholder dots on screen), which slides can be played with their own objects (table rows one by one,
  method steps as they go, surviving dots — into a block). New shapes — only loop carriers. The emphasis goes on
  the main object (dot no. 538), not on the caption next to it.
- Graph built from shapes: before the show, count the edge crossings (`crossings`). If there are many — `plan_edges_clean` +
  `rewire`; recompute the semantic highlighting (colour of edges to the highlighted node) from the new links. An edge that
  crosses the fan of the main example under any routing is better deleted than dragged across the slide.
- Collapsed 0 × 0 dots (`hide_zero_lines` does not touch them) remain in PowerPoint as small "trace" dots —
  the audience likes this ("99 → 15"); hide only zero-size lines and sheets.
- An example of reworking someone else's presentation end to end — `/deck-remix` (`../deck-remix/SKILL.md`): graph without crossings
  (`plan_edges_clean` + `rewire`), dot field, dealing cards, XSD and profile checks.
- If the presentation is monotonous or weak — first an analysis per `pptx-design` (composition, rhythm), then targeted replacement of slides with engine scenes.

## 15. Checking: measure first, then fix
1. `lint(slides, theme)` without errors (including "texts overlap"; `fit_text` wraps long lines in advance): lines fit (substitute font metrics, 1.5% margin; for approximate fonts — 10%), text height, font size ≥ the mode minimum, **contrast** of text against the background beneath it, objects do not stick out past the edge (except parking and `bleed`), emoji, word density, anti-patterns, loops (≤ 2, period 1–4.5 s), Morph pairs, variety of layouts and techniques.
2. **Strict XSD validation** of every slide and the notes (`xsd_check`; the `mc:AlternateContent` block is replaced by its `Fallback`): 0 errors. Then `validate.py` of the pptx skill — PASSED (if the skill is installed; otherwise `xsd_available()` = False — report that XSD was not checked). A PASSED alone does not guarantee that PowerPoint will open the file: check the `gd` adjustment names (section 11).
3. **Render and thumbnail sheet** (`render` → `contact_sheet`): look at every slide with fresh eyes — overlaps, clipped text, empty areas, parked objects in frame, the same layout in a row. If something is off — first find the cause by measuring (line width, coordinates), then fix the generator, not the XML.
4. Loops and `Fx` — by importing into LibreOffice: `lo_effects_check(pptx)['ok']` — every effect is recognised as `ooo-…`, custom signal trajectories are imported as motion. LibreOffice shows p14/p15 transitions only partially; watch them in PowerPoint.
5. Numbers are reconciled with the result files; speech duration from the notes ≈ 125 words/min.
6. LibreOffice does not play Morph or loops: ask the user to run the show in PowerPoint 2019+/365.
7. In the answer, briefly list which techniques are on which transitions and where the loops are.

## 16. Web presentations (HTML) — 0.3.0
The same `Slide`/`O` build into **one self-contained HTML file**: real Morph by `!!` names (outlines with different
point counts are resampled and aligned), effects, live scenes, sheet transitions, hand-drawn elements, clickable
objects and a presenter UI. The `.pptx` twin is built from the same slides with `for_pptx(slides)`.
```python
from morphkit.html import web, link, alt, for_pptx, export_html
web(slide, sec=2, fx=[{"key": "in.stamp", "target": "!!a", "delay": .2}], scenes=[{"k": "liquid", "glass": "!!q0"}])
link(o, slide=12, tip="details")          # button: slide | section | back | href | set | toggle | step
alt(o, "split", "rows", {"groups": o.copy(x=5)})   # state: the object springs to the variant on click
export_html(slides, theme, "deck.html", sections=[...], ui={"menu": "top", "hud": True}, lang="en")
build_pptx(for_pptx(slides), theme, "deck.pptx")
```
- **Rules:** Morph stays the main transition; sheets only at section boundaries and for link jumps. Every section has
  its own motion language (title entrance, Morph verbs, scenes). Numbers are clickable: a metric links to its evidence
  slide with a “back” button. Text does not morph unless `meta["morph_text"]` or `text_policy="morph"`.
- **Checks:** `morphkit.webdemo.shots(html, out)` — Playwright snapshots, 0 console errors; `morphkit.variety.report`
  — still transitions, verbs per slide, repeated layouts; lint/XSD of the `.pptx` twin.
- Example: `examples/demo_web.py OUT --lang en --shots`. Full reference: `references/web.md`; module contract:
  `scripts/morphkit/web/CONTRACT.md`.

## References
| File | When to read |
|---|---|
| `../pptx-design/SKILL.md` | presentation design: brief, composition, headers, 32 layouts, rhythm, infographics, reference analysis |
| `references/concepts.md` | recurring motif in roles, process grammar (text → verbs → scenes), palette with a reason |
| `references/loops.md` | loops: XML, timing, combining with Morph |
| `references/motion-library.md` | 198 animations and 53 transitions: `Fx` API, what to choose, joining with Morph |
| `references/vector.md` | freeforms, boolean operations, frame on the axis, shape morphing, gradients, 3D |
| `references/techniques.md` | 50 Morph recipes with helpers and the protocol for inventing new ones |
| `references/components.md` | Kit components API |
| `references/web.md` | web presentations (HTML): effects, drawing, scenes, sheets, presenter UI, `.pptx` twin |

_Russian original: SKILL.ru.md_
