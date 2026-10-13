# Библиотека движения: 198 анимаций фигур и 53 перехода

Источник анимаций — реестр `scripts/morphkit/data/pptx_animation_presets.json`. Это XML, снятый с файлов PowerPoint 16 (проект PPT Master, MIT, см. `data/NOTICE.md`). Всего 203 эффекта; 5 из них (`*_3d_*`) анимируют 3D-модели и на фигурах не играют. `keys()` их не возвращает, `lint` считает ошибкой.

Посмотреть всё глазами: `python scripts/gallery.py OUT_DIR --check` → `transitions_gallery.pptx` (53 слайда, по переходу на слайд) и `fx_gallery.pptx` (26 слайдов, восемь образцов на слайд, эффекты идут по очереди). Обе проходят XSD.

## API

```python
from morphkit import Fx, Slide, TRANSITIONS
from morphkit.presets import keys, describe

keys("entrance")              # 52 ключа; также "emphasis" (30), "path" (64), "exit" (52)
describe("entrance_fly")      # имя, класс, presetID, длительность по умолчанию, параметры и их значения

Slide(objs, transition="vortex", trans_opts={"dir": "l"}, dur=1600, fx=[
    Fx("entrance_spinner", "!!flower", dur=0.9),                       # первый Fx стартует в 0
    Fx("entrance_fade", "cap", start="after", delay=0.1),              # после окончания предыдущих
    Fx("emphasis_spin", "gear", dur=4, repeat=True, start="with"),     # вместе с предыдущим, до конца слайда
    Fx("emphasis_grow_shrink", "kpi", options={"size": 115}, rev=True, start="after"),
    Fx("emphasis_change_fill_color", "cell", options={"color": "accent"}, start="after"),
    Fx("path_circle", "orbit_dot", dur=6, repeat=True, path_size=(3, 3), start="at", delay=0.4),
    Fx("path_custom", "dot", path=[(2, 3), (6, 3), (6, 5)], dur=1.2, start="after"),
    Fx("exit_fly", "old", options={"direction": "left"}, start="after"),
])
```

- **Старт** — как в панели анимации PowerPoint. `with` — одновременно с предыдущим Fx, плюс `delay`. `after` — когда закончатся все предыдущие неповторяющиеся Fx, плюс `delay`. `at` — от начала шкалы слайда, плюс `delay`. Шкала стартует, когда закончился переход.
- **dur** масштабирует все узлы пресета пропорционально. Это касается и многоступенчатых эффектов: Spinner, Boomerang, Credits. **repeat** — «Повторение: до окончания слайда». **rev** — «Автовозврат».
- **options**:
  - `direction` — направление: up, left, in, out, horizontal_in…;
  - `amount` — угол вращения в градусах (`emphasis_spin`), непрозрачность 0–1 (`emphasis_transparency`) или число спиц (`entrance_wheel`: 1, 2, 3, 4, 8);
  - `size` — масштаб в % (`emphasis_grow_shrink`);
  - `color` — роль темы или hex (эффекты смены цвета);
  - `font_name` — шрифт.
- **Пути.**
  - Готовые пути заданы в долях слайда. Пресет `path_circle` на слайде 16:9 — это эллипс 3,3″ × 1,9″. Нужный габарит в дюймах задаёт `path_size=(w, h)`.
  - `path_custom` берёт ломаную в дюймах из `path`: объект смещается на (p − p0).
  - Можно передать и готовую строку пути `animMotion`, с кривыми `C`.
- Эффекты библиотеки, появление `anim_*` и петли `Loop` живут на одной шкале слайда и не мешают друг другу.

## Что брать для учебных и технических презентаций

| Задача | Эффект | Почему |
|---|---|---|
| спокойно ввести новый объект | `entrance_fade`, `entrance_wipe` (по направлению чтения), `entrance_faded_zoom` | без «цирка», не спорит с Morph |
| показать рост, заполнение | `entrance_wipe` direction=up для столбика, `entrance_stretch` | направление совпадает со смыслом |
| радиальная сборка (колесо, цветок, циферблат) | `entrance_spinner`, `entrance_wheel` (amount = число секторов), `entrance_pinwheel` | вращение подчёркивает «по кругу» |
| акцент на числе | `emphasis_grow_shrink` size 110–120 + rev, `emphasis_bold_flash` | короткий и возвратный |
| «здесь ошибка» | `emphasis_teeter`, `emphasis_change_fill_color` в роль bad | покачивание считывается как «не так» |
| процесс идёт | `emphasis_spin` repeat, `path_circle` repeat с `path_size` | фоновые петли (лучше через `Loop`) |
| убрать лишнее перед Morph | не нужен: Morph сам гасит объекты без пары | выход дублировал бы переход |
| объект уходит по сюжету внутри слайда | `exit_fade`, `exit_fly` по направлению движения | только если объекта нет на следующем слайде |

Экспрессивные эффекты (`bounce`, `boomerang`, `credits`, `light_speed`, `swish`, `sling`) — для титулов и шуточных вставок, не чаще одного на раздел. `random_effects` не использовать: результат непредсказуем.

## Стык анимаций с Morph (проверено записью показа и правилами PowerPoint)

1. **Шкала слайда стартует после перехода.** Задержки не должны включать длительность Morph: первый эффект — через 0–150 мс.
2. **Пара Morph берёт геометрию статичного слайда.** Итог анимаций не учитывается. Отсюда два правила, которые `lint` проверяет:
   - **вход** на объекте с парой на предыдущем слайде: во время перехода объект скрыт, потом появляется второй раз. Входы давай новым объектам;
   - **выход или путь** на объекте с парой на следующем слайде: в начале перехода объект прыгнет в статичное положение. Двигай такие объекты самим Morph (новое положение на следующем слайде), а не путём перемещения.
3. **Объекты с входом скрыты до своего старта, в том числе во время перехода.** Этим пользуется петля `flow`: точки получают эффект «Появление» (entr 1) в момент старта, поэтому не мелькают в очереди под узлом.
4. **Не перекрашивай пару через Morph между далёкими цветами.** Оранжевый → тёмно-синий проходит через грязно-коричневый. Нужна переезжающая рамка-маркер (`Kit.marker`) или смена цвета эффектом `emphasis_change_fill_color` после перехода.
5. **Больше 12 эффектов на слайде** — признак, что слайд надо разбить на шаги Morph. Шаги можно переключать автоматически: `Slide(auto=…)`.

## 53 перехода (`Slide(transition=…, trans_opts=…, dur=…)`)

| Группа | Ключи | XML |
|---|---|---|
| ISO, любые версии | fade push wipe split cover random blinds checkerboard comb cut dissolve random_bars shape uncover clock wheel box wedge plus diamond strips | `<p:…>`, длительность `p14:dur` — в ветке `mc:Choice Requires="p14"` |
| PowerPoint 2010+ (p14) | zoom reveal flash ripple honeycomb glitter vortex shred switch flip gallery cube doors pan ferris_wheel conveyor rotate window orbit fly_through | `mc:Choice Requires="p14"`, запасной `p:fade` |
| PowerPoint 2013+ (p15) | fall_over drape curtains wind prestige fracture crush peel_off page_curl airplane origami | `<p15:prstTrans prst="…"/>`, запасной `p:fade` |
| PowerPoint 2019/365 | morph | `<p159:morph option="byObject|byWord|byChar"/>` |

`trans_opts` переопределяет атрибуты: `{"dir": "l"}` (push, wipe, cover, vortex…), `{"orient": "vert"}` (split), `{"invX": "1"}` (зеркально у p15).

**Как выбирать переход.**
- Morph — основной: связывает соседние состояния.
- Нативный переход — **граница главы** или смена «мира»: cube/rotate — новый раздел, gallery/conveyor — лента примеров, curtains — финал, vortex/shred — «сломали» (ошибка, антипример).
- Разные нативные переходы подряд — это шум. На презентацию 1–3 вида, каждый со своим смыслом.

**LibreOffice** распознаёт ISO-переходы и часть p14/p15: ripple, honeycomb, glitter, vortex, cube, rotate, orbit, flash, fall_over. Остальные он не показывает, но PowerPoint их проигрывает. Поэтому импорт в ODP проверяет только ISO-группу. p14/p15 проверяй глазами в PowerPoint по `transitions_gallery.pptx`.

## Проверка

1. `xsd_check` — 0 ошибок. Ветка `mc:Choice` в схему ISO не входит и проверяется только разбором XML.
2. Импорт в LibreOffice: в `content.xml` у каждого эффекта есть `presentation:preset-id="ooo-entrance-…"`, `ooo-emphasis-…`, `ooo-exit-…` или `ooo-motionpath-…`. В галерее LibreOffice узнал все 198 эффектов фигур.
3. Движение и переходы p14/p15 — в PowerPoint (F5) или по записи показа пользователя.
