"""Кадры из видео-референса для разбора приёма: на сменах сцены и через равные промежутки + лист миниатюр.

    python refs_frames.py ROLIK.mp4 OUT_DIR [--scene 0.08] [--every 0.5] [--max 48] [--width 480]

Нужен ffmpeg. В OUT_DIR: f_XXX_<секунды>.png и sheet.png с отметками времени.
Протокол разбора — pptx-design/references/references-protocol.md.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def duration(video: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                         capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def scene_times(video: Path, threshold: float) -> list[float]:
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf", f"select='gt(scene,{threshold})',showinfo",
                           "-f", "null", "-"], capture_output=True, text=True)
    return [float(t) for t in re.findall(r"pts_time:([0-9.]+)", proc.stderr)]


def grab(video: Path, t: float, out: Path, width: int) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video),
                    "-frames:v", "1", "-vf", f"scale={width}:-2", str(out)], check=True)


def sheet(frames: list[tuple[float, Path]], out: Path, cols: int = 6) -> None:
    ims = [Image.open(p).convert("RGB") for _, p in frames]
    w, h = ims[0].size
    pad, cap = 8, 22
    rows = (len(ims) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * (w + pad) + pad, rows * (h + cap + pad) + pad), (236, 236, 236))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    for k, ((t, _), im) in enumerate(zip(frames, ims)):
        x, y = pad + (k % cols) * (w + pad), pad + (k // cols) * (h + cap + pad)
        draw.text((x, y), f"{k + 1}. {t:.2f} c", fill=(30, 30, 30), font=font)
        canvas.paste(im, (x, y + cap))
    canvas.save(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--scene", type=float, default=0.08, help="порог смены сцены ffmpeg (0..1)")
    ap.add_argument("--every", type=float, default=0.5, help="шаг равномерных кадров, с (0 — не брать)")
    ap.add_argument("--max", type=int, default=48)
    ap.add_argument("--width", type=int, default=480)
    a = ap.parse_args()
    video, out = Path(a.video), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    total = duration(video)
    times = set(round(t, 2) for t in scene_times(video, a.scene))
    if a.every > 0:
        t = 0.0
        while t < total:
            times.add(round(t, 2))
            t += a.every
    times = sorted(times)
    if len(times) > a.max:  # равномерно прореживаем, сохраняя смены сцены в приоритете
        step = len(times) / a.max
        times = [times[int(i * step)] for i in range(a.max)]
    frames = []
    for k, t in enumerate(times):
        p = out / f"f_{k:03d}_{t:06.2f}.png"
        grab(video, t, p, a.width)
        if p.exists():
            frames.append((t, p))
    sheet(frames, out / "sheet.png")
    print(f"{video.name}: {total:.1f} c, кадров {len(frames)} -> {out / 'sheet.png'}")


if __name__ == "__main__":
    main()
