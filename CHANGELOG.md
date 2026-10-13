# Changelog

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
