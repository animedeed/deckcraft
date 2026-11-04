# Presentation structure: navigation, containers, combining style and motion

Lessons from presentations the authors made themselves (a product website-style presentation, a technical thesis defense) and from showings of our
variants. A presentation is built from **navigation** and **live containers**, not from separate pretty slides.

## 1. Navigation — a system that is always visible

| Technique | How it works | When |
|---|---|---|
| Site menu | a row of sections at the top, the current one highlighted (like website navigation); when the section changes, the highlight moves via Morph | product, "startup" talks, interface demos |
| Block label + counter | "Block 2 — Data" at top left, "9\|27" at the right; the label changes by fading, not morphing | thesis defense, long technical talks |
| Talk map → header | on the "What we'll cover" slide, 3–4 section cards; the current section's card **grows** into the section's header/container, the rest slide off the edge and wait | any talk with 3–6 sections — the user's main technique |
| Motif pointer | a persistent motif beyond the edge, part of the motif points at the topic (`motif.MotifTrack`, pointer role) | conceptual presentations |
| Progress within a section | segments of part of the motif fill up across the section's topics (4 topics: 25 / 50 / 75 / 100 %) — `pointer(k, part=…)` | sections with 3–6 subtopics |

Rule: **one** navigation system per presentation. Menu + motif pointer + counter all at once is noise.

## 2. Live containers and parking

- A **container** is a shape that lives across several slides and changes its role: section card → header → content
  frame → card again on the summary slide. The name stays the same (`!!sec_data`); position and size change.
- **Parking**: objects for upcoming slides already lie beyond the edge (x < 0 or y > 7.5) and slide in via Morph rather than
  appearing out of nowhere. Departing objects leave in the direction the story is "moving" (usually left/down).
- Text inside a container changes by fading (text policy); the container itself morphs.

## 3. Combining style, motif and motion

1. **One motif, one palette, one motion language per section.** Example: the "Data" section — dots and their regrouping;
   "Model" — a fan of links and a signal; "Results" — bars and a spotlight. Within a section the technique repeats
   (the viewer learns to read it); between sections it changes.
2. **The transition between sections is of one type for the whole presentation** (if it's a pointer rotation, it's on every section; if
   card → header, that's everywhere too). A single "special" transition (portal, cube, curtain) in the middle of the presentation looks alien.
   A section change is done by **morphing** (camera, pointer rotation, map → header). Native PowerPoint transitions
   (cube, zoom, fly-through) often cheapen a presentation: by default there are none; only if the user asks —
   and then as a system on all section boundaries, short (≤ 0.6 s), curtains only for the finale.
3. **Complex imagery goes where there is little text**: cover, section opening, the section's (single) "wow" slide, data
   that is itself the picture (petals = values), finale. On slides with paragraphs the motif moves into the background (backdrop) or
   beyond the edge (pointer).
4. **The motif works throughout the presentation, not only on the cover**: entrance (reveal), pointer, chart, background, progress,
   rhyming finale. If the motif never changes role after the cover, it is decoration, not a motif.
5. **The motif comes from the topic.** Wine: a glass (level = value), a bunch (grapes = data points), glass rings (intersections);
   power grid: pylons, wires, waves; documents: sheets, stamps, edits; AI: layers, attention arcs.
6. **Motion explains rather than decorates**: every movement answers the question "what changed?" (the sample
   split, a feature became more important, the signal arrived). If there is no answer, the object stays still.

## 4. Where and how to use complex shapes (from the `pptx-morph/scripts/lab` lab)

| Shape | Role in the presentation |
|---|---|
| intersecting circles, fragments flying apart | "what already exists" — parts of the problem and the shared zone; transition from the whole to its parts |
| layers peeling off | levels of detail: architecture, model layers, "under the hood" |
| a "magnifier" ring segment running around a circle | process cycle, current step; navigation around a circle of stages |
| orbits, spirals | time, iterations, training epochs |
| isometry, cubes, depth | system architecture, technology stack, data "layers" |
| topic motifs (glass, bunch, pylons) | cover, pointer, background, data — a through line |

## 5. Structure checklist (before the storyboard)

- [ ] Which navigation system? One.
- [ ] Which containers live across several slides, and how do they change role?
- [ ] What is parked beyond the edge, and where does it slide in from?
- [ ] The motion language of each section (one line) and the type of transition between sections (one per presentation).
- [ ] Motif roles per slide: where it is the hero, the pointer, the background, the data.
- [ ] Where the 1–2 "wows" are and why exactly there (the climax of meaning).

_Russian original: structure.ru.md_
