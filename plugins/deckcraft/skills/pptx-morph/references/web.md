# Web presentations (deckcraft 0.3.0): one generator — HTML and .pptx

The same `Slide` and `O` used for PowerPoint build into **one self-contained HTML file**: real Morph by `!!…` names
(outlines with different point counts are resampled and aligned), effects, live scenes, sheet transitions, hand-drawn
elements, clickable objects and a presenter UI. The `.pptx` twin is built from the same slides (`for_pptx`).

```python
from morphkit.html import web, link, alt, for_pptx, export_html
from morphkit import draw as d

s = Slide(objs, ...)
web(s, sec=2, sheet={"k": "iris", "dur": 800}, steps=[["!!a"], ["!!b"]],
    fx=[{"key": "in.stamp", "target": "!!a", "delay": .2, "dur": .45}],
    scenes=[{"k": "liquid", "glass": "!!q0"}], autoState=[{"at": 2.0, "set": {"lr": "1"}, "reset": {"lr": "0.001"}}])
link(o, slide=12, tip="details")                       # button: slide | section | back | href | set | toggle | step
alt(o, "split", "rows", {"groups": o.copy(x=5.0)})     # object state: a button makes it spring to the variant
o.meta["when"] = {"key": "part", "is": "val", "dflt": "train"}   # visible only for this value
export_html(slides, theme, "out/deck.html", title="…", sections=[...], ui={"menu": "top", "hud": True},
            jumpSheet={"k": "zoomThrough", "dur": 700})
build_pptx(for_pptx(slides), theme, "out/deck.pptx")   # interactivity folded into the default state
```

The presenter UI language (tips, overview, help, presenter view), the title-block labels and the number format of
drawn elements follow `lang` (default — the current `morphkit.i18n` language). A ready example —
`examples/demo_web.py OUT --lang ru|en --shots`: the demo presentation with a clickable menu, its own title entrance
in every section, a slide of state buttons and a slide of hand annotations.

Checks: `morphkit.webdemo.shots(path, out, times=[.6, 3.0], slides=None)` → `{"errors", "files", "sheet"}` —
Playwright snapshots and console errors (must be 0); `morphkit.variety.report(slides)` — monotony in numbers (share of
still transitions, motion verbs per slide, longest run of similar layouts).

## Rules (lessons from shows)

* **Morph is the main transition.** A sheet (`sheet`) goes on section boundaries and on link jumps (`jumpSheet`); a
  jump between slides with ≥ 5 shared pairs is Morph.
* **Text does not morph** by default: a `!!…` pair whose text changed is split (the old one leaves, the new one comes).
  For numbers and short labels — `meta["morph_text"] = True` or `export_html(..., text_policy="morph")`: numbers count,
  shared letters slide into place.
* **Every section has its own motion language**: title entrance, Morph verbs, scenes; a transition where nothing
  moved (`variety`: energy < 0.02) is a signal to rework the slide.
* **Numbers are clickable**: a metric links to its evidence slide with a “← back” button (Backspace).
* **Reduced motion** (`prefers-reduced-motion`): effects jump to their final state, scenes show the final frame, loops
  are off.

## Effects (`web(..., fx=[...])`, fx.js)

Keys carry a category prefix; every effect takes `options.ease`, random ones — `options.seed`; the duration arrives as
`opt._dur`. PowerPoint presets (`entrance_fade` …) work too.

* **Entrances (38):** `in.fade`, `in.rise`, `in.zoom`, `in.zoom-out`, `in.pop`, `in.drop`, `in.bounce`, `in.elastic`,
  `in.back`, `in.flip`, `in.unfold`, `in.spin`, `in.swing`, `in.blur`, `in.ink`, `in.glitch`, `in.iris`,
  `in.slide-l/r/u/d`, `in.reveal-l/r/u/d` (soft-edged wipe), `in.stamp` (jerky print), `in.registration` (offset ink),
  `in.write` (line by line), `in.type` (typing with a cursor), `in.scramble` (decoding), `in.count` (the number grows,
  its format is kept), `in.highlight` (marker underlay), per letter — `in.letters`, `in.wave-letters`,
  `in.split-letters`, `in.words`, `in.rain-letters`, `in.pop-letters`.
* **Emphases (20):** `em.pulse`, `em.shake`, `em.wobble`, `em.jello`, `em.heartbeat`, `em.glow`, `em.flash`, `em.tada`,
  `em.float` (with `repeat`), `em.color` (holds), `em.swing`, `em.rubber`, `em.dim` (holds), `em.wave`, `em.grow`
  (holds), `em.spin`, `em.reg`, `em.glitch`, `em.mark` (marker, holds), `em.jump`.
* **Exits (23):** `out.fade`, `out.zoom`, `out.drop`, `out.slide-l/r/u/d`, `out.blur`, `out.shrink`, `out.burn`,
  `out.flip`, `out.fold`, `out.spin`, `out.erase-l/r/u/d`, `out.type`, `out.glitch`, `out.ink`, `out.words`,
  `out.letters`, `out.scatter-letters`.
* **Drawing** (`in.draw*`, `em.draw*`) — for drawn elements, see below; `in.draw` on lines and paths draws the stroke.

## Drawn elements (`morphkit.draw`, draw.js)

Every function returns a list of `O`: the first is the element (SVG in HTML, drawn along its strokes, parameters morph
between slides), the rest are fallback parts for .pptx. Common parameters: `style` (`blueprint` — for dark backgrounds,
`ink` — wobbly ink, `marker`, `riso` — overprint with a second ink, `chalk`), `color` (role, hex or `"role/30"`), `lw`,
`seed`, `z`.

`line`, `arrow` (arc `bend`, hand-drawn `hand`, polyline `via`, `double`), `dim_h` / `dim_v` (dimensions), `balloon`,
`leader`, `brace` (curly / square, with a label), `hatch` (hatch, cross, grid, halftone), `highlight`, `scribble`,
`encircle` (circle by hand), `mark` / `check` / `cross` / `asterisk`, `stamp` (round seal / rectangular stamp),
`sticker`, `tape`, `gost` (sheet frame and title block), `ruler`, `gauge`, `clock`, `write` (handwriting), `block`
(flowchart: process, terminator, data, decision, document, predef).

Effects: `in.draw`, `in.draw-linear` (handwriting), `in.draw-stamp`, `in.draw-drop` (sticker), `in.draw-reg`,
`in.draw-pop`; `em.draw-redraw`, `em.draw-boil` (with `repeat`), `em.draw-to {value}` (gauge needle / dimension to a
value), `em.draw-run {minutes}` (the clock runs), `em.draw-needle`.

Example — a “printout” annotation over a code block: `d.encircle(…)` around a value, `d.arrow(..., hand=True)` and
`d.write(…)` with a note; effects `in.draw` → `in.draw-linear` one after another.

## Sheet transitions (`sheet` / `jumpSheet`, sheets.js)

`sheetIn`, `sheetUp`, `sheetDown`, `push` (`dir`, `parallax`), `cover`, `uncover`, `fold` (3D), `flip`, `cube`, `iris`
and `diamond` (from the click point), `blinds`, `curtain`, `ink` (a blot with splashes), `zoomThrough`, `dissolve`,
`glitch`, `pageCurl`, `shutter`, `fade`. Going back plays them in reverse. Parameters go into the `sheet` object:
`{"k": "iris", "dur": 800, ...}`.

## Presenter UI (ui.js, `ui={...}` in `export_html`)

`menu`: `top` (section bar with a sliding highlight) | `tabs` (tabs on the right) | `stamp` (engineering title block) |
`none` (your own menu on the slides); `hud` — a corner panel (shows on mouse movement). Keys: ← → / PgUp PgDn / space
— page (steps by clicks), O or Esc — overview, P — presenter view (notes, timer, next slide, sync), D — pen (E eraser,
Z undo, C clear), L — laser, N — notes, digits + Enter — go to a slide, Backspace — back along a link, F — full screen,
B — black screen, ? — help; print / PDF — one page per slide. Keys also work in the Russian layout; links are
reachable with Tab.

## Live scenes (`web(..., scenes=[...])`, scenes.js)

Scenes draw over the slide (`layer: "over" | "under"`) and modify objects every frame (wine level, outline, colour);
the Morph out of a slide starts from the scene's last frame. Python: `from morphkit import scenes as SC` — constructors
with parameter checks (inches, pt, seconds; colours — theme roles). Common parameters: `character` (calm | lively |
dramatic — speed, amplitude, density, overshoot), `delay`, `step` (on click), `seed`, `layer`.

* `liquid(glass, level_from, level_to, …)` — wine in a `Glass`: the wave settles after the transition and the pour,
  ripples, bubbles, foam, a highlight; the surface stays level in a tilted glass too.
* `pour(src, dst, …)` / `pour_into(glass, from_obj, level_from, level_to)` — a stream that accelerates, with drops,
  splashes and rings; from a bottle neck or a tilted glass, with the fill.
* `bubbles`, `drip`, `stain` (spreads and dries with a ring), `ripple`.
* `particles(n ≤ 6000, layouts, shares, colors, labels, …)` — layouts cloud, clusters, grid, groups, bars, into (into
  glasses: the particles fall inside and dissolve in the wine); phases — `SC.phase(kind, at, dur, stagger)`.
* `signal(layers, edges="auto", …)` — pulses along graph edges layer by layer, node flashes, bars and a number at the
  output.
* `counter`, `clock` (hand and an event log by the hour), `gauge` (springy needle, zones, interval band, zero),
  `terminal` (commands type out, output by lines, cursor, scrolling).
* `sparks`, `confetti`, `grain` (paper / film), `halftone`, `chart_draw` (a chart line draws itself with marks),
  `bars_grow` (bars grow, labels ride on top).

Scenes are visible during the transition too (start frame); with reduced motion — the final frame right away (after
their `step`).

## Modules and contract

Core `web/core.js` + `base.css`, modules `draw.js`, `fx.js`, `scenes.js`, `sheets.js`, `ui.js` (+ `ui.css`); the
contract for module authors — `scripts/morphkit/web/CONTRACT.md`. Demos and checks: `python3 -m morphkit.demo_fx OUT
--all`, `demo_draw OUT`, `demo_scenes OUT`, `demo_ui OUT` (from the `scripts` folder).

_Russian original: web.ru.md_
