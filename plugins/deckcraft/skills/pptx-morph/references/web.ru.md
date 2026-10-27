# Web-презентации (deckcraft 0.3.0): один генератор — HTML и .pptx

Те же `Slide` и `O`, что для PowerPoint, собираются в **один HTML-файл без зависимостей**: настоящий Morph по именам
`!!…` (контуры с разным числом точек выравниваются), эффекты, живые сцены, листы-переходы, элементы рисования,
кликабельные объекты и интерфейс показа. `.pptx`-двойник собирается из тех же слайдов (`for_pptx`).

```python
from morphkit.html import web, link, alt, for_pptx, export_html
from morphkit import draw as d

s = Slide(objs, ...)
web(s, sec=2, sheet={"k": "iris", "dur": 800}, steps=[["!!a"], ["!!b"]],
    fx=[{"key": "in.stamp", "target": "!!a", "delay": .2, "dur": .45}],
    scenes=[{"k": "liquid", "glass": "!!q0"}], autoState=[{"at": 2.0, "set": {"lr": "1"}, "reset": {"lr": "0.001"}}])
link(o, slide=12, tip="подробнее")                     # кнопка: slide | section | back | href | set | toggle | step
alt(o, "split", "rows", {"groups": o.copy(x=5.0)})     # состояние объекта: по кнопке плавно переезжает (пружина)
o.meta["when"] = {"key": "part", "is": "val", "dflt": "train"}   # виден только при этом значении
export_html(slides, theme, "out/deck.html", title="…", sections=[...], ui={"menu": "top", "hud": True},
            jumpSheet={"k": "zoomThrough", "dur": 700})
build_pptx(for_pptx(slides), theme, "out/deck.pptx")   # интерактив свёрнут в состояние по умолчанию
```

Язык интерфейса показа (подсказки, обзор, справка, окно докладчика), графы рамки ГОСТ и формат чисел в элементах
рисования — по `lang` (по умолчанию текущий язык `morphkit.i18n`). Готовый пример — `examples/demo_web.py OUT --lang
ru|en --shots`: демо-презентация с меню-кнопками, своим входом заголовка у каждого раздела, слайдом кнопок-состояний
и слайдом пометок от руки.

Проверка: `morphkit.webdemo.shots(path, out, times=[.6, 3.0], slides=None)` → `{"errors", "files", "sheet"}` — снимки
Playwright и ошибки консоли (должно быть 0); `morphkit.variety.report(slides)` — однообразие в числах (доля «стоячих»
переходов, глаголы движения на слайд, длина серии похожих раскладок).

## Правила (из показов)

* **Morph — основной переход.** Лист (`sheet`) — на границах разделов и для прыжков по ссылкам (`jumpSheet`); прыжок
  между слайдами с ≥ 5 общими парами идёт Morph.
* **Текст не переливается** по умолчанию: пара `!!…` с изменённым текстом рвётся (старый уходит, новый приходит). Для
  чисел и коротких надписей — `meta["morph_text"] = True` или `export_html(..., text_policy="morph")`: числа считают,
  общие буквы съезжаются.
* **Каждому разделу — свой язык движения**: вход заголовка, глаголы Morph, сцены; переход, где ничего не сдвинулось
  (`variety`: energy < 0,02), — сигнал переделать слайд.
* **Числа кликабельны**: метрика — ссылка на слайд-доказательство с кнопкой «← вернуться» (Backspace).
* **Без движения** (`prefers-reduced-motion`): эффекты сразу в финале, сцены — финальный кадр, петли выключены.

## Эффекты (`web(..., fx=[...])`, модуль fx.js)

Ключ с префиксом категории; у любого эффекта `options.ease`, у случайных — `options.seed`; длительность приходит в
`opt._dur`. Пресеты PowerPoint (`entrance_fade` …) тоже работают.

* **Входы (38):** `in.fade`, `in.rise`, `in.zoom`, `in.zoom-out`, `in.pop`, `in.drop`, `in.bounce`, `in.elastic`,
  `in.back`, `in.flip`, `in.unfold`, `in.spin`, `in.swing`, `in.blur`, `in.ink`, `in.glitch`, `in.iris`,
  `in.slide-l/r/u/d`, `in.reveal-l/r/u/d` (шторка с мягким краем), `in.stamp` (печать рывками), `in.registration`
  (сдвиг краски), `in.write` (пишется по строкам), `in.type` (печать с курсором), `in.scramble` (расшифровка),
  `in.count` (число растёт, формат сохраняется), `in.highlight` (маркер-подложка), побуквенно — `in.letters`,
  `in.wave-letters`, `in.split-letters`, `in.words`, `in.rain-letters`, `in.pop-letters`.
* **Выделения (20):** `em.pulse`, `em.shake`, `em.wobble`, `em.jello`, `em.heartbeat`, `em.glow`, `em.flash`,
  `em.tada`, `em.float` (с `repeat`), `em.color` (держит), `em.swing`, `em.rubber`, `em.dim` (держит), `em.wave`,
  `em.grow` (держит), `em.spin`, `em.reg`, `em.glitch`, `em.mark` (маркер, держит), `em.jump`.
* **Выходы (23):** `out.fade`, `out.zoom`, `out.drop`, `out.slide-l/r/u/d`, `out.blur`, `out.shrink`, `out.burn`,
  `out.flip`, `out.fold`, `out.spin`, `out.erase-l/r/u/d`, `out.type`, `out.glitch`, `out.ink`, `out.words`,
  `out.letters`, `out.scatter-letters`.
* **Рисование** (`in.draw*`, `em.draw*`) — у элементов рисования, см. ниже; `in.draw` у линий и путей — рисование
  обводки.

## Элементы рисования (`morphkit.draw`, модуль draw.js)

Каждая функция возвращает список `O`: первый — элемент (в HTML — SVG, рисуется по длине штрихов, параметры
переливаются при Morph), остальные — запасные части для .pptx. Общие параметры: `style` (`blueprint` — для тёмного
фона, `ink` — тушь с дрожанием, `marker`, `riso` — надпечатка второй краской, `chalk`), `color` (роль, hex или
`"роль/30"`), `lw`, `seed`, `z`.

`line`, `arrow` (дуга `bend`, «от руки» `hand`, ломаная `via`, `double`), `dim_h` / `dim_v` (размеры), `balloon`,
`leader`, `brace` (фигурная / квадратная, с подписью), `hatch` (штриховка, клетка, сетка, растр), `highlight`,
`scribble`, `encircle` (обвести от руки), `mark` / `check` / `cross` / `asterisk`, `stamp` (круглая печать / штамп),
`sticker`, `tape`, `gost` (рамка и основная надпись), `ruler`, `gauge`, `clock`, `write` (рукопись), `block`
(блок-схема: process, terminator, data, decision, document, predef).

Эффекты: `in.draw`, `in.draw-linear` (рукопись), `in.draw-stamp`, `in.draw-drop` (стикер), `in.draw-reg`, `in.draw-pop`;
`em.draw-redraw`, `em.draw-boil` (с `repeat`), `em.draw-to {value}` (стрелка прибора / размер к значению),
`em.draw-run {minutes}` (часы идут), `em.draw-needle`.

Пример — пометка «по распечатке» поверх блока кода: `d.encircle(…)` вокруг значения, `d.arrow(..., hand=True)` и
`d.write(…)` с подписью; эффекты `in.draw` → `in.draw-linear` по очереди.

## Листы-переходы (`sheet` / `jumpSheet`, модуль sheets.js)

`sheetIn`, `sheetUp`, `sheetDown`, `push` (`dir`, `parallax`), `cover`, `uncover`, `fold` (3D), `flip`, `cube`, `iris`
и `diamond` (из точки клика), `blinds`, `curtain`, `ink` (пятно с брызгами), `zoomThrough`, `dissolve`, `glitch`,
`pageCurl`, `shutter`, `fade`. Назад — обратный ход. Параметры — в объекте `sheet`: `{"k": "iris", "dur": 800, ...}`.

## Интерфейс показа (модуль ui.js, `ui={...}` в `export_html`)

`menu`: `top` (строка разделов с переезжающей подсветкой) | `tabs` (вкладки справа) | `stamp` (штамп ГОСТ) | `none`
(своё меню на слайдах); `hud` — панель в углу (появляется при движении мыши). Клавиши: ← → / PgUp PgDn / пробел —
листать (шаги — по кликам), O или Esc — обзор, P — окно докладчика (заметки, таймер, следующий слайд, синхронизация),
D — перо (E ластик, Z отмена, C очистить), L — указка, N — заметки, цифры + Enter — к слайду, Backspace — назад по
ссылке, F — полный экран, B — чёрный экран, ? — справка; печать / PDF — страница на слайд. Работает в русской
раскладке, ссылки доступны с Tab.

## Живые сцены (`web(..., scenes=[...])`, модуль scenes.js)

Сцены рисуют поверх слайда (`layer: "over" | "under"`) и меняют объекты на каждом кадре (уровень вина, контур,
цвет); Morph ухода начинается с последнего кадра сцены. Python: `from morphkit import scenes as SC` — конструкторы с
проверкой параметров (дюймы, pt, секунды; цвета — роли темы). Общие параметры: `character` (calm | lively | dramatic —
скорость, амплитуда, плотность, перелёт), `delay`, `step` (по клику), `seed`, `layer`.

* `liquid(glass, level_from, level_to, …)` — вино в бокале из `Glass`: волна гаснет после перехода и налива, рябь,
  пузырьки, пена, блик; поверхность горизонтальна и у наклонённого бокала.
* `pour(src, dst, …)` / `pour_into(glass, from_obj, level_from, level_to)` — струя с ускорением, каплями, брызгами и
  кругами; из горлышка бутылки или наклонённого бокала, с наливом.
* `bubbles`, `drip`, `stain` (пятно растекается и подсыхает кольцом), `ripple`.
* `particles(n ≤ 6000, layouts, shares, colors, labels, …)` — раскладки cloud, clusters, grid, groups, bars, into (в
  бокалы: частицы ссыпаются внутрь и растворяются в вине); фазы — `SC.phase(kind, at, dur, stagger)`.
* `signal(layers, edges="auto", …)` — импульсы по рёбрам графа слой за слоем, вспышки узлов, у выхода — столбики и
  число.
* `counter`, `clock` (стрелка и журнал событий по часам), `gauge` (стрелка с пружиной, зоны, полоса интервала, ноль),
  `terminal` (команды печатаются, вывод строками, курсор, прокрутка).
* `sparks`, `confetti`, `grain` (бумага / плёнка), `halftone` (растр), `chart_draw` (линия графика рисуется с
  метками), `bars_grow` (столбики растут, подписи едут с вершиной).

Сцены видны и во время перехода (стартовый кадр), без движения — сразу финальный кадр (после своего `step`).

## Модули и контракт

Ядро `web/core.js` + `base.css`, модули `draw.js`, `fx.js`, `scenes.js`, `sheets.js`, `ui.js` (+ `ui.css`); контракт
для авторов модулей — `scripts/morphkit/web/CONTRACT.ru.md`. Демо и проверки: `python3 -m morphkit.demo_fx OUT --all`,
`demo_draw OUT`, `demo_scenes OUT`, `demo_ui OUT` (из папки `scripts`).
