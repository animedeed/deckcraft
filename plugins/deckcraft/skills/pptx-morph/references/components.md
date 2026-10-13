# Компоненты `morphkit.components.Kit`

`k = Kit(theme)`. Каждый метод возвращает `list[O]` (кроме `link`, `flow`, `terminal`, `fit`). Имена строятся от `id` с префиксом `!!`: одинаковый `id` на соседних слайдах даёт пару Morph. Цвета — роли темы.

| Метод | Что делает | Важное |
|---|---|---|
| `fit(lines, w, sz, font, bold)` | наибольший кегль ≤ sz, при котором строки помещаются | метрики шрифта-заменителя, шаг 6% |
| `label(text, id="sec")` | метка раздела капителью | сквозной якорь `!!sec` |
| `title(text, id="ttl", size="h1", w=…)` | заголовок, автоподбор кегля | `\n` — явные строки |
| `text(id, x, y, w, txt, size, color, bullets)` | абзацы/пункты | высота считается сама |
| `folio(n, total)` | колонтитул «03 / 18» | моно, `!!folio` |
| `rail(steps, active)` | таблетки шагов, активная раскрыта | приём 8 |
| `progress(n, active)` | точки прогресса | `!!s0…` |
| `card(id, x, y, w, h, title, body, kicker)` | карточка | части `!!id`, `_k`, `_t`, `_b` |
| `stat(id, x, y, w, value, label)` | большое число + подпись | `_v`, `_l` |
| `callout(id, x, y, w, kicker, text, tone)` | предупреждение / типовая ошибка | тонированная подложка, без цветного края |
| `node(id, x, y, w, h, label, sub)` | узел схемы | `sub` моноширинный (пути файлов) |
| `link(id, a, b)` → `(objs, path)` | стрелка от края до края + путь для потока | путь от центра к центру |
| `flow(path, n, period)` → `Loop` | петля-поток | точки под узлами (`z=5`) |
| `code(id, x, y, w, code, title, highlight)` | панель кода с подсветкой Python | прогоны готовые: `{}` безопасны |
| `terminal(id, x, y, w, lines)` → `(objs, cursor)` | терминал, `$ ` — приглашение | курсор для `Loop("blink")` |
| `tree(id, x, y, entries)` | дерево файлов `(глубина, имя, пояснение, выделить)` | |
| `table(id, x, y, widths, rows, highlight)` | таблица из текстов и линеек | первая строка — шапка |
| `bars(id, x, y, w, h, values, labels, zero)` | горизонтальные столбики | `zero=True` — нулевое состояние |
| `columns(id, x, y, w, h, values, labels, zero)` | вертикальные столбики | общая база |
| `bg_grid(step)` | миллиметровка (фактура) | без пар Morph |

Низкоуровневый объект — `O(name, kind, x, y, w, h, …)`: `kind` ∈ rect, rrect, oval, text, line, arrow, arc, chevron, tri, pent, hex, donut, img. Поля: `fill, fa, ln, lw, la, dash, head, txt, sz, col, b, font, al, va, spacing, para_gap, bullets, caps, tracking, rot, radius, adj, img, crop, world, z, meta`. Полезные `meta`: `inset` (поля текста), `runs` (готовые прогоны), `bleed` (намеренный вылет за край), `texture` (мелкий текст-фактура), `decor` (не проверять контраст), `parallax`, `allow_bar`.
