---
name: deck-brief
description: "Create a presentation brief with a visual palette, motif and motion survey for PowerPoint and interactive HTML. Use before Deckcraft builds; supports Russian and English."
---

# Deckcraft brief in Codex / ChatGPT Work
Read `../../RUNTIME.md`, `../pptx-design/SKILL.md` and its `references/structure.md` before a storyboard.
Paths are relative to this installed skill. Engine: `../pptx-morph/scripts`.

1. Read the user's source fully. Identify audience, purpose, duration, sections, main claims, process verbs and sourced numbers. Inspect supplied HTML/PPTX before choosing a design. Preserve requested artwork, animation, layout and interactions. Ask only material unknowns, in the user's language (RU or EN).
2. Offer “trust me” or “customize visually”; establish format (`pptx`, `html`, `both`), duration, audience and prohibitions if unknown. For HTML or both formats, always offer “Full controls (recommended)” or “Customize the panel” unless the user's choice is already known. The visual brief includes checkboxes for navigation/slide number, notes, overview, presenter view, annotations/pen, laser pointer, print/PDF, full screen and keyboard help; it also selects section navigation (top/tabs/stamp/none), panel visibility and optional printed notes. Save these decisions in `brief.json.show_ui`. Keep the full panel by default; do not silently omit tools. All HTML decks retain the presentation UI module. If the user supplied a panel reference, preserve its controls unless they request changes.
3. Use `morphkit.catalog.auto_brief(topic, sections, audience, minutes, lang=lang)` as a starting point. Check recommendations against the actual topic; rewrite their reasons. Read `../pptx-morph/references/concepts.md` when planning motif roles and process grammar. Save `deck_profile.json` with `morphkit.profile.DeckProfile`.
4. For visual customization, generate/cache previews using `python -m lab.previews <assets> --lang <lang>` from the engine directory. Build the page with `scripts/brief_page.py <assets> --brief <brief.json> --lang <lang>`. Supply translated `--alt-topic`, `--alt-sections`, `--alt-audience` and optionally `--assets-other` as documented by `--help`. Keep the page and all files from `publish.json` together. Open locally or deliver the complete folder as a ZIP. No external publication is required.
5. “Save choice” downloads `deckcraft-brief-choice.json` and keeps a browser-local copy. The user can also copy the visible JSON. Read the actual saved file or pasted JSON; Codex cannot read localStorage automatically. Confirm topic and validate schema 2, catalog keys, sections, variants 1–3, notes, `show_ui` toolbar keys/menu and selected transition accents before merging it into the brief. An invalid file must not silently fall back to recommendations.
6. For multiple variants use `morphkit.combine.plan_variants(choice)`; preserve priority ordering. Show the storyboard (section, slide purpose, layout, motif role, transition, loop) and obtain the user's agreement unless already given. Then use `deck-build`.

Use the task's output folder for final files and a work folder for previews. Do not write into the plugin, publish or commit during this workflow.
