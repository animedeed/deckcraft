---
name: deck-brief
description: "Presentation brief (pick several options per category to build 2–3 different presentations to compare): splits a topic or text into a structure, asks a short survey and proposes a palette, a recurring motif, navigation, a section transition and a motion language per section, each with a reason. “Trust me” mode shows a storyboard; “customize” publishes a survey page with GIF previews. Works in English and Russian. / Бриф новой презентации (можно отметить несколько вариантов в каждой категории и собрать 2–3 разные презентации для сравнения): разбирает текст или тему на структуру (разделы, носитель, глаголы, числа), задаёт короткий опрос, предлагает палитру, сквозной мотив от темы, навигацию, переход между разделами и язык движения каждого раздела — каждое решение с причиной. Режим «доверить» — решаю сам и показываю раскадровку; режим «настроить» — публикую страницу-витрину с GIF-превью, где пользователь меняет выбор, и читаю его ответ. Итог — brief.json и раскадровка для /deck-build."
argument-hint: "[topic, text or file / тема, текст или файл]"
---

# /deck-brief — бриф презентации

Пути ниже — от базы этого скилла. Движок: `../pptx-morph/scripts` (morphkit, лаборатория форм `lab/`).
Правила дизайна: `../pptx-design/SKILL.md` и `../pptx-design/references/structure.md` (их читаешь до раскадровки).


## Язык / Language
Язык опроса, страниц, подписей и самой презентации — язык материала или запроса пользователя: `ru` или `en`.
Передавай его везде: `auto_brief(..., lang=)`, `brief_page.py --lang`, `python -m lab.previews OUT --lang`
(английские GIF — в своей папке), `compare_page.py --lang`, в генераторе — `morphkit.i18n.set_lang(lang)` и
`localize(slides)`. Отвечай пользователю на его языке. The skill text is in Russian; answer in the user's language.

## 1. Разобрать материал на структуру
Источник — аргумент команды: тема, вставленный текст или файл (.md/.docx/.pdf/.pptx — прочитай целиком).
По протоколу «текст → структура» (`../pptx-morph/references/concepts.md`, §2):
- разделы (3–7), у каждого — один главный вывод;
- носитель процесса (что зритель узнаёт на каждом шаге) и цепочка глаголов (8–14 шагов);
- числа, которые надо показать (сверить с файлами, если они есть; не выдумывать);
- где кульминация и где «вау» каждого раздела.
Покажи структуру коротко — списком разделов с выводом каждого.

## 2. Опрос (один вызов AskUserQuestion, только то, чего ещё не знаешь)
1. **Как выбрать оформление?** — «Доверить мне (рекомендуется)» / «Настроить самому по витрине».
2. **Длительность** — 5 / 10 / 15–20 мин.
3. **Аудитория** — защита / лекция / заказчик / коллеги.
4. **Чего избегать?** (multiSelect) — много текста / тёмный фон / сложная анимация / ничего.
Известное из запроса не спрашивай. Без ответа — рекомендация.

## 3. Рекомендация
```
cd ../pptx-morph/scripts
python3 -c "from morphkit.catalog import auto_brief; import json; print(json.dumps(auto_brief(TOPIC, SECTIONS, AUDIENCE, MIN), ensure_ascii=False, indent=1))"
```
`auto_brief` подбирает по словам темы. Проверь его смыслом: если мотив не совпал с темой (`score` 0) или навигация
не подходит аудитории — выбери сам из `morphkit.catalog` (MOTIFS, NAVIGATION, MOTION, TRANSITIONS) и перепиши `reason`
одной фразой «почему для этой темы». Мотив можно и новый, от материала темы (бочка, лист, деталь станка), — тогда
опиши его роли: обложка, указатель, фон, данные, финал (concepts.md §1).
Сохрани в `out/decks/<slug>/brief.json`.

## 4а. «Доверить»
Сразу раскадровка (таблица `№ · раздел · слайд · макет · роль мотива · приём на переходе · петля`), правила —
`structure.md`: одна навигация, один тип перехода между разделами, свой язык движения у раздела, мотив в ролях,
сложная картинка там, где мало текста. Спроси одно: «собираю?». После «да» — /deck-build.

## 4б. «Настроить» — витрина
1. Превью (кэш; ~5 мин, запускать в фоне):
   `cd ../pptx-morph/scripts && python3 -m lab.previews <scratchpad>/brief_assets --lang <lang>` и то же для второго
   языка в `<scratchpad>/brief_assets_<other>` (GIF каждого пункта каталога, карточки 12 палитр, index.json). Если папка
   уже есть — не пересобирай.
2. Страница: `python3 scripts/brief_page.py <scratchpad>/brief_assets --brief out/decks/<slug>/brief.json --lang <lang>
   --assets-other <scratchpad>/brief_assets_<other>` → `index.html` и `publish.json` (карта файлов). Страница открывается
   на `<lang>`, в углу — переключатель RU/EN: меняются подписи, причины и GIF, выбор сохраняется. Без `--assets-other`
   второй язык показывает те же GIF с переведёнными подписями. Всегда добавляй тему, разделы и аудиторию
   пользователя в переводе на второй язык: `--alt-topic "…" --alt-sections "…|…" --alt-audience "…"` (тот же порядок
   разделов; переводи сам) — иначе после переключения они останутся на языке пользователя.
3. Публикация: инструмент Artifact, `file_path` = index.html, `files` = карта из publish.json,
   `capabilities: {"db": {}}`, `icon: "palette"`. Страница сохраняет выбор в документ `brief/choice`.
4. Скажи пользователю: открыть ссылку, поменять что хочется, нажать «Сохранить выбор» и написать «готово».
5. Прочитай выбор: ArtifactData `get`, `collection` "brief", `doc_id` "choice". Если пусто — попроси скопировать
   «Выбор текстом» со страницы в чат. Схема 2 (`schema: 2`): в каждой оси — **список** (порядок = приоритет):
   `palettes`, `motifs`, `navigation`; `transition: {main, accents[]}` — основной переход раздела и акцентные
   нативные (`morphkit.combine.ACCENTS`); `sections: {раздел: [языки движения]}` — первый ведущий; `variants` 1–3;
   `notes` — пожелания (учесть в раскадровке и в профиле презентации).
6. `variants` > 1 → `morphkit.combine.plan_variants(choice)` даёт варианты A/B/C (максимально непохожие
   комбинации, акценты поделены между вариантами, ведущий язык раздела сдвигается). Покажи их одной строкой
   каждый и переходи к /deck-build (он соберёт все и покажет сравнение). `variants` = 1 → слей выбор в brief.json
   → раскадровка (как в 4а) → «собираю?».

Нет инструмента Artifact — отдай `index.html` файлом (SendUserFile, display "render") и попроси вставить выбор текстом.

## 5. Профиль презентации
Запиши `out/decks/<slug>/deck_profile.json` (`morphkit.profile.DeckProfile`): тема, концепт, запреты из опроса
и из `notes`. Правила профиля и отвергнутые приёмы — `../pptx-morph/SKILL.md` и `references/techniques.md`.
