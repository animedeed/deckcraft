# Choosing the form: what to show and with what

First the **data's job** (what the viewer must see), then the form, and only then the color. Charts are built from shapes so that they morph. Color and palette checks — per the `dataviz` skill, if it is available.

| Data's job | Form | What to avoid | Morph technique |
|---|---|---|---|
| One main number | hero number with a hanging caption and context | 4 numbers of the same size | entrance via an effect; a correction — strikethrough and a new value |
| Share of a whole (1 number) | progress ring, bar, 10×10 “waffle” | pie chart with 6 sectors | ring with a circular fill, dot field |
| Shares across groups | dot field by group, sectors with one pulled out | 3D pie, a 6-color legend | field → groups, pie piece by piece |
| Comparing 2–3 values | bars with labels at the ends, “before / after”; magnitude in objects (document sheets 3.3 vs 1.1) | dual axis | growth within the slide, split screen |
| Ranking | horizontal bars in descending order | alphabetical order | re-sorting |
| Distribution | dot histogram, interval whiskers | a mean without spread | field → histogram, intervals from zero |
| Relationship of two quantities | scatter plot, our point larger | trend line without points | scatter out from the origin |
| Change over time | line made of segments, event strip | 12 lines on one chart | drawing the polyline, strip + camera |
| Process / conveyor | nodes and links with flows | bulleted list of steps | marker, flow loop |
| Cycle / steps in a circle | pointer flower beyond the screen edge | “carousel” arrows from a picture | turning the flower to the topic, pinwheel |
| Hierarchy / layers | tree, isometric stack | nested frames | isometry, node expansion |
| Many-to-many links | graph, matrix | spaghetti without focus | network growth, spotlight |
| Composition / what it is made of | fragmentation, an “exploded” diagram | legend unconnected to the parts | scatter apart, assembly |
| Uncertainty | intervals, semi-transparent areas | a single figure without ± | intervals from zero |

## Honesty rules

- The bar axis starts at zero. A truncated axis — only on scatter plots, and it is labeled.
- Labels next to the data, units in the label (“MAE, points”).
- Color follows the entity (red wine is always `red_wine`), not the rank.
- Status colors (`good`, `warn`, `bad`) — only for statuses, with a label or a sign, never the sole carrier of meaning.
- Numbers are taken programmatically from result files, not typed in by hand.
- One dot = N observations — this is labeled.

_Russian original: infographics.ru.md_
