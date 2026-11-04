# Motion library: 198 shape animations and 53 transitions

The source of the animations is the registry `scripts/morphkit/data/pptx_animation_presets.json`. This is XML captured from PowerPoint 16 files (the PPT Master project, MIT, see `data/NOTICE.md`). There are 203 effects in total; 5 of them (`*_3d_*`) animate 3D models and do not play on shapes. `keys()` does not return them, `lint` treats them as an error.

To see everything with your own eyes: `python scripts/gallery.py OUT_DIR --check` → `transitions_gallery.pptx` (53 slides, one transition per slide) and `fx_gallery.pptx` (26 slides, eight samples per slide, the effects play in turn). Both pass XSD.

## API

```python
from morphkit import Fx, Slide, TRANSITIONS
from morphkit.presets import keys, describe

keys("entrance")              # 52 keys; also "emphasis" (30), "path" (64), "exit" (52)
describe("entrance_fly")      # name, class, presetID, default duration, parameters and their values

Slide(objs, transition="vortex", trans_opts={"dir": "l"}, dur=1600, fx=[
    Fx("entrance_spinner", "!!flower", dur=0.9),                       # the first Fx starts at 0
    Fx("entrance_fade", "cap", start="after", delay=0.1),              # after the previous ones finish
    Fx("emphasis_spin", "gear", dur=4, repeat=True, start="with"),     # together with the previous one, until the end of the slide
    Fx("emphasis_grow_shrink", "kpi", options={"size": 115}, rev=True, start="after"),
    Fx("emphasis_change_fill_color", "cell", options={"color": "accent"}, start="after"),
    Fx("path_circle", "orbit_dot", dur=6, repeat=True, path_size=(3, 3), start="at", delay=0.4),
    Fx("path_custom", "dot", path=[(2, 3), (6, 3), (6, 5)], dur=1.2, start="after"),
    Fx("exit_fly", "old", options={"direction": "left"}, start="after"),
])
```

- **Start** — as in the PowerPoint animation pane. `with` — simultaneously with the previous Fx, plus `delay`. `after` — when all previous non-repeating Fx have finished, plus `delay`. `at` — from the start of the slide timeline, plus `delay`. The timeline starts when the transition has finished.
- **dur** scales all nodes of the preset proportionally. This applies to multi-stage effects too: Spinner, Boomerang, Credits. **repeat** — "Repeat: Until End of Slide". **rev** — "Rewind when done playing" (auto-reverse).
- **options**:
  - `direction` — direction: up, left, in, out, horizontal_in…;
  - `amount` — rotation angle in degrees (`emphasis_spin`), opacity 0–1 (`emphasis_transparency`) or number of spokes (`entrance_wheel`: 1, 2, 3, 4, 8);
  - `size` — scale in % (`emphasis_grow_shrink`);
  - `color` — a theme role or hex (color-change effects);
  - `font_name` — font.
- **Paths.**
  - Built-in paths are defined in fractions of the slide. The `path_circle` preset on a 16:9 slide is a 3.3″ × 1.9″ ellipse. `path_size=(w, h)` sets the required extent in inches.
  - `path_custom` takes a polyline in inches from `path`: the object is offset by (p − p0).
  - You can also pass a ready-made `animMotion` path string, with `C` curves.
- Library effects, `anim_*` appearances and `Loop` loops live on one slide timeline and do not interfere with each other.

## What to use for educational and technical presentations

| Task | Effect | Why |
|---|---|---|
| calmly introduce a new object | `entrance_fade`, `entrance_wipe` (in reading direction), `entrance_faded_zoom` | no "circus", does not compete with Morph |
| show growth, filling | `entrance_wipe` direction=up for a bar, `entrance_stretch` | the direction matches the meaning |
| radial assembly (wheel, flower, clock face) | `entrance_spinner`, `entrance_wheel` (amount = number of sectors), `entrance_pinwheel` | rotation emphasizes "in a circle" |
| accent on a number | `emphasis_grow_shrink` size 110–120 + rev, `emphasis_bold_flash` | short and reversible |
| "here is an error" | `emphasis_teeter`, `emphasis_change_fill_color` to the bad role | teetering reads as "wrong" |
| a process is running | `emphasis_spin` repeat, `path_circle` repeat with `path_size` | background loops (better via `Loop`) |
| remove clutter before Morph | not needed: Morph itself fades out objects without a pair | an exit would duplicate the transition |
| an object leaves as part of the story within the slide | `exit_fade`, `exit_fly` in the direction of motion | only if the object is not on the next slide |

Expressive effects (`bounce`, `boomerang`, `credits`, `light_speed`, `swish`, `sling`) — for title slides and humorous inserts, no more than one per section. Do not use `random_effects`: the result is unpredictable.

## Joining animations with Morph (verified by a slide show recording and PowerPoint rules)

1. **The slide timeline starts after the transition.** Delays must not include the Morph duration: the first effect comes after 0–150 ms.
2. **A Morph pair takes the geometry of the static slide.** The end state of animations is not taken into account. Hence two rules that `lint` checks:
   - an **entrance** on an object that has a pair on the previous slide: during the transition the object is hidden, then it appears a second time. Give entrances to new objects;
   - an **exit or path** on an object that has a pair on the next slide: at the start of the transition the object jumps to its static position. Move such objects with Morph itself (a new position on the next slide), not with a motion path.
3. **Objects with an entrance are hidden until their start, including during the transition.** The `flow` loop uses this: the dots get the "Appear" effect (entr 1) at the moment of start, so they do not flicker in the queue under the node.
4. **Do not recolor a pair via Morph between distant colors.** Orange → dark blue passes through a muddy brown. You need a moving marker frame (`Kit.marker`) or a color change with the `emphasis_change_fill_color` effect after the transition.
5. **More than 12 effects on a slide** is a sign that the slide should be split into Morph steps. The steps can advance automatically: `Slide(auto=…)`.

## 53 transitions (`Slide(transition=…, trans_opts=…, dur=…)`)

| Group | Keys | XML |
|---|---|---|
| ISO, any version | fade push wipe split cover random blinds checkerboard comb cut dissolve random_bars shape uncover clock wheel box wedge plus diamond strips | `<p:…>`, duration `p14:dur` — in the `mc:Choice Requires="p14"` branch |
| PowerPoint 2010+ (p14) | zoom reveal flash ripple honeycomb glitter vortex shred switch flip gallery cube doors pan ferris_wheel conveyor rotate window orbit fly_through | `mc:Choice Requires="p14"`, fallback `p:fade` |
| PowerPoint 2013+ (p15) | fall_over drape curtains wind prestige fracture crush peel_off page_curl airplane origami | `<p15:prstTrans prst="…"/>`, fallback `p:fade` |
| PowerPoint 2019/365 | morph | `<p159:morph option="byObject|byWord|byChar"/>` |

`trans_opts` overrides attributes: `{"dir": "l"}` (push, wipe, cover, vortex…), `{"orient": "vert"}` (split), `{"invX": "1"}` (mirrored for p15).

**How to choose a transition.**
- Morph is the main one: it links neighboring states.
- A native transition marks a **chapter boundary** or a change of "world": cube/rotate — a new section, gallery/conveyor — a strip of examples, curtains — the finale, vortex/shred — "broke it" (an error, a counter-example).
- Different native transitions in a row are noise. 1–3 kinds per presentation, each with its own meaning.

**LibreOffice** recognizes ISO transitions and part of p14/p15: ripple, honeycomb, glitter, vortex, cube, rotate, orbit, flash, fall_over. It does not show the rest, but PowerPoint plays them. Therefore import into ODP checks only the ISO group. Check p14/p15 by eye in PowerPoint using `transitions_gallery.pptx`.

## QA

1. `xsd_check` — 0 errors. The `mc:Choice` branch is not part of the ISO schema and is checked only by parsing the XML.
2. Import into LibreOffice: in `content.xml` every effect has `presentation:preset-id="ooo-entrance-…"`, `ooo-emphasis-…`, `ooo-exit-…` or `ooo-motionpath-…`. In the gallery LibreOffice recognized all 198 shape effects.
3. Motion and p14/p15 transitions — in PowerPoint (F5) or from the user's slide show recording.

_Russian original: motion-library.ru.md_
