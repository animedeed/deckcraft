---
name: deck-build
description: "Сборка .pptx с Morph по brief.json и раскадровке из /deck-brief: генератор колоды на morphkit (мотив в ролях, навигация, язык движения раздела, петли процессов), затем полная проверка с замерами — lint, проверка движения (ничего не пролетает по тексту), XSD, распознавание эффектов, рендер и лист миниатюр, GIF ключевых переходов. Итог — .pptx, отчёт и список того, что посмотреть в PowerPoint."
argument-hint: "[путь к brief.json]"
---

# /deck-build — сборка по брифу

Нет брифа — сначала /deck-brief. Пути — от базы скилла; движок `../pptx-morph/scripts`.
Перед кодом прочитай `../pptx-morph/SKILL.md` (правила профиля, Morph, сборка §12, проверка §15) и
`../pptx-design/references/structure.md`.

## 1. Генератор
Пиши `out/decks/<slug>/build_deck.py` (не правь XML руками): `sys.path` → `../pptx-morph/scripts`.
- Тема: `next(p.theme for p in morphkit.palette.CATALOG if p.theme.name == brief["palette"]["key"])`.
- Профиль: `DeckProfile.load(out/decks/<slug>/deck_profile.json)`.
- Мотив: готовые помощники — `morphkit.motif` (Flower, Orbit, `MotifTrack.at(...)` с ролями hero / pointer /
  backdrop / data / progress) и семейства лаборатории (`lab/f_wine.py` Bunch, Glass; `lab/f_iso.py` платформа;
  `lab/f_energy.py`, `lab/f_docs.py`, `lab/f_neural.py`, … — превью у каждого пункта `morphkit.catalog.MOTIFS[*].preview`).
  Бери из них функции-формы, а не слайды целиком; имена — через свой префикс, чтобы не пересечься.
- Навигация: `recipes.agenda` (карта доклада → шапка), `recipes.menu_bar`, `recipes.block_counter` или мотив у края
  (`MotifTrack` pointer с делениями). Одна на колоду.
- Язык движения раздела → инструменты: dots — `process.Carrier`, `recipes.dots`; fragments — `ops.explode/gather`;
  circle — `recipes.magnify`, кольца; depth — `ops.tilt3d/recede`, камера; flow — `recipes.flow_along`, петли flow;
  growth — `components.Kit.bars`, `recipes.curve`; lens — `recipes.magnify`, `recipes.spotlight`; fold — `ops.fold/peel`.
- Каждый слайд: `layout=`, `technique=`, `title=`, заметки-конспект. Тексты — через `fit_text`.
- Числа — только из файлов проекта; нет источника — не пиши число.

## 2. Проверка (всё до показа пользователю)
```
issues = lint(slides, theme, profile=prof)           # 0 ошибок
motion_lint(slides, theme)                            # 0: фигуры не пролетают по тексту
r = build_pptx(slides, theme, out, title=..., profile=prof)
xsd_check(r["path"])                                  # 0
lo_effects_check(r["path"])["ok"]                     # True
pngs = render(r["path"], out_dir); contact_sheet(pngs, sheet)
morphkit.motion.preview(slides, theme, out_dir/"motion", which=[ключевые переходы])
```
Посмотри лист миниатюр и ленты движения сам (чек-лист `../pptx-design/SKILL.md` §5). Нашёл проблему — найди
причину замером и правь генератор; перепроверь. Не больше трёх кругов: потом покажи как есть и назови остаток.

## 3. Ответ
.pptx (SendUserFile, attach), лист миниатюр и 1–3 GIF ключевых переходов (render). Коротко: какие приёмы на каких
переходах, где петли, что LibreOffice не проверяет (Morph свободных форм, z-порядок в переходе, 3D) —
попроси прогнать показ в PowerPoint 2019+/365. Закоммить генератор и бриф.
