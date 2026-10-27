# Контракт модулей web-движка deckcraft 0.3.0

Ядро — `core.js` (+ `base.css`), сборка — `../html.py`, проверка — `../webdemo.py`. Модули — отдельные файлы в этой
папке; `html.py` склеивает их в один HTML в порядке: `core.js`, `draw.js`, `fx.js`, `scenes.js`, `sheets.js`, `ui.js`,
затем остальные `*.js`; CSS — `base.css`, затем остальные `*.css` по алфавиту. Модуль только **регистрирует** функции в
глобальном `window.DC`; запуск — `DC.start()` в конце страницы (после всех модулей).

**Правила для авторов модулей**

* Свой файл — только свой: `draw.js`/`draw.py`, `fx.js`, `scenes.js`/`scenes.py`, `sheets.js`/`ui.js`/`ui.css`.
  `core.js`, `base.css`, `html.py`, `webdemo.py` не правим — нужное изменение ядра описываем в отчёте («НУЖНО ОТ ЯДРА»).
* Без внешних библиотек и сети; всё детерминировано (`DC.u.rng(seed)`), цвета — из `DC.data.colors` (роли темы: bg,
  surface, surface2, line, ink, ink2, muted, accent, on_accent, accent2, accent3, good, warn, bad, code_bg, code_ink …), шрифты — `DC.data.fonts.head/body/mono`.
* Производительность: на кадре не создаём DOM заново — кэшируем узлы в `node`/`inst`; цель 60 к/с на 300 объектах.
* `DC.REDUCED` (prefers-reduced-motion): эффекты сразу в финальном состоянии, сцены рисуют финальный кадр, без петель.
* Кириллица везде; подписи интерфейса — на языке презентации (`DC.data.lang` ru|en; ui.js — `DC.ui.tr`).

## Координаты и время

Сцена 1600×900 px; **1 дюйм = 120 px** (слайд 13,333×7,5 дюйма). У объекта `o` поля в **px**: `x, y, w, h` (рамка),
`r` (поворот, градусы, вокруг центра рамки), `z`. В состоянии эффекта `st` смещения `dx, dy` и `clip` — в **дюймах**
(как в Python-превью `morphkit.motion`), `tx, ty` — в px. Время эффекта — секунды после конца перехода к слайду
(минус `DC.data.fxStart` = 0,15 с); шаги (`steps`) сдвигают начало своих эффектов на момент клика.

## Объект (JSON из Python)

`{n, k: "path"|"line"|"img"|"text", x, y, w, h, r, z, f (заливка #hex|null), fa, s (обводка), sw (px), la, dash,
head, rings (нормированные контуры [[x0,y0,x1,y1,…], …] в долях рамки), grad {a, kind, stops [[pos, #hex, alpha]]},
t {lines [[[text, color, bold, mono], …], …], sz (pt), col, b, font, mono, al l|c|r, va t|m|b, sp, pg, tr, inset, lh},
img, link, tip, ease, lag, draw, when, web}`

* `link` — объект-кнопка: `{slide: i}` | `{section: k}` | `{back: true}` | `{href}` | `{set: {key: value}}` |
  `{toggle: key, values: [...]}` | `{step: true}`. Ядро вешает клик и класс `.dc-link`, переходы по ссылке кладут
  текущий слайд в `DC.backStack` (Backspace / `DC.back()` возвращают).
* `tip` — подсказка: ядро шлёт `DC.emit('tip', o, event, on)` при наведении (UI рисует её; запасной вариант — `<title>`).
* `when` — `{key, is, dflt}`: объект виден, только когда `DC.state[key] == is` (плавно 0,35 с) — переключатели A/B.
* `alt` — `{key, dflt, values: {значение: {x, y, w, h, r, f, fa, s, sw, la, rp}}, dur, ease}`: состояния объекта —
  при `DC.setState(key, v)` (кнопки `link set/toggle`) объект плавно переходит к варианту (пружина 0,65 с). Python:
  `morphkit.html.alt(o, key, dflt, {значение: вариант O})`.
* `ease` — кривая Morph этого объекта (`DC.ease`: linear, inOut, out, in, back, elastic, spring, bounce + свои).
* `lag` — задержка Morph объекта, с (каскады); у слайда есть `cascade: {by: "x"|"y"|"radial"|"-x", amount}`.
* `draw` — спецификация элемента рисования: `{kind, ...}`; если `DC.draw[kind]` зарегистрирован, объект рисует модуль
  draw (ядро не строит `path`).

## Слайд (JSON)

`{title, notes, dur (мс Morph), tr ("morph"|"none"|нативный ключ PowerPoint), bg, objs, fx {name: [[key, start, dur,
opt, step, cat], …]}, loops [...], scenes [...], steps [[имена], …], sec (номер раздела), sheet, jumpSheet, cascade,
label, nav, autoState [{at, set, reset}]}`; колода: `{slides, pool, imgs, colors, fonts, sections [{title, start}], title, jumpSheet, …}`.

Переход к соседнему слайду: `tr == "morph"` и нет `sheet` → Morph по именам `!!…` (при разном числе точек контуры
выравниваются по длине и сдвигу); иначе лист `sheet` (по умолчанию `fade`). Прыжок по ссылке/меню на далёкий слайд:
если у слайдов ≥ 5 общих пар — тоже Morph, иначе `jumpSheet` (или `DC.data.jumpSheet`, или `fade`).

## Реестры

### `DC.fx[key] = (o, e, p, opt, sl) => st` — эффекты

* `key` — имя с префиксом категории: `in.*` (вход), `em.*` (выделение), `out.*` (выход), `path.*`. Ключи пресетов
  PowerPoint (`entrance_fade` …) обрабатывает ядро; модуль может их переопределить, зарегистрировав тот же ключ.
* `p` — линейный прогресс 0..1, `e` — после кривой (`opt.ease` или inOut), `opt` — параметры из Python, `sl` — слайд.
* Возвращает **состояние** `st` (все поля необязательны):

| поле | смысл |
|---|---|
| `alpha` | прозрачность (умножается) |
| `scale`, `sx`, `sy` | масштаб вокруг центра рамки (умножается) |
| `dx`, `dy` (дюймы), `tx`, `ty` (px) | сдвиг (складывается) |
| `drot` | доп. поворот, градусы (складывается) |
| `skewX` | наклон, градусы |
| `clip` | `[x0, y0, x1, y1]` дюймы — видимый прямоугольник |
| `blur`, `bright`, `sat`, `hue` | CSS-фильтры (px, множители, градусы) |
| `glow` (+`glowR`), `shadow` | свечение цветом / тень `"dx dy r color"` |
| `drawP` | 0..1 — «рисование» обводки пути/линии |
| `chars` | показать первые N символов текста (печать) |
| `col` | цвет текста |
| `fill`, `outline` | заливка / обводка поверх исходной |
| `dz` | сдвиг слоя |
| `t` | замена текстовой спецификации объекта (`{...o.t, lines: …}`) — счётчики, подстановки |
| `textFx` | `{k, ...}` — отрисовать текст своим рендером `DC.textFx[k](node, o, st, surface)` (побуквенные эффекты); рендер работает в `node.tg` и ставит `node.tfx = true` |

* Вход до начала скрывает объект, выход после конца — тоже; `h.hold = true` — удерживать финальное состояние
  эффекта после окончания (для выделений «перекрасить и оставить»).
* Перелив текста: `DC.textMorph = (a, b, t, o) => [[obj, alpha, st?], …]` — вызывается ядром для пар `!!…` с разным
  текстом (и у фигур с подписью: контур переливается без текста, подпись приходит сюда как текстовый объект). Элементы
  рисуются с ключами `имя`, `имя#1`, `имя#2`…; `st` (необязательно) — состояние элемента (`textFx`, `dx` …), его `alpha`
  умножается. Пары с изменённым текстом доходят до web, только если `export_html(..., text_policy="morph")` или у
  объекта `meta["morph_text"] = True` (по умолчанию — правило профиля «текст не переливается»: пара рвётся).
* В `opt` эффекта ядро кладёт `_dur` — длительность, с (ритм курсора, перебора символов в секундах).
* `DC.REDUCED`: ядро само отдаёт входам и выделениям финальное состояние (p = 1), выходы — до конца видны.

### `DC.loops[kind] = (lp, byName, tt, sl, index) => items` — петли до конца слайда

`items` — `{key, o, st}` (новые объекты) или `{replace: имя, st}` (состояние поверх объекта слайда). Встроены flow,
pulse, ripple, spin, blink.

### `DC.scenes[kind] = { mount(ctx, params) => inst }` — живые сцены

`inst = { frame(t, ctx), unmount() }`; `t` — секунды после перехода (как у эффектов). `ctx`:
`layer` (свой `<g>` в слое `params.layer` = "over" | "under"), `canvas()` → 2D-контекст во весь слайд (foreignObject;
в снимке для листа-перехода ядро растрирует его в `<image>`), `obj(name)` → объект слайда (для объектов с `alt` —
текущий вариант), `mod(name, fn)` — модификатор объекта на каждом кадре: `fn(o, st, t) => [o2, st2]` (можно менять
копию объекта: контур, уровень, цвет; вернуть null — скрыть); модификаторы всех сцен на одно имя ядро применяет
цепочкой (одна и та же функция — один раз). `T` — цвета, `reduced`, `u` — утилиты, `sl` — слайд. `frame(t)`
вызывается и во время перехода с t < 0 (стартовый кадр), модификаторы — тоже (цель Morph); Morph ухода начинается с
последнего кадра слайда после модификаторов и состояний (`sl.last`), скрытые на уходе объекты не всплывают. Параметры сцены приходят из Python: `web(slide, scenes=[{"k": "pour", ...}])`.

### `DC.sheets[kind] = (p, A, B, ctx) => void` — листы-переходы

`A` — `<svg>`-снимок предыдущего кадра (поверх), `B` — живой `<svg>` нового слайда (под ним; его эффекты входа ждут
конца листа). Модуль меняет `style` у A и B (transform, clip-path, opacity, filter, 3D — у `#dc-stage` есть
perspective). `p` — прогресс после кривой, `ctx = {dur, opt, stage, from, to, u, raw}`. После листа ядро удаляет A и
сбрасывает `B.style`.

### `DC.draw[kind] = (node, o, st, surface) => void` — элементы рисования

`node.dg` — пустая `<g>` (создаётся ядром при смене вида); модуль сам кэширует свои элементы в `node`. Учитывать
`st.drawP` (рисование), `o.draw` (параметры), рамку `o.x/y/w/h` (px), поворот делает ядро. `DC.draw._interp(a, b, t)` —
необязательно: перелив параметров двух спецификаций одного вида при Morph.

### События и навигация

`DC.on(ev, fn)`: `ready`, `slide (i, from, opts)`, `step (i, n)`, `frame (t, sl)`, `link (link, o)`, `tip (o, e, on)`,
`state (state)`, `trans (kind, on, trans)` — начало (`on = true`) и конец перехода (Morph или лист). У каждого узла
поверхности `node.wrap.dcObj` — объект, который он рисует (подсветка ссылок, подписи для экранного диктора). `DC.t0` —
геттер момента входа на слайд (performance.now). Клавиши ядра не срабатывают при Ctrl/Alt/Meta и в полях ввода, а
Enter/Space — на кнопке в фокусе. Системный `<title>` у объектов с `tip` ядро ставит, только если нет модуля `DC.ui`.
Текст рисуется с сохранением пробелов (`white-space: pre`) — колонки в моноширинном коде совпадают с .pptx. API: `DC.go(i, {push, instant})`, `DC.next()`, `DC.prev()`, `DC.back()`, `DC.cur`, `DC.backStack`,
`DC.renderStatic(i)` → `<svg>` финального кадра (обзор, печать, миниатюры), `DC.snapshot()`, `DC.keys[key] = fn`
(клавиши; ядро занимает стрелки, PgUp/PgDn, Space, Enter, Home/End, Backspace), `DC.clickAdvance` (false — клик по
сцене не листает), `#dc-overlay` — слой HTML поверх сцены для интерфейса.

## Python

```python
from morphkit.html import web, link, export_html
from morphkit.webdemo import build, shots

s = Slide(objs, ...)
web(s, sec=2, sheet={"k": "sheetIn", "dur": 800}, steps=[["!!a", "!!b"], ["!!c"]],
    fx=[{"key": "in.stamp", "target": "!!a", "delay": .2, "dur": .45, "options": {...}}],
    scenes=[{"k": "pour", "from": "!!q0", "layer": "over"}], cascade={"by": "x", "amount": .3})
link(o, slide=12, tip="подробнее")
path = build([s1, s2], "demo.html", sections=["Раздел 1", "Раздел 2"])
r = shots(path, "out/", times=[.4, 1.2, 3.0]); assert not r["errors"]
```

Эффекты web не попадают в .pptx; объекты `draw` в .pptx — их запасная форма (лента-`vec`), в HTML — настоящий SVG.
