---
name: "pptx-design"
description: "Presentation design before code: brief, palette roles and contrast, typography, slide composition, 32 layouts, deck rhythm and structure (one navigation, one section transition, a motion language per section), data forms, storyboard and critique, reference analysis. / Дизайн презентаций без кода: бриф и визуальный тезис, палитра по ролям и контраст, типографика с кириллицей, композиция слайда (фокус, масштаб, асимметрия, пустота, нарушение сетки, шапки без однообразия), каталог 32 макетов, ритм презентации (акты, плотность, дыхание, рифма начала и конца, язык движения по разделам), выбор формы для данных и процессов, три стилевых превью, раскадровка и критика, протокол разбора референсов (презентации, видео TikTok/Reels, Pinterest) в рецепты. Использовать вместе с pptx-morph (сборка) для любой презентации, где важно, чтобы она выглядела сделанной дизайнером, а не шаблоном, и когда пользователь присылает примеры, на которые надо равняться."
---

# Presentation design: decisions before code

This skill answers the question **"how should it look and move"**. The `pptx-morph` skill answers the question **"how to build it"**: the morphkit engine, Morph, animations, vector, QA. Decisions are made and the storyboard is written here first, then the presentation is built from it in pptx-morph.

The main rule: **every slide is a composition, not a template with text plugged in.** If all slides share the same header ("label · title" at the top left) and only the middle changes, the presentation looks generated, even when its animations are good.

## 1. Process
1. **Brief** (`references/design-system.md`, §1): audience, goal, density, visual thesis, motif, constraints.
   - **Palette** — 2–3 options from `pptx-morph` `palette.suggest(topic)` with one line of "why this scheme" (light and dark).
   - **Concept**: the recurring motif and its roles across the presentation, the process carrier and the chain of verbs
     (`pptx-morph/references/concepts.md`): complex transformations run through the whole presentation, not on one slide.
   - If the topic is a heavy process (an algorithm, model training, a lab exercise): first the "text → structure" protocol
     (same file, §2): carrier, verbs, climax, motif roles.
2. **Structure** (`references/structure.md`): one navigation system, live containers, parking off the edge,
   motion language per section, one transition type between sections, motif roles per slide.
3. **Presentation rhythm** (`references/rhythm.md`):
   - acts and density changes;
   - where the "breath" is, where the "wow" is — one per section;
   - motion language per section;
   - rhyme between the beginning and the end.
3. **Three style previews** — built via `pptx-morph` (`build_previews`). The user makes the choice.
4. **Storyboard.** For each slide: layout (`references/layouts.md`), focus, what moves, Morph technique (`pptx-morph/references/techniques.md`), what appears after the transition, loops, the meaning of the notes. Table — `references/rhythm.md`, §6.
5. **Storyboard critique** before the build (checklist §5 below).
6. Build in `pptx-morph` → render → **critique from thumbnails** (§5) → fixes.
7. If the user sent examples — first **reference analysis** (`references/references-protocol.md`); the recipes go into the storyboard.

## 2. Composition: six decisions for every slide
In detail, with techniques and examples — `references/composition.md`.
1. **Focus.** One point the eye lands on first: a number, a diagram, a word. The focus is at least 2–3 times larger than everything else.
2. **Hierarchy — three levels, no more:** focus → support (title, captions) → auxiliary (label, footer). Each level differs in size **and** in color or saturation.
3. **Scale as a tool.** One big number instead of four medium ones. A diagram over 70% of the slide instead of an icon in the corner.
4. **Asymmetry and tension.** Split the slide 1/3 + 2/3 or 5 + 7 columns, not 50/50. Put the focus on the lines of thirds, not in the center. Centering — only for statements and the finale.
5. **Empty space works.** 30–45% of the area is empty, margins ≥ 0.65″. Empty space next to the focus, not smeared evenly.
6. **The grid and breaking it.** Everything sits on 12 columns. One element per slide may break the grid: a bleed off the edge, a giant number, a diagonal. Only one, and on purpose.

## 3. Headers without monotony
Header systems (`references/composition.md`, §6) alternate according to the meaning of the slide:
- **A. Label + title at the top left** — only for "document" slides (table, code).
- **B. Title inside the composition** — a caption to a diagram, a conclusion under a number.
- **C. Side column** — header on the right or left, diagram at full height.
- **D. Section number as texture** — a huge semi-transparent digit, title next to it.
- **E. No header** — a statement slide, a hero number, a full-screen diagram; context comes from a recurring anchor (color, progress).
- **F. Breadcrumbs** — the path "Project A › P3 › split" in small type at the bottom, only on navigation slides.

Rules:
- The context "Project A · practice N" is written on the title slide, on section slides and in the footer, but **not** as a label above every title. Inside a section the context is held by anchors: section color, number in the corner, progress dots.
- One header system — no more than 3 slides in a row.
- A conclusion title instead of a topic title: "The network is off by 0.54 points", not "Results".

## 4. Presentation rhythm (brief; in detail — `references/rhythm.md`)
- A presentation consists of **acts**: setup → problem → method → evidence → conclusion. Each act has its own motion language and, optionally, its own tint.
- Density alternates: dense slide → "inhale" (one number or phrase) → dense. Three dense slides in a row lose the viewer.
- A section has **one "wow" technique** (wheel, matryoshka, scatter, isometry); the rest is calm Morph. A "wow" on every slide loses its value.
- The beginning and the end rhyme: the same world or diagram, the finale highlights the result.

## 5. Critique: checklist before showing
Look at the contact sheet (`pptx-morph`: `render` → `contact_sheet`) as an unfamiliar viewer.

**Slide:**
- [ ] The focus is visible within 1 second, and there is only one.
- [ ] Hierarchy: three levels, auxiliary elements do not compete with the main one.
- [ ] The header does not repeat the previous 3 slides; the title is a conclusion.
- [ ] Asymmetry or deliberate centering; empty space next to the focus.
- [ ] Nothing touches the edges by accident; a bleed is single and intentional.
- [ ] Color: a dominant, one accent, status colors only for statuses.
- [ ] Text ≤ the mode's limit; if it does not fit — two slides.

**Presentation:**
- [ ] ≥ 6 different layouts per 8 scenes.
- [ ] Density changes and breathing room.
- [ ] One "wow" per section.
- [ ] The beginning and the end rhyme.

**Motion:**
- [ ] Every transition has a meaning: "what is preserved, what changes".
- [ ] No identical techniques in a row (except series).
- [ ] Loops only on processes.

**Anti-patterns** (`references/design-system.md`, §6): a rule under the title, full-width bands, a colored edge on a card, emoji, "icon in a circle", a "purple on white" gradient, shadows without meaning.

## 6. The user's references
The user can put examples (.pptx presentations, videos, screenshots) in the `design-refs` branch, folder `refs/`:
```
git fetch origin design-refs && git ls-tree -r --name-only origin/design-refs refs/
git checkout origin/design-refs -- refs/          # or git show origin/design-refs:refs/<file> > <path>
```
Analysis follows the protocol in `references/references-protocol.md`:
1. Video frames — `pptx-morph/scripts/refs_frames.py`.
2. Presentation structure — `pptx-morph/scripts/refs_deck.py`.
3. Recipe card.
4. Reproduction in morphkit.
5. Entry in the technique catalog.

We learn techniques; we do not copy other people's images, logos and texts.

## References
| File | When to read |
|---|---|
| `references/design-system.md` | brief (template), palette by roles, contrast, fonts with Cyrillic, grid, density, anti-patterns |
| `references/structure.md` | presentation structure: navigation (menu, label + counter, talk map → header, pointer motif), live containers and parking, combining style and motion, where to use complex shapes |
| `references/composition.md` | focus, hierarchy, scale, asymmetry, empty space, grid and breaking it, reading paths, header systems, "magazine" layout techniques |
| `references/layouts.md` | 32 layouts: where the focus is, grid division, which Morph techniques fit, density |
| `references/layouts-basic.md` | 16 basic archetypes with coordinates (from pptx-morph v2) |
| `references/rhythm.md` | acts, density, breathing, "wow" per section, motion language, durations, storyboard |
| `references/infographics.md` | which form to choose for a number, a share, a comparison, a distribution, a flow, a cycle, a hierarchy |
| `references/references-protocol.md` | analysis of submitted presentations and videos into recipes |
| `references/sources.md` | studied sources and what was taken from each |

_Russian original: SKILL.ru.md_
