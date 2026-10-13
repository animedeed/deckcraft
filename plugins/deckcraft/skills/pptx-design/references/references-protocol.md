# Reference analysis protocol

The goal is to turn someone else's example (a TikTok/Reels video, a .pptx presentation, a Pinterest pin, a Behance frame) into a **recipe** that morphkit reproduces, and to record it in the technique catalog.

## 1. Where the examples live

- Branch `design-refs`, folder `refs/` — the user puts them there. The chat's file size limit is bypassed through GitHub.
  ```
  git fetch origin design-refs
  git ls-tree -r --name-only origin/design-refs refs/
  git show origin/design-refs:refs/<file> > <scratchpad>/refs/<file>
  ```
- Links (TikTok, Pinterest) often do not open without JavaScript. Then ask the user to download the video or screenshots into `refs/`.

## 2. Video → frames

`python pptx-morph/scripts/refs_frames.py ROLIK.mp4 OUT_DIR [--scene 0.08] [--every 0.5]`:
- frames at scene changes (threshold `--scene`) and every N seconds;
- a thumbnail sheet `sheet.png` with timestamps.

From the sheet:
1. Find the **key states** — frames where the motion has stopped. These are the future slides.
2. Find the **in-between frames** — they show exactly how the motion goes: along an arc or a chord, by morphing or fading, rotating around what.
3. Time the durations: from the start to the end of the motion, and the pauses.

## 3. Presentation → how it is built

`python pptx-morph/scripts/refs_deck.py DECK.pptx [--slides 3-7]` prints for each slide:
- transition: type, duration, Morph mode;
- auto-advance (advTm);
- objects: name, type (prstGeom / custGeom / pic / text), x, y, w, h, rotation, 3D, fill;
- `!!` pairs with neighboring slides;
- the animation timeline: effects, presetID, class, delays, durations, repeats.

The output shows **how it is actually done**: what morphs, what appears via an effect, where the service slides are, which objects are parked beyond the edge.

## 4. Recipe card

```
Name:           “Wheel with the active petal sliding out”
Source:         refs/flower.mp4, 0:12–0:31 (Dr. Saeed Faal) / refs/deck.pptx, slides 4–6
Meaning:        cycle steps; the active step comes forward
States:         S1 — flower assembled; S2 — rotated by 36°, petal 2 slid out; …
How it moves:   rotation around the flower's center (arc), sliding out — shape morph; 1.1 s
In morphkit:    V.petal + V.shape(pivot=center, rot=…); active — a different outline with the same n; Fx("entrance_spinner") on entry
Pitfalls:       step > 45° — half-steps; labels travel along a chord; neighboring petals have close colors
Status:         reproduced in gallery_vector.py, slides 3–6; awaiting a slideshow check
```

## 5. Reproduce and check

1. Build a minimal example (2–4 slides) in morphkit, check `lint`, `xsd_check` and the thumbnails.
2. Send it to the user to record a slideshow, compare it with the reference frame by frame.
3. Record a successful recipe:
   - in `pptx-morph/references/techniques.md` — a new item with a helper;
   - in `layouts.md` — if it is a new layout;
   - the takeaway from the slideshow — in `WORKLOG.md`.

## 6. What not to do

- Do not copy other people's images, logos, texts and branded templates. We take the technique: motion, composition, rhythm.
- Do not reproduce “wow” for the sake of “wow”. Every recipe must have a **meaning** (item 4), otherwise it does not go into the catalog.
- Do not guess how it is built from a single frame: first the in-between frames or a dump of the presentation.

_Russian original: references-protocol.ru.md_
