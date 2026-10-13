# Vector and 3D: `morphkit.vector`

The module builds geometry in shapely (`pip install shapely`) and turns it into a freeform `a:custGeom` (`O(kind="vec")`). Coordinates are slide or world inches (`world=True`), the y axis points down. This is a programmatic analog of the PowerPoint menu "Shape Format → Merge Shapes", only reproducible and with exact control over the points.

To see everything with your own eyes: `python scripts/gallery_vector.py OUT_DIR --check` → `vector_gallery.pptx`. The presentation contains a flower with the "Spinner" entrance, a Morph wheel, shape morphing, fragmentation with scatter, a 3D flip, an isometric stack and an orbit. The notes of each slide say what to check in the slide show.

## Primitives and operations

| Function | What it gives |
|---|---|
| `circle(cx, cy, r)`, `ellipse`, `rect(x, y, w, h, r=rounding)`, `polygon(pts)`, `regular(cx, cy, r, n)`, `star(cx, cy, r_out, r_in, n)` | basic shapes |
| `sector(cx, cy, r_out, a0, a1, r_in=0)` | a sector or a ring segment (a "donut" chart made of shapes, a clock face) |
| `lens(center, r, gap, angle)` | a lens — the intersection of two circles |
| `petal(pivot, r_in, r_out, width, angle=-90)` | a petal from r_in to r_out around the axis (a lens of the required length and width) |
| `union(*g)` | Union |
| `intersect(a, b)` | Intersect |
| `subtract(a, *b)` | Subtract |
| `combine(a, b)` | Combine — exclusion |
| `fragment(*g)` | Fragment — all the pieces the shapes cut each other into |
| `slices(g, n, pivot)` | cuts a shape into n equal sectors |
| `rotate(g, deg, origin)`, `move(g, dx, dy)`, `scale(g, k, origin)`, `radial(g, n, pivot)` | transformations; `radial` — n copies around the axis |
| `resample(g, n=160, start="top")` | an outline of exactly n points, clockwise, starting at the top point — preparation for morphing |
| `shape(name, g, pivot=None, rot=0, frame=None, fill, ln, lw, grad, d3, …)` | an `O` object |
| `gradient(stops, angle=90, kind="linear"\|"radial"\|"rect")` | a gradient (a stop is `(position, role\|hex[, opacity])`) |
| `rot3d(x, y, z, depth, depth_color, bevel, camera, fov, material)` | 3D rotation and extrusion (`O.meta["d3"]`) — for any shape, not only `vec` |

Gradient and 3D fit any object: `O(..., meta={"grad": V.gradient(...), "d3": V.rot3d(...)})`.

## Technique 1. A frame on the axis (pivot) — rotation around any point

PowerPoint rotates a shape around the center of its frame, and Morph interpolates the rotation angle. If the frame is a square centered on `pivot` and the shape is drawn inside it with an offset, then `rot` and its morphing rotate the shape **around pivot along an arc**. An ordinary object in Morph travels **along a chord**, directly.

```python
PIV = (4.1, 4.05)
PET = V.resample(V.petal(PIV, 0.62, 2.55, 0.98), 120)          # one outline for all petals
petals = [V.shape(f"!!pet{i}", PET, pivot=PIV, rot=(i - turn) * 45, fill=col[i]) for i in range(8)]
```

- **Wheel or carousel.** On the next slide `turn + 1`: all petals rotate 45° around the center of the flower.
- **Orbit.** A satellite is a circle at radius R in a frame on the sun's axis. Rotating the frame moves it along the orbit.
- **The "Spinner" entrance** (`Fx("entrance_spinner")`) and the "Spin" emphasis also rotate such an object around pivot: the petals unwind from the center of the flower, as in the reference video.
- **Push out the active petal** — replace the outline with a longer one (`PET_ON`) with the same number of points. Morph morphs the shape and rotates it at the same time.

**Rotation rules.**
- The step per transition is **less than 180°**: PowerPoint rotates along the shortest path (a transition 315° → 0° goes +45°).
- A full turn within one Morph is not animated: 0° and 360° are the same state. Split it into 2–3 steps; the intermediate slides advance on their own (`Slide(auto=0)`).
- Move labels that must stay horizontal as ordinary objects: they travel along the chord. At a 45° step the deviation from the arc is ≈ 0.08·R — unnoticeable.

## Technique 2. Shape morph

Morph honestly morphs one freeform into another if both have:
- the same number of points;
- the same winding direction;
- the same start point;
- no more than one hole.

`resample(g, n)` gives all of this at once. `lint` warns if a pair has a different number of points or more than one hole.

```python
for k, g in enumerate([V.circle(cx, cy, 1.5), V.rect(..., r=0.45), V.star(cx, cy, 1.85, 0.78), drop]):
    Slide([V.shape("!!blob", V.resample(g, 160), fill=col[k])], …)
```

- A drop, a star, a heart and an arrow are assembled with `union`/`subtract` from primitives, then `resample`.
- Keep the colors of a pair close (section 9, item 6a of SKILL.md).
- A shape with two holes and the result of `combine` (a ring with a lens) do not morph: Morph replaces the morph with a fade.

## Technique 3. Fragmentation and scatter (explode)

1. Slide A: whole shapes.
2. Slide B: `fragment(...)` — pieces in the same places, each with its own name `!!fr{i}`. The A → B transition is almost unnoticeable.
3. Slide C: pieces moved away from a common center (`move(p, dx·k, dy·k)`). Morph pulls them apart, producing an "exploded" diagram (a Venn diagram in parts, the composition of a whole).

The reverse is assembly: C → B. Each piece is its own pair, so it can be recolored, labeled or carried to the next slide.

## Technique 4. 3D rotation

`rot3d(x, y, z)` is "3-D Rotation" in the PowerPoint interface: X — around the vertical (`lon`), Y — around the horizontal (`lat`), Z — in the plane (`rev`). Morph smoothly changes the 3D rotation. Text in the shape rotates with it.

- **Card flip** — two Morphs in a row, the intermediate slide advances on its own:
  - 1: front 0°, back 270° (edge-on, not visible);
  - 2 (`auto=0`, 450 ms): front 90° (edge-on), back 270°;
  - 3 (450 ms): front 90°, back 0°.
  
  The back comes out of 270° to 0° along the shortest path, in the same direction the front went: the flip is continuous and without mirrored text.
- **Isometric stack:**
  - flat tiles in a list → `rot3d(x=314.7, y=324.6, z=60.2, camera="orthographicFront", depth=8)` with a step in y — these are the values of the "Isometric Top Up" preset;
  - pipeline steps "fold" into architecture layers;
  - the reverse transition unfolds the stack into a list.
- **Tilting a card toward the viewer** (`rot3d(x=20, camera="perspectiveFront")`) — "focus" without enlarging.
- `depth` (pt) — extrusion with color `depth_color`, `bevel` — a bevel.
- Animation effects for 3D models (`*_3d_*`) do not play on shapes. Motion of a shape in 3D comes from Morph and 3D rotation.

**LibreOffice draws 3D approximately or flat**, so 3D is checked only in PowerPoint. On a LibreOffice thumbnail, a card rotated 270° appears flat on top of the front: this is a rendering quirk, not a file error.

## Gradients

- `gradient([(0, light), (1, color)], angle=90)`: `rotWithShape="1"`, the gradient rotates with the shape.
- For a shape in a frame on the axis, `fit=True` (the default) stretches the stops over the shape itself, not over the large frame. Otherwise a petal would get only a slice of the gradient.
- For an even fill take close shades of one color: `mix(col, "FFFFFF", 0.3)` → `col`. Rainbow gradients are an anti-pattern.

## QA

- `xsd_check` — 0 errors. Order in `spPr`: xfrm → custGeom → fill → ln → scene3d → sp3d. The engine writes it itself.
- Import into LibreOffice: every freeform has `draw:enhanced-geometry`, entrances have `ooo-entrance-…`.
- `lint` uses the real extent of the shape (`bbox`): a frame on the axis may extend beyond the slide — this is not an error.
- Rotation along an arc, shape morph and 3D — only in the PowerPoint slide show.

_Russian original: vector.ru.md_
