---
name: deck-brief
description: "Presentation brief (pick several options per category to build 2–3 different presentations to compare): splits a topic or text into a structure, asks a short survey and proposes a palette, a recurring motif, navigation, a section transition and a motion language per section, each with a reason. “Trust me” mode shows a storyboard; “customize” publishes a survey page with GIF previews. Works in English and Russian. / Бриф новой презентации (можно отметить несколько вариантов в каждой категории и собрать 2–3 разные презентации для сравнения): разбирает текст или тему на структуру (разделы, носитель, глаголы, числа), задаёт короткий опрос, предлагает палитру, сквозной мотив от темы, навигацию, переход между разделами и язык движения каждого раздела — каждое решение с причиной. Режим «доверить» — решаю сам и показываю раскадровку; режим «настроить» — публикую страницу-витрину с GIF-превью, где пользователь меняет выбор, и читаю его ответ. Итог — brief.json и раскадровка для /deck-build."
argument-hint: "[topic, text or file / тема, текст или файл]"
---

# /deck-brief — presentation brief

Paths below are relative to this skill's base. Engine: `../pptx-morph/scripts` (morphkit, shape lab `lab/`).
Design rules: `../pptx-design/SKILL.md` and `../pptx-design/references/structure.md` (read them before the storyboard).


## Language
The language of the survey, pages, captions and the presentation itself is the language of the user's material or request: `ru` or `en`.
Pass it everywhere: `auto_brief(..., lang=)`, `brief_page.py --lang`, `python -m lab.previews OUT --lang`
(English GIFs go in their own folder), `compare_page.py --lang`, and in the generator — `morphkit.i18n.set_lang(lang)` and
`localize(slides)`. Always answer the user in the user's language.

## 1. Break the material down into a structure
The source is the command argument: a topic, pasted text or a file (.md/.docx/.pdf/.pptx — read it in full).
Follow the “text → structure” protocol (`../pptx-morph/references/concepts.md`, §2):
- sections (3–7), each with one main takeaway;
- the process carrier (what the viewer learns at each step) and the chain of verbs (8–14 steps);
- the numbers to show (check them against the files, if there are any; do not invent them);
- where the climax is and where each section's “wow” is.
Show the structure briefly — as a list of sections with each one's takeaway.

## 2. Survey (one AskUserQuestion call, only what you do not know yet)
1. **How to choose the design?** — “Trust me (recommended)” / “Customize it myself from the showcase”.
2. **Duration** — 5 / 10 / 15–20 min.
3. **Audience** — thesis defense / lecture / client / colleagues.
4. **What to avoid?** (multiSelect) — lots of text / dark background / complex animation / nothing.
Do not ask what is already known from the request. No answer — use the recommendation.

## 3. Recommendation
```
cd ../pptx-morph/scripts
python3 -c "from morphkit.catalog import auto_brief; import json; print(json.dumps(auto_brief(TOPIC, SECTIONS, AUDIENCE, MIN), ensure_ascii=False, indent=1))"
```
`auto_brief` picks by the words of the topic. Check it for sense: if the motif does not match the topic (`score` 0) or the navigation
does not suit the audience — choose yourself from `morphkit.catalog` (MOTIFS, NAVIGATION, MOTION, TRANSITIONS) and rewrite `reason`
as one sentence: “why for this topic”. The motif can also be a new one, drawn from the topic's material (a barrel, a leaf, a machine part) — then
describe its roles: cover, pointer, backdrop, data, finale (concepts.md §1).
Save to `out/decks/<slug>/brief.json`.

## 4a. “Trust me”
Go straight to the storyboard (table `# · section · slide · layout · motif role · technique on the transition · loop`), rules —
`structure.md`: one navigation, one transition type between sections, each section has its own motion language, the motif in roles,
a complex picture where there is little text. Ask one thing: “shall I build it?”. After “yes” — /deck-build.

## 4b. “Customize” — the showcase
1. Previews (cached; ~5 min, run in the background):
   `cd ../pptx-morph/scripts && python3 -m lab.previews <scratchpad>/brief_assets --lang <lang>` and the same for the
   other language into `<scratchpad>/brief_assets_<other>` (a GIF for every catalog item, cards for the 12 palettes,
   index.json). If a folder already exists — do not rebuild it.
2. Page: `python3 scripts/brief_page.py <scratchpad>/brief_assets --brief out/decks/<slug>/brief.json --lang <lang>
   --assets-other <scratchpad>/brief_assets_<other>` → `index.html` and `publish.json` (file map). The page opens in
   `<lang>` and has an RU/EN switch in the corner: captions, reasons and GIFs change, the choice stays. Without
   `--assets-other` the second language shows the same GIFs with translated captions. Always add the user's topic,
   sections and audience translated into the other language: `--alt-topic "…" --alt-sections "…|…" --alt-audience "…"`
   (same order of sections; translate them yourself) — otherwise they stay in the user's language after the switch.
3. Publishing: the Artifact tool, `file_path` = index.html, `files` = the map from publish.json,
   `capabilities: {"db": {}}`, `icon: "palette"`. The page saves the choice to the document `brief/choice`.
4. Tell the user: open the link, change whatever they want, press “Save choice” and write “done”.
5. Read the choice: ArtifactData `get`, `collection` "brief", `doc_id` "choice". If it is empty — ask the user to copy
   “Choice as text” from the page into the chat. Schema 2 (`schema: 2`): each axis is a **list** (order = priority):
   `palettes`, `motifs`, `navigation`; `transition: {main, accents[]}` — the main section transition and accent
   native ones (`morphkit.combine.ACCENTS`); `sections: {section: [motion languages]}` — the first one leads; `variants` 1–3;
   `notes` — wishes (take them into account in the storyboard and in the presentation profile).
6. `variants` > 1 → `morphkit.combine.plan_variants(choice)` gives variants A/B/C (maximally dissimilar
   combinations, accents divided between the variants, the leading language of a section shifts). Show them one line
   each and move on to /deck-build (it builds them all and shows a comparison). `variants` = 1 → merge the choice into brief.json
   → storyboard (as in 4a) → “shall I build it?”.

No Artifact tool — hand over `index.html` as a file (SendUserFile, display "render") and ask the user to paste the choice as text.

## 5. Presentation profile
Write `out/decks/<slug>/deck_profile.json` (`morphkit.profile.DeckProfile`): topic, concept, prohibitions from the survey
and from `notes`. Profile rules and rejected techniques — `../pptx-morph/SKILL.md` and `references/techniques.md`.

_Russian original: SKILL.ru.md_
