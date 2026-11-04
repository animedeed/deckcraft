# Loops and ordinary animations on top of Morph

## What lives where

| Layer | Defined by | When it works |
|---|---|---|
| Morph transition | `p:transition` (section 11 of SKILL.md) | between slides: `!!` pairs flow into each other, the rest fades in/out |
| Appearance after the transition | `anim_*` → `appear` effect | once, in turn, after the transition |
| Loops | `Slide(loops=[Loop(...)])` → effects with `repeatCount="indefinite"` | continuously, while the slide is on screen |

All effects of a slide are on one timeline: `tmRoot` → `mainSeq` → one "with previous" group from the start of the slide (`delay="indefinite"` + `evt="onBegin"`) → `nodeType="withEffect"` effects with their own delays. No clicks are needed.

## Five loops

### flow — a stream of dots along a path
```python
nodes_a, nodes_b = k.node("srv", ...), k.node("cli", ...)
wire, path = k.link("wire", nodes_a[0], nodes_b[0])      # arrow from edge to edge + path from center to center
Slide(objs + wire, loops=[k.flow(path, n=3, period=2.4)])
```
The path can be a polyline (`points=[(x1,y1),(x2,y2),(x3,y3)]`), coordinates in slide inches. In XML each dot is an oval `loop_…_dotI` with the effect:
```xml
<p:cTn presetID="0" presetClass="path" presetSubtype="0" repeatCount="indefinite" fill="hold" nodeType="withEffect">
  <p:stCondLst><p:cond delay="{start + i·period/n}"/></p:stCondLst>
  <p:childTnLst><p:animMotion origin="layout" path="M 0 0 L 0.56250 0.00000 E" pathEditMode="relative" ptsTypes="">
    <p:cBhvr><p:cTn dur="{period}" fill="hold"/><p:tgtEl><p:spTgt spid="…"/></p:tgtEl>
      <p:attrNameLst><p:attrName>ppt_x</p:attrName><p:attrName>ppt_y</p:attrName></p:attrNameLst></p:cBhvr>
  </p:animMotion></p:childTnLst></p:cTn>
```
The path is defined **in fractions of the slide size** relative to the start point (`motion_path()`): `L dx/13.333 dy/7.5`. The speed is constant, no acceleration (no `accel/decel`).
The queue trick: the dots wait for their delay at the start of the path. If the path starts at the center of the source node and the dots lie below the node (`z` 5 < 10), the waiting and the return to the start are not visible.
In the PowerPoint interface it is the same thing: "Motion Paths → Lines", "Effect Options → Repeat: Until End of Slide".

### pulse — a node "breathes"
emph 6 "Grow/Shrink": `animScale by x=y=scale·100000`, `autoRev="1"`, repeat. `period` — a full there-and-back cycle. Scale 1.04–1.10 for nodes, up to 1.2 for small markers.

### ripple — ripples on water
The engine creates a copy ring around the target (`loop_…_ring`, no fill) and puts in one node `animScale` (growth to `scale`) and `animEffect transition="out" filter="fade"`. Each cycle starts from the original size. Good for "the event happened here", "the lock is closed", "a signal".

### spin — rotation
emph 8 "Spin": `animRot by="21600000"` (360° in 60000ths of a degree) with repeat. For "training is in progress", "processing". Rotate symmetric shapes (a hexagon, a ring with a gap), not text.

### blink — blinking
emph 35 "Blink": a discrete animation of `style.visibility` hidden → visible at the middle of the cycle. For a terminal cursor (`Kit.terminal` returns the cursor name) and waiting indicators. Period 0.9–1.2 s.

## Combining with Morph

1. **A loop object is never a Morph pair.** A motion path and scale change the rendering, while Morph takes static coordinates — there would be a jerk. `resolve()` forbids `!!` on `loop_…`. Putting pulse and spin on a `!!` node is allowed (they return to the original state), but then the transition starts from the frame where the effect was cut off. If it matters, put the pulse on a separate underlay ring without a pair.
2. **The diagram morphs, the stream is recreated.** On each slide the loops are described anew for the new coordinates. The old dots fade out during the transition, the new ones start after it.
3. **Order:** transition → slide timeline (starts after the transition ends — confirmed by a slide show recording) → loops after 150 ms + `start`, `anim_*` after 150 + i·380 ms. Do not add the Morph duration to the delays: the loop would start with a visible pause.
3a. **Carriers are hidden until the start.** Before the cycle, each `flow` dot and `ripple` ring gets the "Appear" entrance (presetID 1, entr) with the same delay. Until the start the object is invisible, including during Morph: the queue of dots under the node does not flicker during the transition.
3b. **Highlight a step with a frame.** Do not recolor a node via Morph between distant colors (orange → blue gives brown): `Kit.marker(node)` — a `!!marker` pair that moves to the new node.
4. **Rhythm:** the periods of different loops on a slide are not multiples of each other (2.2 and 1.6 s), so there is no mechanical "march". The dots of one loop go evenly (offset period/n).
5. **Measure:** ≤ 2 loop systems per slide (loops with a common name prefix up to "_" — `sig_a`, `sig_b` — are one system: for example, a signal from one source along three edges); within a section — not on every slide. A loop explains a process (what flows, what works, what waits), it does not decorate.
6. **Color:** stream dots — the `flow` role (usually the accent), size 0.10–0.16″; on a dark background they can be brighter, on a light one — a saturated dark.

## Ordinary animations without loops

One-off effects are made with the same mechanism: `anim_*` — appearance (fade + rise). The order is set by `Slide(anims=[…])`. Any other PowerPoint effect (198 of them) — `Slide(fx=[Fx(…)])`, see `motion-library.md`. On-click build requires a separate `par` with `delay="indefinite"` for each click (not enabled in the engine by default: presentations are driven by transitions).

## QA without PowerPoint

1. `xsd_check(pptx)` — 0 errors (the effects are valid against the PresentationML schema).
2. Import into LibreOffice: `soffice.py --headless --convert-to odp deck.pptx`, then in `content.xml`:
   - `smil:repeatCount="indefinite"` — one for each loop;
   - `presentation:preset-id="ooo-emphasis-spin"` / `-blink` / `-grow-and-shrink` — the presets are recognized;
   - `anim:animateMotion … svg:path="M 0 0 L …"` — the stream paths.
3. The motion itself — only in PowerPoint 365/2019+ (F5): LibreOffice does not play Morph.

_Russian original: loops.ru.md_
