# Changelog

## 0.2.1 — 2026-10-13
- RU/EN switch translates the user's topic, sections and audience too (the brief stores them in both languages:
  `brief_page.py --alt-topic --alt-sections --alt-audience`, `compare_page.py --alt-topic`); topic words in the
  reasons come from the translated text. The choice is kept by the original section names.
- README: the English survey screenshot shows an English page.

## 0.2.0 — 2026-10-13
- Survey: pick several palettes, motifs, navigation systems, accent transitions and motion languages per section
  (the number on a card is its priority); the plan of presentation variants A/B/C is shown live. Every item has a GIF
  preview; the section rows switch their GIF as you pick a motion language.
- `morphkit.combine`: most-different variant combos; accent transitions are a system — one type on every section
  boundary or none, the finale accent only at the end; Morph stays the main transition.
- Compare page (only after the variants are built from the saved survey choice): the same moments of every variant
  side by side, images open full size; pick the best or assemble the result from parts.
- English: the whole plugin works in `en` or `ru` — catalog, palettes, GIF captions, demo presentation (with its own
  English sentence), survey and compare pages with an RU/EN switch; skill docs are in English (Russian originals
  are kept as `*.ru.md`).
- Smoother shapes: Hermite smoothing of custom outlines, no gaps between petals and layers; resampling keeps corners.
- Navigation previews (counter, menu, agenda, pointer) and native-transition previews in the survey.
- Update check at session start: "deckcraft X is available — update now / later / skip"
  (off with `DECKCRAFT_NO_UPDATE_CHECK=1`).

## 0.1.1 — 2026-10-13
- Lab examples use illustrative numbers; your own data can be passed via `DECKCRAFT_LAB_DATA` (JSON).
- Text measurement finds metric-compatible fonts on macOS and Windows; XSD and LibreOffice checks are skipped with a hint when missing.

## 0.1.0 — 2026-10-13
- `/deck-brief`: text → structure, short survey; "trust me" mode (auto brief + storyboard) or "customize" mode
  (published survey page with GIF previews, choice saved for Claude to read).
- `/deck-build`: build with morphkit and full QA (lint, motion lint, XSD, LibreOffice effects check, render, GIFs).
- `/deck-remix`: edit an existing .pptx keeping what works (`morphkit.existing.Deck`).
- `/deck-review`: design critique with a severity table and motion sketches of any deck (`Deck.to_slides()`).
- Skills `pptx-morph` (engine, 54 Morph techniques, motif roles, process grammar, 12 palettes, ~300-variant form lab)
  and `pptx-design` (composition, rhythm, deck structure).
- Demo deck built from scratch: `plugins/deckcraft/skills/pptx-morph/scripts/examples/demo_deck.py`.
