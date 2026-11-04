# Presentation concept: recurring motif, process grammar, palette

Complex transformations work when they run **through the whole presentation** rather than standing as a “trick” on one slide. For this
a presentation has three recurring things:

1. **motif** — one hero object that changes role (cover → pointer → backdrop → chart → portal → finale);
2. **process carrier** — the elements that go through the process (tokens, rows, documents, pairs) and change
   state from step to step;
3. **palette** with a short reason why it fits the topic.

Modules: `morphkit.motif`, `morphkit.process`, `morphkit.palette`. Gallery of all roles and verbs —
`scripts/gallery_concepts.py OUT [ink|lab|neuro|…]`. A complete example presentation — `scripts/examples/demo_deck.py`.

## 1. Motif in roles (`MotifTrack`)

| Role | What is on screen | When |
|---|---|---|
| `hero` | the motif large, on the right or in the center | cover, finale (the beginning and end rhyme) |
| `pointer` | half behind the left edge, part k (petal, body) faces the header; `part=0.5` — the stripes of part k are 50 % filled (progress through the section's topics) | section k; on the section's topics the motif stays put, the divisions fill |
| `backdrop` | huge, ~8–10 % opacity, under everything (z = −400); `next_k` — pre-rotated for the next section so it returns to the pointer without rotating | chart and table slides: “the presentation breathes”, text stays readable |
| `progress` | a small navigator in the corner: k+1 of n parts revealed | long presentations without pointer sections |
| `data` | part sizes = values, labels around the ring | 3–12 quantities of the same kind (importances, shares); labels can be the labels of the carrier's chips — then the chips “fly over” to the petals |
| `portal` | the central disc inflates to fill the screen in the background color | **only if every section is entered this way**; the user does not like it so far — do not use by default |
| `seed` | the motif collapsed into a dot | do not use: “suddenly tiny” (user feedback) |

Rules:
- one presentation — one motif; the role changes no more often than every 1–3 slides, otherwise the motif distracts;
- `pointer` → `pointer` of the neighboring section: rotation by one part (`MotifTrack` keeps the step < 180°);
- `data` only where the motif's parts really correspond to quantities (12 petals = 12 model inputs);
- `portal` — only as the single transition type into ALL sections (otherwise it feels foreign); the next slide starts from an “empty” background;
- after `backdrop`, text and charts lie on top: check contrast (lint) and do not put labels over the densest parts.
- Motifs: `Flower` (multi-layer petals, reference — the user's video), `Orbit` (orbits and bodies, the sun is the portal).
  A new motif = a class with `objs(theme, center, scale, turn, alpha, sizes, focus, disc_scale)`, `facing(k)`, `tip(k)`
  and constant part names.

## 2. Process grammar (`Carrier` + verbs)

A heavy process (“how a model finds an error in a text”, “how training goes”, “how an edit propagates across documents”)
is broken down into **verb steps**. Each verb is a new state of the same carrier objects:

| Verb | Carrier state | Example |
|---|---|---|
| `split` | `row` / `groups` | phrase → tokens; data → train/val/test |
| `encode` | `vectors` | token → embedding column; row → point |
| `relate` | `links` (arcs) | attention, references, graph |
| `score` | `bars` | error probability, importance |
| `flag` | `row(flagged=True)` + `flag_loops()` | the main thing found (error, anomaly) |
| `filter` | `filtered` | what is filtered out shrinks into a trace dot |
| `aggregate` | `merged` | parts merge into the result |
| `compare` | two states side by side | before / after, forecast / actual |
| `cluster` | `groups` | divergence into groups |
| `zoom` | world camera or spotlight | one part large |
| `iterate` | `R.curve` + marker | epochs, iterations |

Carrier names are constant: body `!!{id}{i}` (no text) and label `!!{id}{i}t` — so the body morphs from a chip
into a dot, a bar or a cell, while the label follows along and does not turn into “letter mush” (the text does not change). `plan(verbs)` checks
the storyboard: known verbs, no three identical in a row, there is a climax (`flag`, `aggregate` or `compare`).

### “Text → structure” protocol (what the skill or plugin does from a task description)

1. **Read the task text** and write down: who goes through the process (carrier), what steps happen to it (verbs),
   what is at the end (result), where the main moment is (climax), what numbers there are.
2. **Choose the carrier**: something the viewer can recognize at every step (words of a phrase, rows, documents). If there are
   two carriers (for example, features and samples) — each gets its own stretch of the presentation; the motif is the bridge between them.
3. **Write down the verb chain** (8–14 steps per talk), run `plan()`.
4. **Choose the motif and assign roles**: cover `hero`, sections `pointer` (or `progress`), charts — `backdrop`,
   “by parts” data — `data`, section topics — `pointer(k, part=…)`, finale — `hero`; the transition between sections — one type per presentation.
5. **Pick a palette** with `palette.suggest(topic)` — show 2–3 options with a reason; with no answer, take the first one.
6. **Show the storyboard** as a table: # · slide · layout · verb/technique on the transition (like `scripts/examples/demo_storyboard.md`).
   After approval — build, then checks: `lint`, `xsd_check`, `lo_effects_check`, render and thumbnail sheet.

## 3. Palette with a reason (`palette.suggest`)

The catalog has 12 directions (`CATALOG`): Lab, Cellar, Blueprint, Ink, Control room, Neural, Registry, Clinic,
Ledger, Forest, Classroom, Cosmos. Each has topic tags and one “why” line. `suggest(text, k=3)` returns
options with a reason (`p.reason`: the “why” + the topic words it was chosen by); the output always contains a light and a dark
scheme. If the topic is not recognized — neutral ones: Ink, Classroom, Blueprint. `check_catalog()` — contrast of all themes (empty = ok).

The caption for the user is one line: “**Control room** — dispatcher’s mimic diagram: dark blue background, teal
links, amber — attention. In the topic: power grids.”

## 4. Checks that catch concept bugs

- `lint`: texts do not overlap each other (petal labels on the header, group labels on each other); lines
  fit (`fit_text` wraps in advance); rotation step < 180°; background under text.
- `lo_effects_check(pptx)`: all effects recognized by LibreOffice (`ok: True`); custom signal paths — separately.
- Render and thumbnail sheet: the motif backdrop did not land on top of a chart; carrier labels are at the right parts; no “invented”
  numbers (every number on a slide comes from the project files).


## 5. Motion operators (`morphkit.ops`) — animation for any shape

An operator takes a state (a list of shapes) and returns a new one with the same names — Morph turns one into the other.
One operator works on petals, dots, cards, orbits, fragments; operators compose into chains.

| Operator | What it does | What for |
|---|---|---|
| `explode` / `gather` / `scatter` | burst from the center / gather into a point / scatter | structure, compression, chaos → order |
| `orbit` / `swirl` / `fan` | rotate the system / vortex (outer stronger) / fan around a point | cycle, “pulling in”, choosing options |
| `wave` / `colorwave` / `cascade` | displacement wave / color wave / appearance cascade by distance | a signal passed, propagation |
| `along` / `peel` / `lift` | along a curve / layers as a staircase / push toward the viewer with a shadow | time, versions, the selected topic |
| `tilt3d` / `recede` / `squash` / `shear` / `fold` | plane tilt with perspective / recede to a vanishing point / squash / shear / fold | 2D → 3D: top view, background in depth, orbit, face, sheet |

Pseudo-3D works on outlines: first `to_vec(objs, n)` (a fixed number of points), then `tilt3d` / `recede` —
it morphs smoothly. The `lab/f_ops.py` family shows each operator on five bases and chains of 2–3 operators.

## 6. Motion check

- `motion.preview(slides, theme, out, which=[…])` — frame strips and transition GIFs (Morph, effects, loops). Look at
  every strip: what disappears instead of flying over, what spins the wrong way, what flies over text.
- `qa.motion_lint(slides, theme)` — automatic: a shape that flies over text present on both
  slides (“dots fly off in front of the text”).

_Russian original: concepts.ru.md_
