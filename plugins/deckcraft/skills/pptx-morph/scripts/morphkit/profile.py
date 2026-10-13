"""Профиль презентации: правила, которые сборка и проверка соблюдают для ВСЕЙ презентации.

Профиль заполняется на этапе брифа (опрос пользователя или решение по скиллу) и хранится рядом с презентацией
(deck_profile.json). Значения по умолчанию — выводы из записей показа пользователя (WORKLOG.md, раздел 4):

* изменённый текст не переливается: старый гаснет, новый появляется (text_policy="fade");
* режимы Morph «по словам»/«по буквам» — только если на слайде один текст (иначе буквы улетают в номер страницы);
* без служебных автослайдов: назад листать невозможно; рост из нуля делается эффектами внутри слайда;
* быстрые переходы: Morph ≤ 0,9 с, полёт камеры ≤ 1,2 с, затухание ≤ 0,6 с;
* замок стиля: набор макетов, приёмов и фонов задан заранее — новый стиль посреди презентации запрещён.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class DeckProfile:
    name: str = "default"
    concept: str = ""  # общая идея презентации одной фразой (держится на всех слайдах)
    theme: str = ""  # имя темы morphkit
    motion: str = "calm"  # calm | technical | cinematic | expressive — профиль движения из каталога
    text_policy: str = "fade"  # fade — изменённый текст не морфится; morph — разрешить перелив текста
    allow_char_modes: bool = False  # byWord/byChar при нескольких текстах на слайде
    allow_auto: bool = False  # служебные слайды с автопереходом
    max_morph_ms: int = 900
    max_camera_ms: int = 1200
    max_fade_ms: int = 600
    allowed_layouts: list[str] = field(default_factory=list)  # пусто — любые; иначе замок стиля
    allowed_techniques: list[str] = field(default_factory=list)  # пусто — любые из каталога, кроме banned
    banned_techniques: list[str] = field(default_factory=lambda: list(BANNED_DEFAULT))
    backgrounds: list[str] = field(default_factory=lambda: ["bg"])  # допустимые роли фона слайда
    max_loop_systems: int = 2

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "DeckProfile":
        return cls(**json.loads(Path(path).read_text(encoding="utf-8")))


# Приёмы, отвергнутые пользователем по записям показа (причины — в references/techniques.md, «Отвергнутые»)
BANNED_DEFAULT = ("одометр", "индикатор", "полушаги", "колесо в угол", "круг-граница")

DEFAULT = DeckProfile()


def camera_like(technique: str) -> bool:
    t = technique.lower()
    return any(k in t for k in ("камера", "зум", "полёт", "отъезд", "матрёшка"))
