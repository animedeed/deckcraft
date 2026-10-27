---
name: deck-build
description: "Builds a .pptx with Morph (and/or one interactive HTML file with the same slides) from the brief: a morphkit generator (motif in roles, navigation, motion language per section, process loops) plus full QA — lint, motion check, XSD, effects import, render and thumbnails, GIFs of key transitions; several variants and a comparison page. English or Russian. / Сборка .pptx с Morph (и/или интерактивной HTML-презентации из тех же слайдов) по brief.json и раскадровке из /deck-brief: генератор презентации на morphkit (мотив в ролях, навигация, язык движения раздела, петли процессов), затем полная проверка с замерами — lint, проверка движения (ничего не пролетает по тексту), XSD, распознавание эффектов, рендер и лист миниатюр, GIF ключевых переходов. Итог — .pptx, отчёт и список того, что посмотреть в PowerPoint."
argument-hint: "[brief.json]"
---

# /deck-build — сборка по брифу

Нет брифа — сначала /deck-brief. Пути — от базы скилла; движок `../pptx-morph/scripts`.
Перед кодом прочитай `../pptx-morph/SKILL.md` (правила профиля, Morph, сборка §12, проверка §15) и
`../pptx-design/references/structure.md`.


## Язык / Language
Язык опроса, страниц, подписей и самой презентации — язык материала или запроса пользователя: `ru` или `en`.
Передавай его везде: `auto_brief(..., lang=)`, `brief_page.py --lang`, `python -m lab.previews OUT --lang`
(английские GIF — в своей папке), `compare_page.py --lang`, в генераторе — `morphkit.i18n.set_lang(lang)` и
`localize(slides)`. Отвечай пользователю на его языке. The skill text is in Russian; answer in the user's language.

## 1. Генератор
Пиши `out/decks/<slug>/build_deck.py` (не правь XML руками): `sys.path` → `../pptx-morph/scripts`.
- Тема: `next(p.theme for p in morphkit.palette.CATALOG if p.theme.name == brief["palette"]["key"])`.
- Профиль: `DeckProfile.load(out/decks/<slug>/deck_profile.json)`.
- Мотив: готовые помощники — `morphkit.motif` (Flower, Orbit, `MotifTrack.at(...)` с ролями hero / pointer /
  backdrop / data / progress) и семейства лаборатории (`lab/f_wine.py` Bunch, Glass; `lab/f_iso.py` платформа;
  `lab/f_energy.py`, `lab/f_docs.py`, `lab/f_neural.py`, … — превью у каждого пункта `morphkit.catalog.MOTIFS[*].preview`).
  Бери из них функции-формы, а не слайды целиком; имена — через свой префикс, чтобы не пересечься.
- Навигация: `recipes.agenda` (карта доклада → шапка), `recipes.menu_bar`, `recipes.block_counter` или мотив у края
  (`MotifTrack` pointer с делениями). Одна на презентацию.
- Язык движения раздела → инструменты: dots — `process.Carrier`, `recipes.dots`; fragments — `ops.explode/gather`;
  circle — `recipes.magnify`, кольца; depth — `ops.tilt3d/recede`, камера; flow — `recipes.flow_along`, петли flow;
  growth — `components.Kit.bars`, `recipes.curve`; lens — `recipes.magnify`, `recipes.spotlight`; fold — `ops.fold/peel`.
- Каждый слайд: `layout=`, `technique=`, `title=`, заметки-конспект. Тексты — через `fit_text`.
- Числа — только из файлов проекта; нет источника — не пиши число.

## 1б. Несколько вариантов (выбор из опроса со `variants` > 1)
- `plan_variants(choice)` → список вариантов; генератор презентации принимает вариант (палитра, мотив, навигация,
  `transition.accents`, пулы языков разделов) — как `examples/demo_deck.py --variant JSON --gifs`.
- Смена раздела по умолчанию — Morph-приём (камера, указатель, карта); нативные акценты только если их выбрали
  в опросе (они часто удешевляют презентацию).
- Узор переходов: `transition_pattern(n_разделов + 1, "morph", accents, climax=…, roles={i: "error"})` — акцент
  на входе в раздел (финал — последней главой); пул языков внутри раздела — `motion_schedule(n_слайдов, pool)`.
- Каждый вариант — своя папка: .pptx, `report.json` (variant, проверки, `gifs` одних и тех же моментов, `pattern`),
  `sheet.png`. Проверка §2 — у каждого.
- Сравнение — **только после сборки** вариантов по сохранённому выбору опроса (без опроса не публикуй):
  `python3 scripts/compare_page.py OUT VAR_A VAR_B VAR_C --topic "…" --brief-url <ссылка на опрос> --lang <lang> --alt-topic "<тема на втором языке>"`
  (на странице переключатель RU/EN; GIF — из собранной презентации) → публикуй как артефакт
  (`files` из publish.json, `capabilities: {"db": {}}`, `icon: "compare"`). Решение — ArtifactData `get`
  `compare`/`choice`: `best` (A/B/C или "mix"), `from` (ось → вариант), `result` (итоговые палитра, навигация,
  мотив, переходы), `notes`. Итоговая презентация — генератор с `result`, затем §2–3.

## 1в. HTML (`format` = html или both)
Тот же генератор: слайды → `morphkit.html.export_html(slides, theme, out/deck.html, sections=…, ui={"menu": …,
"hud": True}, lang=lang)`, `.pptx`-двойник — `build_pptx(for_pptx(slides), …)`. Web-слой поверх слайдов
(`web(slide, …)`): у каждого раздела свой вход заголовка; метрики — ссылки на слайды-доказательства с «назад»;
переключатели (`link set` + `alt`/`when`) там, где есть сравнение; живые сцены (`liquid`, `particles`, `signal`,
`gauge`…) — где процесс; пометки `morphkit.draw` (обвести, стрелка, рукопись) — на коде и таблицах. Справочник —
`../pptx-morph/references/web.ru.md`, пример — `../pptx-morph/scripts/examples/demo_web.py`.

## 2. Проверка (всё до показа пользователю)
```
issues = lint(slides, theme, profile=prof)           # 0 ошибок
motion_lint(slides, theme)                            # 0: фигуры не пролетают по тексту
r = build_pptx(slides, theme, out, title=..., profile=prof)
xsd_check(r["path"])                                  # 0
lo_effects_check(r["path"])["ok"]                     # True
pngs = render(r["path"], out_dir); contact_sheet(pngs, sheet)
morphkit.motion.preview(slides, theme, out_dir/"motion", which=[ключевые переходы])
# HTML: снимки всех слайдов и ошибки консоли (0), разнообразие движения
r = morphkit.webdemo.shots(html, out_dir/"web", times=[.5, 3.5]); assert not r["errors"]
morphkit.variety.report(slides)["deck"]              # still_transitions ≤ 0,35, глаголов на слайд ≥ 3
```
Посмотри лист миниатюр и ленты движения сам (чек-лист `../pptx-design/SKILL.md` §5). Нашёл проблему — найди
причину замером и правь генератор; перепроверь. Не больше трёх кругов: потом покажи как есть и назови остаток.

## 3. Ответ
.pptx (SendUserFile, attach), HTML (SendUserFile, display "render") — если собирался, лист миниатюр и 1–3 GIF ключевых переходов (render). Коротко: какие приёмы на каких
переходах, где петли, что LibreOffice не проверяет (Morph свободных форм, z-порядок в переходе, 3D) —
попроси прогнать показ в PowerPoint 2019+/365. Закоммить генератор и бриф.
