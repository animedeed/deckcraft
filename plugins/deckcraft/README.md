# deckcraft

Плагин Claude Code для презентаций .pptx с переходом «Трансформация» (Morph). Публичный репозиторий,
описание на русском и английском: https://github.com/animedeed/deckcraft

| Команда | Что делает |
|---|---|
| `/deck-brief [тема или файл]` | разбор материала на структуру, короткий опрос; «доверить» — раскадровка, «настроить» — витрина с GIF |
| `/deck-build [brief.json]` | сборка движком morphkit и проверка: lint, движение, XSD, эффекты, рендер, GIF переходов |
| `/deck-remix [pptx] [что поменять]` | доработка существующей колоды с сохранением удачного |
| `/deck-review [pptx]` | дизайн-критика с таблицей серьёзности и эскизом движения |

## Установка
```
claude plugin marketplace add animedeed/deckcraft
claude plugin install deckcraft@deckcraft
pip install python-pptx lxml Pillow numpy shapely
```
Рекомендуется скилл pptx от Anthropic (схемы для XSD-проверки):
`claude plugin marketplace add anthropics/skills && claude plugin install document-skills@anthropic-agent-skills`.
LibreOffice (`soffice`) — для рендера и проверки эффектов.
