# Slide composition

Slide 13.333″ × 7.5″, 12-column grid (margins 0.65″, gutter 0.25″, column ≈ 0.774″). Lines of thirds: x = 4.44″ and 8.89″, y = 2.5″ and 5.0″.

## 1. Focus

- **One entry point.** The eye goes first to whatever is largest, most contrasting and most saturated. That must be the point of the slide: a number, the changed node, the conclusion.
- **Size difference ≥ 2–3×.** A 36 pt title next to a 40 pt number is two equal focal points and no main one. The number should be 72–120 pt.
- **The focus color is the accent.** Only the focus and what belongs to it (caption, marker frame) get the accent.
- **Focus on the lines of thirds**, not in the geometric center: the center is static, a third creates movement.
- **Squint test.** Squint or shrink the thumbnail to 10%: one blob should remain.

## 2. Hierarchy — three levels

| Level | What | How to distinguish |
|---|---|---|
| 1. Focus | number, diagram, key word | size ×2–3, accent, weight |
| 2. Support | conclusion title, data labels, 1–3 lines of explanation | ink, regular weight, 18–26 pt |
| 3. Utility | section label, footer, source, axes | muted, 12–13 pt, letter-spaced small caps |

There is no fourth level: if one appears, there is too much text or the slide must be split.

## 3. Scale

- **Hero number.** One number at 96–140 pt, caption 18–22 pt, context 13 pt. Other numbers go to the next slide or small in a row.
- **Hero diagram.** The diagram takes 60–75% of the area instead of "illustrating" text in a corner.
- **Scale contrast across a series.** On the wide shot details are small (texture); in the close-up one detail fills the slide (camera, section 7 of pptx-morph).
- **Giant element as background.** A section number at 300–400 pt with `fa` 0.06–0.1 behind the title, a piece of a diagram bleeding off the edge.

## 4. Asymmetry and tension

- **Splits:** 5+7, 4+8, 3+9 columns; 1/3 + 2/3 vertically. Equal 6+6 halves only for a "before/after" comparison, where equality is the point.
- **Weight and counterweight.** A heavy block on the left (diagram, dark plate) is balanced by a small but contrasting element on the right (number, accent). Not by two identical blocks.
- **Diagonal.** Focus in the top-left third, conclusion in the bottom-right. The diagonal leads the eye and suggests the Morph direction: whatever "leaves" leaves along the diagonal.
- **Tension at the edge.** An element almost touching the edge (0.3–0.5″) or bleeding off it creates movement. This needs `meta={"bleed": True}`, otherwise `lint` complains.

## 5. Empty space

- **30–45% of the area is empty.** The empty space sits next to the focus rather than being scattered as even gaps between blocks.
- **Margins ≥ 0.65″**, inner card padding ≥ 0.22″.
- **Group by proximity.** Spacing within a group is 2–3 times smaller than between groups. Then frames and rules are unnecessary.
- An empty "breather" slide (one phrase or number) is part of the presentation's rhythm, not an unfinished slide.

## 6. Header systems (to avoid monotony)

| System | What it looks like | When |
|---|---|---|
| A. Label + title at top left | 12 pt small-caps label, 26–36 pt title | documents: table, code, file tree |
| B. Title inside the composition | the title is a caption to the diagram or a conclusion under the number, placed by the focus | diagrams, numbers, charts |
| C. Side column | label and title in columns 9–12 (or 1–4), the scene at full height | wheel, pipeline, isometry, map |
| D. Section number as texture | section number 300+ pt, `fa` 0.08, title on top of or next to it | section slides, start of an act |
| E. No header | the scene only; context comes from persistent anchors (section color, progress, footer) | statement, hero number, full-screen diagram, finale |
| F. Breadcrumbs | path "Project A › P3 › splitting" at 12 pt bottom left | navigation, start of a section |

Alternation rules:
1. One system for **no more than 3 slides in a row**. Exception: a series of Morph steps within one scene, where the header stays put and serves as an anchor.
2. **Course context** ("Project A · practical 3") goes on the title slide, the section slide and in the footer. It is not repeated as a label above every title.
3. **The section label moves together with the header system.** The `!!sec` Morph pair travels from the corner to the side column — that is continuous motion, not repetition.
4. **Conclusion title.** "The network beats Ridge by 0.035 points", not "Model comparison". The topic goes in the label, the conclusion in the title.
5. Breather slides have no header at all.

## 7. The grid and breaking it

- Everything aligns to the columns and to **shared lines**: the left edge of the text matches the left edge of the diagram, the top of the number matches the top of the neighboring card.
- **One break per slide**, and a deliberate one:
  - a diagram bleeding off the edge;
  - a giant number;
  - a diagonal ribbon;
  - a full-slide photo;
  - a circle cropped by the edge.
- The break is backed by repetition: if a circle is cropped on the right on one slide, it "lives" in the same place on the section's slides (Morph changes its size — a motif).

## 8. Reading paths

- **Z-path** (top left → right → diagonally down → right): for "title → visual → conclusion" slides.
- **F-path** (rows from the left): tables and lists; the most important things go at the start of rows.
- **Circular path:** wheel, cycle, orbit. Focus in the center or at 12 o'clock, text on the right.
- **Order of appearance = reading order.** `anim_*` and `Fx` run in the same order the eye should read.

## 9. Editorial techniques (what makes a slide look "designed")

1. **Large type as an image:** one word at 120–200 pt, cropped by the edge or the frame.
2. **Hanging captions:** a small caption beside the number, aligned to its top rather than placed under it.
3. **Footers and numbers as a system:** "03 / 18" in mono 12 pt, the section number always in the same corner.
4. **Thin rules** (0.75–1 pt, `line`) instead of frames: they divide without boxing in.
5. **Color fields:** half the slide filled with `surface2` or the accent, text on it in `on_accent`. Changing the field between sections is a Morph transition of the `!!panel` backing shape.
6. **Motif repetition with variation:** a spectrum, ring or petal runs through the whole presentation at different scales.
7. **Labels right at the data** instead of a legend. A legend only with ≥ 5 series.
8. **Bento card grid:** cards of different sizes on a shared grid (2×2 + 1 wide), the main one larger.
9. **Negative space as a shape:** text flows around a large empty shape or sits in its "window".
10. **Density contrast on one slide:** a dense table in small type + one huge conclusion number beside it.

_Russian original: composition.ru.md_
