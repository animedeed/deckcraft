"""morphkit — сборка .pptx с переходом «Трансформация» (Morph), зацикленными анимациями и дизайн-системой."""

from .model import Cam, Loop, O, Run, Slide, apply_camera, parse_line, plain, resolve
from .theme import BLUEPRINT, CELLAR, INK, LAB, READING, SLIDE_H, SLIDE_W, SPEAKER, THEMES, Theme, contrast, mix
from .build import build_pptx
from .presets import TRANSITIONS, Fx

__all__ = ["Cam", "Loop", "O", "Run", "Slide", "apply_camera", "parse_line", "plain", "resolve", "BLUEPRINT", "INK",
           "CELLAR", "LAB", "READING", "SLIDE_H", "SLIDE_W", "SPEAKER", "THEMES", "Theme", "contrast", "mix",
           "build_pptx", "Fx", "TRANSITIONS"]
