# Presentation design system

## 1. Brief — template

```
Audience:         who is watching, what they already know
Goal:             what the viewer should understand/decide after the show
Density mode:     speaker | reading
Visual thesis:    one phrase about the character of the design
Motif:            one recurring graphic element (not a stripe, not a frame)
Palette:          a theme from morphkit.theme or a custom one (roles below) + contrast report
Fonts:            headings / text / code (+ substitutes for checking)
Grid:             12 columns, margins, gutter
Motion language:  section -> Morph technique; where the loops are and why
Constraints:      what it is shown on (PowerPoint 365/2019+?), language, brand
```

The thesis drives the decisions. "Lab notebook" means white paper, sharp corners, thin rules, page-number footers, mono file labels and a single wine-red accent. "Dark cellar" means a deep background, soft rounding, glowing flows and progress arcs.

## 2. Palette by role

| Role | Purpose | Requirement |
|---|---|---|
| `bg` | slide background | dominant |
| `surface`, `surface2` | cards, nodes | close to the background, distinguishable from it |
| `line` | rules, connectors, grid | quiet |
| `ink` | main text, titles | ≥ 4.5:1 against bg and surface |
| `ink2` | secondary text | ≥ 4.5:1 against bg, surface, surface2 |
| `muted` | labels, footers | ≥ 4.5:1 against bg and surface (small type!) |
| `accent` | one sharp accent: active step, main number | ≥ 4.5:1 against bg and surface if used for small text |
| `on_accent` | text on an accent fill | ≥ 4.5:1 against accent |
| `accent2`, `accent3` | supporting | do not compete with accent |
| `good`, `warn`, `bad` | statuses | statuses only, with a label; not for "series 4" |
| `code_bg`, `code_ink`, `code_kw`, `code_str`, `code_num`, `code_com` | code and terminal panels | code_ink and code_com ≥ 4.5:1 against code_bg |
| `flow` | flow dots | visible against the background and connectors |
| subject colors (`red_wine`, `white_wine`) | the color is bound to an entity | one color — one entity across the whole presentation |

Principles:
- **Dominance:** 60–70% of the area is background and neutral surfaces, 1–2 supporting colors, one accent. An even rainbow looks timid.
- **From the subject:** if the palette could be moved to a presentation on a different topic and still "work", the choice is not specific enough.
- **Color follows the entity, not the order:** red wine is always `red_wine`, on every chart.
- **Check:** `theme.contrast_report()` before building; `lint()` checks every text against the background beneath it.
- For categorical charts, check distinguishability under color-vision deficiencies (the dataviz skill's validator, if available).

Ready-made directions in `morphkit/theme.py`: `LAB` (light editorial, burgundy + green + amber), `CELLAR` (dark, wine and gold), `BLUEPRINT` (blue blueprint, orange markup, turquoise flows). A custom theme is `Theme(name=…, colors={…})` with the same roles.

## 3. Typography with Cyrillic

PowerPoint renders with the font **the user** has installed, while the check here uses a substitute font. If the widths differ, the line-break check lies.

| In the .pptx | Substitute for checking | Width match | Cyrillic |
|---|---|---|---|
| Calibri | Carlito | exact | yes |
| Arial | Liberation Sans | exact | yes |
| Times New Roman | Liberation Serif | exact | yes |
| Courier New | Liberation Mono | exact | yes |
| Georgia, Cambria, Consolas, Segoe UI, Bahnschrift | DejaVu | approximate — 10% margin | yes |

Rules:
- Body text and anything where fit matters comes from the first group. Calibri is the best balance for Russian text on slides.
- Scale (pt): display 60 · h1 36 · h2 26 · lead 22 · body 18 · small 15 · caption 13 · code 14 · label 12. Minimum 12 (reading mode), 14 (speaker); body text ≥ 15 / 22.
- "Bigger means lighter": large titles in regular weight; bold for small labels (small caps + 1–1.5 pt letter spacing) and accent numbers.
- Line spacing 1.05–1.15 for text, 0.95 for two-line titles.
- Line breaks are explicit (`\n`), autofit is off. `Kit.title/text/card` pick the font size themselves (`Kit.fit`) if a line does not fit.
- Monospace only for code, paths, commands and footer numbers.
- No more than two families per presentation (plus mono).

## 4. Grid

12 columns on 13.333″: margins 0.65″, gutter 0.25″, column ≈ 0.774″. `Grid.x(col)` is the left edge of a column (1…12), `Grid.w(span)` is the width of span columns. Vertical: top margin 0.55″ (section label), title from 0.9–1.25″, bottom margin 0.5″ (footer). Typical splits: 12 · 6+6 · 5+7 · 4+4+4 · 3×4 · 8+4. Everything adjacent aligns to a shared line.

## 5. Density modes

| | speaker | reading |
|---|---|---|
| For | talk, pitch, live explanation | lectures for self-study, walkthroughs, handouts |
| On a slide | one idea, 1–3 points | structure + key numbers + short explanations, up to 6 points |
| Words per slide | ≤ 35 | ≤ 90 |
| Text size | ≥ 22 | ≥ 15 |
| Notes | talking points | detailed write-up (80–180 words) |

If it does not fit, split it into two slides instead of shrinking the font.

## 6. Anti-patterns

Forbidden (signs of generated slides):
- a line or stripe under the title; full-width colored bars at the top/bottom; a colored edge on a card;
- emoji instead of icons; an "icon in a circle" on every bullet;
- "purple on white" gradient backgrounds; shadows and glows without purpose;
- a slide made of one title and a list; the same layout three slides in a row;
- centering everything; text touching the edges;
- a beige/cream background "by default" (unless chosen deliberately);
- made-up figures, "decorative" metrics, lorem ipsum;
- service labels on the slide ("option A", "template").

Do:
- one motif, repeated with variations;
- expressive scale (one big number instead of five medium ones);
- empty space as part of the composition;
- charts and diagrams built from shapes so they morph;
- labels right at the data instead of legends, where possible.

_Russian original: design-system.ru.md_
