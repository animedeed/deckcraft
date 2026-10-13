# Участие · Contributing

**[Русский](#русский) · [English](#english)**

## Русский

### Как предложить изменение
1. **Issue.** Опишите ошибку (что делали, что ожидали, что получилось, файл или скриншот) или идею.
   Крупное — сначала обсудить в issue, чтобы не делать зря.
2. **Fork → ветка → правка.** Ветку назовите по сути: `motif-barrel`, `fix-text-overflow`.
3. **Проверка локально** (то же запускает CI):
   ```bash
   pip install -r requirements.txt
   cd plugins/deckcraft/skills/pptx-morph/scripts
   python examples/demo_deck.py /tmp/demo --no-render     # должно завершиться с кодом 0
   ```
4. **Pull Request** по шаблону: что меняется, зачем, как проверено, GIF или скриншот для визуальных правок.
5. Мейнтейнер смотрит, просит поправить или вливает. После слияния версия в `plugin.json` повышается —
   так пользователи получают обновление.

### Что куда добавлять
| Что | Где | Чтобы попало в опрос |
|---|---|---|
| Мотив (новая форма от темы) | семейство `scripts/lab/f_<имя>.py` с функцией `variants(theme)` | пункт в `morphkit/catalog.py` → `MOTIFS` с `preview=("f_<имя>", "<ключ>")` и тегами темы |
| Язык движения | оператор в `morphkit/ops.py` или рецепт в `morphkit/recipes.py` + вариант в лаборатории | пункт в `MOTION` |
| Палитра | `morphkit/palette.py` → `CATALOG` (тема, причина, теги) | автоматически; `check_catalog()` проверяет контраст |
| Приём Morph | `references/techniques.md` + помощник в `recipes.py` | — |
| Правило дизайна | `skills/pptx-design/references/*.md` | — |

### Правила
- Колоды собираются из описания сцен (`O`, `Slide`), XML руками не правится.
- Тексты проходят `fit_text`; `lint` — 0 ошибок, `motion_lint` — 0.
- Числа на слайдах только из данных; иллюстративные значения подписываются как условные.
- Отвергнутые приёмы (`references/techniques.md`, «Отвергнутые») не возвращать без обсуждения.
- Чужой код и ресурсы — только под совместимой лицензией и с указанием источника.

## English

### How to propose a change
1. **Issue.** Describe the bug (what you did, expected, got, a file or screenshot) or the idea. Discuss big
   changes in an issue first.
2. **Fork → branch → change.** Name the branch after the change: `motif-barrel`, `fix-text-overflow`.
3. **Check locally** (CI runs the same):
   ```bash
   pip install -r requirements.txt
   cd plugins/deckcraft/skills/pptx-morph/scripts
   python examples/demo_deck.py /tmp/demo --no-render     # must exit with code 0
   ```
4. **Pull Request** using the template: what changes, why, how it was checked, a GIF or screenshot for visual
   changes.
5. The maintainer reviews, asks for changes or merges. After a merge the `version` in `plugin.json` is bumped so
   users receive the update.

### Where things go
| What | Where | To show up in the survey |
|---|---|---|
| Motif | a family `scripts/lab/f_<name>.py` with `variants(theme)` | an entry in `morphkit/catalog.py` → `MOTIFS` with `preview=("f_<name>", "<key>")` and topic tags |
| Motion language | an operator in `morphkit/ops.py` or a recipe in `morphkit/recipes.py` + a lab variant | an entry in `MOTION` |
| Palette | `morphkit/palette.py` → `CATALOG` (theme, reason, tags) | automatic; `check_catalog()` checks contrast |
| Morph technique | `references/techniques.md` + a helper in `recipes.py` | — |
| Design rule | `skills/pptx-design/references/*.md` | — |

### Rules
- Decks are built from scene descriptions (`O`, `Slide`); no hand-edited XML.
- Text goes through `fit_text`; `lint` has 0 errors, `motion_lint` 0.
- Numbers on slides come from data; illustrative values are labelled as such.
- Rejected techniques (`references/techniques.md`, "Отвергнутые") stay out unless discussed.
- Third-party code and assets only under a compatible license, with attribution.
