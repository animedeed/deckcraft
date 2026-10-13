---
name: deck-remix
description: "Improves an existing .pptx without rebuilding it your own way: inventory, a list of edits with reasons, edits via morphkit.existing.Deck (transition speed, text re-flow, signals along lines, staggered entrances, graph edges without crossings), checks and before/after motion sketches. / Доработка существующей .pptx пользователя без пересборки «по-своему»: инвентарь (фигуры, пары Morph, переходы, эффекты), список правок с причинами, правки инструментами morphkit.existing.Deck (скорость переходов, разрыв пар изменённого текста, петли сигнала по линиям, ступенчатое появление, перестройка связей без пересечений, удаление служебных слайдов), проверка и эскиз движения до/после."
argument-hint: "[.pptx] [what to change / что поменять]"
---

# /deck-remix — правка существующей презентации

Правило профиля 8: **удачное у пользователя не заменять своим.** Меняй только то, что просили или что ломается.
Справка по инструментам — `../pptx-morph/SKILL.md` §14; движок — `../pptx-morph/scripts`.

## 1. Инвентарь
```
from morphkit.existing import Deck
d = Deck(path)
print("\n".join(d.report()))                 # слайды, переходы, пары !!, эффекты
for i in range(1, len(d.slides)+1): d.shapes(i), d.transition(i)
```
Сделай рендер оригинала (`qa.render` → `contact_sheet`) и эскиз движения
`motion.preview(d.to_slides(), theme, out/"before")` — чтобы видеть, что уже работает.

## 2. План правок
Таблица: № слайда · что не так (замер) · правка · инструмент. Типовые:
- переходы медленные → `d.speed(max_morph_ms=900, max_fade_ms=600)`;
- изменённый текст переливается буквами → `d.text_policy()`, `d.fix_char_modes()`;
- служебные автослайды → `d.inline_service_slides()`;
- появление списком → `d.stagger(i, names, ...)`; сдвиг шкалы → `d.retime()`, `d.shift()`;
- граф «криво по связям» → `plan_edges_clean(...)` + `d.rewire(...)`; нулевые линии → `d.hide_zero_lines()`;
- процесс без жизни → петли `d.flow_on(i, connectors)` (сигнал по линиям), `d.ripple(i, target)`;
- новые объекты → `d.add(i, [O(...)])`, перестановка → `d.move`, `d.regroup`, `d.stack_under`.
Покажи план, если правок больше пяти или они меняют вид слайдов; мелкие технические — делай сразу.

## 3. Сохранить и проверить
`d.save(out)` (новый файл, оригинал не трогать) → `xsd_check`, `lo_effects_check`, рендер, лист миниатюр,
`motion.preview(Deck(out).to_slides(), ...)` для изменённых переходов. Сравни «до/после» по миниатюрам.
Ответ: файл, список правок по слайдам, что проверить в PowerPoint.
