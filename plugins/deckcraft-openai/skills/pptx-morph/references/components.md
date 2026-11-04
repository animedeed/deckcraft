# Components `morphkit.components.Kit`

`k = Kit(theme)`. Every method returns `list[O]` (except `link`, `flow`, `terminal`, `fit`). Names are built from `id` with the `!!` prefix: the same `id` on neighboring slides gives a Morph pair. Colors are theme roles.

| Method | What it does | Notes |
|---|---|---|
| `fit(lines, w, sz, font, bold)` | the largest font size ≤ sz at which the lines fit | substitute-font metrics, 6% step |
| `label(text, id="sec")` | section label in small caps | persistent anchor `!!sec` |
| `title(text, id="ttl", size="h1", w=…)` | title, auto-fitted font size | `\n` — explicit lines |
| `text(id, x, y, w, txt, size, color, bullets)` | paragraphs/bullets | height is computed automatically |
| `folio(n, total)` | folio “03 / 18” | monospace, `!!folio` |
| `rail(steps, active)` | step pills, the active one expanded | technique 8 |
| `progress(n, active)` | progress dots | `!!s0…` |
| `card(id, x, y, w, h, title, body, kicker)` | card | parts `!!id`, `_k`, `_t`, `_b` |
| `stat(id, x, y, w, value, label)` | big number + caption | `_v`, `_l` |
| `callout(id, x, y, w, kicker, text, tone)` | warning / common mistake | tinted backing, no colored edge |
| `node(id, x, y, w, h, label, sub)` | diagram node | `sub` is monospace (file paths) |
| `link(id, a, b)` → `(objs, path)` | edge-to-edge arrow + path for a flow | the path goes center to center |
| `flow(path, n, period)` → `Loop` | flow loop | dots under the nodes (`z=5`) |
| `code(id, x, y, w, code, title, highlight)` | code panel with Python highlighting | runs prebuilt: `{}` are safe |
| `terminal(id, x, y, w, lines)` → `(objs, cursor)` | terminal, `$ ` is the prompt | cursor for `Loop("blink")` |
| `tree(id, x, y, entries)` | file tree `(depth, name, comment, highlight)` | |
| `table(id, x, y, widths, rows, highlight)` | table made of texts and rules | the first row is the header |
| `bars(id, x, y, w, h, values, labels, zero)` | horizontal bars | `zero=True` — zero state |
| `columns(id, x, y, w, h, values, labels, zero)` | vertical columns | shared baseline |
| `bg_grid(step)` | graph-paper grid (texture) | no Morph pairs |

The low-level object is `O(name, kind, x, y, w, h, …)`: `kind` ∈ rect, rrect, oval, text, line, arrow, arc, chevron, tri, pent, hex, donut, img. Fields: `fill, fa, ln, lw, la, dash, head, txt, sz, col, b, font, al, va, spacing, para_gap, bullets, caps, tracking, rot, radius, adj, img, crop, world, z, meta`. Useful `meta` keys: `inset` (text margins), `runs` (prebuilt runs), `bleed` (intentional bleed beyond the edge), `texture` (small texture text), `decor` (skip the contrast check), `parallax`, `allow_bar`.

_Russian original: components.ru.md_
