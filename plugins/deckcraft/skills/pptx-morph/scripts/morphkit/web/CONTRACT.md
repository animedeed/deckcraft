# deckcraft 0.3.0 web engine: module contract

The core is `core.js` (+ `base.css`), the build is `../html.py`, the check is `../webdemo.py`. Modules are separate
files in this folder; `html.py` concatenates them into one HTML file in the order `core.js`, `draw.js`, `fx.js`,
`scenes.js`, `sheets.js`, `ui.js`, then the other `*.js`; CSS — `base.css`, then the other `*.css` alphabetically. A
module only **registers** functions on the global `window.DC`; `DC.start()` runs at the end of the page (after all
modules).

**Rules for module authors**

* Your file is yours only: `draw.js`/`draw.py`, `fx.js`, `scenes.js`/`scenes.py`, `sheets.js`/`ui.js`/`ui.css`. Do not
  edit `core.js`, `base.css`, `html.py`, `webdemo.py` — describe the core change you need in your report.
* No external libraries or network; everything is deterministic (`DC.u.rng(seed)`), colours come from
  `DC.data.colors` (theme roles: bg, surface, surface2, line, ink, ink2, muted, accent, on_accent, accent2, accent3,
  good, warn, bad, code_bg, code_ink …), fonts — `DC.data.fonts.head/body/mono`.
* Performance: no DOM rebuilding per frame — cache nodes in `node`/`inst`; target 60 fps with 300 objects.
* `DC.REDUCED` (prefers-reduced-motion): effects in their final state, scenes draw the final frame, no loops.
* Cyrillic everywhere; UI captions follow the presentation language (`DC.data.lang` ru|en; in ui.js — `DC.ui.tr`).

## Coordinates and time

The stage is 1600×900 px; **1 inch = 120 px** (the slide is 13.333×7.5 in). Object fields `o` are in **px**:
`x, y, w, h` (frame), `r` (rotation, degrees, around the frame centre), `z`. In an effect state `st` the offsets
`dx, dy` and `clip` are in **inches** (as in the Python preview `morphkit.motion`), `tx, ty` — in px. Effect time is
seconds after the transition into the slide ends (minus `DC.data.fxStart` = 0.15 s); `steps` shift the start of their
effects to the moment of the click.

## Object (JSON from Python)

`{n, k: "path"|"line"|"img"|"text", x, y, w, h, r, z, f (fill #hex|null), fa, s (stroke), sw (px), la, dash, head,
rings (normalised outlines [[x0,y0,x1,y1,…], …] in frame fractions), grad {a, kind, stops [[pos, #hex, alpha]]},
t {lines [[[text, color, bold, mono], …], …], sz (pt), col, b, font, mono, al l|c|r, va t|m|b, sp, pg, tr, inset, lh},
img, link, tip, ease, lag, draw, when, web}`

* `link` — a button: `{slide: i}` | `{section: k}` | `{back: true}` | `{href}` | `{set: {key: value}}` |
  `{toggle: key, values: [...]}` | `{step: true}`. The core adds the click and the `.dc-link` class; link jumps push the
  current slide onto `DC.backStack` (Backspace / `DC.back()` return).
* `tip` — a tip: the core emits `DC.emit('tip', o, event, on)` on hover (the UI draws it; fallback — `<title>`).
* `when` — `{key, is, dflt}`: the object is visible only while `DC.state[key] == is` (0.35 s fade) — A/B switches.
* `alt` — `{key, dflt, values: {value: {x, y, w, h, r, f, fa, s, sw, la, rp}}, dur, ease}`: object states — on
  `DC.setState(key, v)` (`link set/toggle` buttons) the object moves to the variant (0.65 s spring). Python:
  `morphkit.html.alt(o, key, dflt, {value: variant O})`.
* `ease` — this object's Morph curve (`DC.ease`: linear, inOut, out, in, back, elastic, spring, bounce + your own).
* `lag` — Morph delay of the object, s (cascades); a slide has `cascade: {by: "x"|"y"|"radial"|"-x", amount}`.
* `draw` — a drawn-element spec `{kind, ...}`; if `DC.draw[kind]` is registered, the draw module renders the object
  (the core builds no `path`).

## Slide (JSON)

`{title, notes, dur (Morph ms), tr ("morph"|"none"|native PowerPoint key), bg, objs, fx {name: [[key, start, dur, opt,
step, cat], …]}, loops [...], scenes [...], steps [[names], …], sec (section number), sheet, jumpSheet, cascade, label,
nav, autoState [{at, set, reset}]}`; the deck: `{slides, pool, imgs, colors, fonts, sections [{title, start}], title,
jumpSheet, lang, ui, …}`.

Transition to the adjacent slide: `tr == "morph"` and no `sheet` → Morph by `!!…` names (outlines with different point
counts are aligned by length and shift); otherwise the `sheet` (default `fade`). A link/menu jump to a distant slide:
Morph too if the slides share ≥ 5 pairs, otherwise `jumpSheet` (or `DC.data.jumpSheet`, or `fade`).

## Registries

### `DC.fx[key] = (o, e, p, opt, sl) => st` — effects

* `key` — a name with a category prefix: `in.*` (entrance), `em.*` (emphasis), `out.*` (exit), `path.*`. PowerPoint
  preset keys (`entrance_fade` …) are handled by the core; a module may override them by registering the same key.
* `p` — linear progress 0..1, `e` — after the curve (`opt.ease` or inOut), `opt` — parameters from Python (the core adds
  `opt._dur`, the duration in s), `sl` — the slide.
* Returns a **state** `st` (all fields optional):

| field | meaning |
|---|---|
| `alpha` | opacity (multiplied) |
| `scale`, `sx`, `sy` | scale around the frame centre (multiplied) |
| `dx`, `dy` (in), `tx`, `ty` (px) | offset (added) |
| `drot` | extra rotation, degrees (added) |
| `skewX` | skew, degrees |
| `clip` | `[x0, y0, x1, y1]` inches — the visible rectangle |
| `blur`, `bright`, `sat`, `hue` | CSS filters (px, multipliers, degrees) |
| `glow` (+`glowR`), `shadow` | coloured glow / shadow `"dx dy r color"` |
| `drawP` | 0..1 — “drawing” the stroke of a path/line |
| `chars` | show the first N characters of the text (typing) |
| `col` | text colour |
| `fill`, `outline` | fill / stroke over the original |
| `dz` | layer offset |
| `t` | replacement text spec (`{...o.t, lines: …}`) — counters, substitutions |
| `textFx` | `{k, ...}` — render the text with `DC.textFx[k](node, o, st, surface)` (per-letter effects); the renderer works in `node.tg` and sets `node.tfx = true` |

* An entrance hides the object before it starts, an exit — after it ends; `h.hold = true` keeps the final state after
  the end (for “recolour and keep” emphases).
* Text morph: `DC.textMorph = (a, b, t, o) => [[obj, alpha, st?], …]` — called by the core for `!!…` pairs with
  different text (and for shapes with a caption: the outline morphs without text, the caption arrives here as a text
  object). Items are drawn with keys `name`, `name#1`, `name#2`…; `st` (optional) is the item state (`textFx`, `dx` …),
  its `alpha` is multiplied. Pairs with changed text reach the web only with `export_html(..., text_policy="morph")` or
  `meta["morph_text"] = True` on the object (default — the profile rule “text does not morph”: the pair is split).
* `DC.REDUCED`: the core itself gives entrances and emphases their final state (p = 1); exits stay visible to the end.

### `DC.loops[kind] = (lp, byName, tt, sl, index) => items` — loops until the end of the slide

`items` — `{key, o, st}` (new objects) or `{replace: name, st}` (a state over a slide object). Built in: flow, pulse,
ripple, spin, blink.

### `DC.scenes[kind] = { mount(ctx, params) => inst }` — live scenes

`inst = { frame(t, ctx), unmount() }`; `t` — seconds after the transition (as for effects). `ctx`: `layer` (an own
`<g>` in the `params.layer` = "over" | "under" layer), `canvas()` → a 2D context over the whole slide (foreignObject;
the core rasterises it into an `<image>` in the snapshot for a sheet transition), `obj(name)` → a slide object (the
current variant for objects with `alt`), `mod(name, fn)` — a per-frame object modifier `fn(o, st, t) => [o2, st2]`
(change a copy: outline, level, colour; return null to hide); the core chains the modifiers of all scenes on one name
(the same function — once). `T` — colours, `reduced`, `u` — utilities, `sl` — the slide. `frame(t)` is also called
during the transition with t < 0 (start frame), modifiers too (the Morph target); the Morph out of a slide starts from
its last frame after modifiers and states (`sl.last`), objects hidden on leaving do not pop up. Scene parameters come
from Python: `web(slide, scenes=[{"k": "pour", ...}])`.

### `DC.sheets[kind] = (p, A, B, ctx) => void` — sheet transitions

`A` — the `<svg>` snapshot of the previous frame (on top), `B` — the live `<svg>` of the new slide (underneath; its
entrances wait for the sheet to end). The module changes the `style` of A and B (transform, clip-path, opacity,
filter, 3D — `#dc-stage` has perspective). `p` — progress after the curve, `ctx = {dur, opt, stage, from, to, u, raw}`.
After the sheet the core removes A and resets `B.style`.

### `DC.draw[kind] = (node, o, st, surface) => void` — drawn elements

`node.dg` — an empty `<g>` (created by the core when the kind changes); the module caches its own elements in `node`.
Respect `st.drawP` (drawing), `o.draw` (parameters), the frame `o.x/y/w/h` (px); the core applies rotation.
`DC.draw._interp(a, b, t)` — optional: interpolate two specs of one kind during Morph.

### Events and navigation

`DC.on(ev, fn)`: `ready`, `slide (i, from, opts)`, `step (i, n)`, `frame (t, sl)`, `link (link, o)`, `tip (o, e, on)`,
`state (state)`, `trans (kind, on, trans)` — start (`on = true`) and end of a transition (Morph or sheet). Every surface
node has `node.wrap.dcObj` — the object it draws (link highlights, screen-reader labels). `DC.t0` — a getter of the
slide entry time (performance.now). Core keys do not fire with Ctrl/Alt/Meta or in input fields, and Enter/Space do not
fire on a focused button. The core adds a system `<title>` to objects with `tip` only when there is no `DC.ui` module.
Text keeps its spaces (`white-space: pre`) — monospace code columns match the .pptx. API: `DC.go(i, {push, instant})`,
`DC.next()`, `DC.prev()`, `DC.back()`, `DC.cur`, `DC.backStack`, `DC.renderStatic(i)` → `<svg>` of the final frame
(overview, print, thumbnails), `DC.snapshot()`, `DC.keys[key] = fn` (keys; the core takes the arrows, PgUp/PgDn, Space,
Enter, Home/End, Backspace), `DC.clickAdvance` (false — a click on the stage does not page), `#dc-overlay` — an HTML
layer over the stage for the UI.

## Python

```python
from morphkit.html import web, link, export_html
from morphkit.webdemo import build, shots

s = Slide(objs, ...)
web(s, sec=2, sheet={"k": "sheetIn", "dur": 800}, steps=[["!!a", "!!b"], ["!!c"]],
    fx=[{"key": "in.stamp", "target": "!!a", "delay": .2, "dur": .45, "options": {...}}],
    scenes=[{"k": "pour", "from": "!!q0", "layer": "over"}], cascade={"by": "x", "amount": .3})
link(o, slide=12, tip="details")
path = build([s1, s2], "demo.html", sections=["Section 1", "Section 2"])
r = shots(path, "out/", times=[.4, 1.2, 3.0]); assert not r["errors"]
```

Web effects do not go into the .pptx; `draw` objects are their fallback form there (a `vec` ribbon), in HTML — real SVG.

_Russian original: CONTRACT.ru.md_
