"""Язык интерфейса и надписей плагина: ru (по умолчанию) или en.

    from morphkit.i18n import tr, set_lang, localize
    set_lang("en")                  # или переменная окружения DECKCRAFT_LANG=en
    tr("Палитра")                   # -> "Palette"
    slides = localize(slides)       # надписи слайдов (O.txt) на текущем языке

Источник английских строк — data/i18n_en.json {русская строка: английская}. Строки, которых нет в словаре,
остаются как есть, `missing()` их собирает (для проверки перед выпуском). Пользовательский текст презентации
(тема, разделы, тезисы) не переводится — он пишется сразу на языке материала.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import replace
from pathlib import Path

_DATA = Path(__file__).parent / "data" / "i18n_en.json"
_EN: dict[str, str] | None = None
_LANG = os.environ.get("DECKCRAFT_LANG", "ru")
_MISSING: set[str] = set()
_CYR = re.compile("[А-Яа-яЁё]")

# слова-связки, которые движок собирает сам (причины выбора и т. п.)
UI = {
    "ru": {"topic_words": "В теме", "lang_name": "Русский"},
    "en": {"topic_words": "Topic words", "lang_name": "English"},
}


def set_lang(lang: str) -> None:
    global _LANG
    _LANG = "en" if str(lang).lower().startswith("en") else "ru"


def get_lang() -> str:
    return _LANG


def _en() -> dict[str, str]:
    global _EN
    if _EN is None:
        _EN = {}
        for f in (_DATA, _DATA.with_name("ui_en.json")):  # надписи слайдов и каталога + интерфейс страниц
            try:
                _EN.update(json.loads(f.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass
    return _EN


def tr(s, lang: str | None = None):
    """Перевод строки (или списка строк) на язык lang (по умолчанию — текущий)."""
    lang = lang or _LANG
    if lang != "en" or s is None:
        return s
    if isinstance(s, (list, tuple)):
        return type(s)(tr(x, lang) for x in s)
    if not isinstance(s, str) or not _CYR.search(s):
        return s
    out = _en().get(s)
    if out is None:
        _MISSING.add(s)
        return s
    return out


def ui(key: str, lang: str | None = None) -> str:
    return UI.get(lang or _LANG, UI["ru"])[key]


def localize(slides, lang: str | None = None):
    """Копии слайдов с переведёнными надписями (O.txt) и заголовками; для ru — без изменений."""
    lang = lang or _LANG
    if lang != "en":
        return slides
    out = []
    for s in slides:
        objs = [o.copy(txt=tr(o.txt, lang)) if o.txt is not None else o for o in s.objs]
        out.append(replace(s, objs=objs, title=tr(s.title, lang), notes=tr(s.notes, lang)))
    return out


def register(pairs: dict[str, str]) -> None:
    """Добавить/переопределить английские строки (семейство лаборатории со своим примером на английском)."""
    _en().update(pairs)


def missing() -> list[str]:
    return sorted(_MISSING)


__all__ = ["tr", "ui", "set_lang", "get_lang", "localize", "missing", "register", "UI"]
