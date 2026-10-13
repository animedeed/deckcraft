"""Подбор палитры по теме: каталог направлений с тегами и короткой причиной «почему именно эта гамма».

    from morphkit.palette import suggest
    for p in suggest("Мониторинг нагрузки в электросетях", k=3):
        print(p.title, "—", p.reason)          # подпись для пользователя плагина
        theme = p.theme                         # готовая тема для сборки

Подбор — по словам темы (основы слов, регулярные выражения), затем разнообразие: в выдаче есть и светлая, и тёмная
гамма. Каждая тема каталога проходит проверку контраста (`check_catalog`): текст ≥ 4,5 к фону и к карточкам.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .theme import BLUEPRINT, CELLAR, INK, LAB, Theme, _lum, contrast

_CODE_DARK = {"code_bg": "08090C", "code_ink": "E8E8E4", "code_com": "8E8E89"}
_CODE_LIGHT = {"code_bg": "1E1F24", "code_ink": "E8E6E1", "code_com": "8C8A86"}


def _theme(name: str, title: str, thesis: str, motif: str, c: dict, dark: bool, **kw) -> Theme:
    colors = dict(c)
    colors.setdefault("good", colors["accent2"])
    colors.setdefault("warn", colors["accent3"])
    colors.setdefault("flow", colors["accent"])
    colors.setdefault("on_accent", "0B0B0D" if _lum(colors["accent"]) > 0.25 else "FFFFFF")
    for k, v in (_CODE_DARK if dark else _CODE_LIGHT).items():
        colors.setdefault(k, v)
    colors.setdefault("code_kw", colors["accent"] if dark else "F29E74")
    colors.setdefault("code_str", "A5D6A7")
    colors.setdefault("code_num", "8FC1E3")
    return Theme(name=name, title=title, thesis=thesis, motif=motif, colors=colors, **kw)


GRID = _theme("grid", "Диспетчерская",
              "Ночная мнемосхема: тёмно-синее поле, бирюзовые связи, янтарь — то, что требует внимания",
              "Узлы и линии связей; сигнал бежит по рёбрам", {
                  "bg": "0B1622", "surface": "12202F", "surface2": "1A2C3E", "line": "2A4058",
                  "ink": "EEF3F8", "ink2": "B8C6D6", "muted": "8C9DB1",
                  "accent": "F5A300", "accent2": "2BD4C0", "accent3": "6E93C8", "bad": "FF6B6B"}, True,
              head_bold=True, radius=0.1)

NEURO = _theme("neuro", "Нейросеть",
               "Графит и фиолетовое свечение интерфейсов ИИ; мятный — активация, розовый — ошибка",
               "Слои точек и дуги внимания; активации загораются по очереди", {
                   "bg": "0E0C16", "surface": "17142A", "surface2": "221E38", "line": "363052",
                   "ink": "F2F0FA", "ink2": "C8C3DF", "muted": "9790B4",
                   "accent": "B794F6", "accent2": "5EE6C1", "accent3": "FFB86B", "bad": "FF7A90"}, True,
               head_bold=True, radius=0.16)

REGISTRY = _theme("registry", "Реестр",
                  "Бумага и чернила документа: слоновая кость, тёмно-синий текст, красный — печать и правка",
                  "Листы, поля, штампы; изменение — красная правка поверх текста", {
                      "bg": "F7F4EC", "surface": "EFEADF", "surface2": "E4DDCC", "line": "C9BDA3",
                      "ink": "1B2233", "ink2": "3A4256", "muted": "565C6A",
                      "accent": "B3261E", "accent2": "1F3A68", "accent3": "8A6A12", "bad": "B3261E",
                      "good": "2F6B3A"}, False, head_font="Georgia", radius=0.0)

CLINIC = _theme("clinic", "Клиника",
                "Чистый белый и бирюза — гигиена и доверие; коралл сигналит без тревожного красного",
                "Мягкие круги-клетки и тонкие линии; данные — пульс и кривые", {
                    "bg": "FAFCFC", "surface": "EEF5F5", "surface2": "DDEBEB", "line": "BFD6D6",
                    "ink": "10282C", "ink2": "2E4A4F", "muted": "51696B",
                    "accent": "0B7C7E", "accent2": "C9493C", "accent3": "3D5A99", "bad": "C9493C",
                    "good": "2E7D4F", "warn": "A0620A"}, False, radius=0.18)

LEDGER = _theme("ledger", "Гроссбух",
                "Отчётная бумага, глубокий зелёный и золото — деньги, рост и аккуратные цифры",
                "Колонки цифр, линейки, столбики; рост — зелёным, потери — бордовым", {
                    "bg": "F6F5F0", "surface": "ECEAE2", "surface2": "DEDBCF", "line": "C4BFAE",
                    "ink": "14201A", "ink2": "34433A", "muted": "59625B",
                    "accent": "1E6B47", "accent2": "8E6A12", "accent3": "7A2E2E", "bad": "7A2E2E"}, False,
                radius=0.04)

FOREST = _theme("forest", "Лес",
                "Тёмная хвоя и солнечный свет: природа, климат, медленные циклы",
                "Кольца роста и ветвления; рост — расходящимися кругами", {
                    "bg": "0F1A14", "surface": "16251C", "surface2": "1F3226", "line": "2F4A38",
                    "ink": "EEF4EC", "ink2": "C3D3C2", "muted": "92A897",
                    "accent": "E9C46A", "accent2": "7FC48A", "accent3": "F28F6B", "bad": "F28F6B"}, True,
                radius=0.2)

CLASSROOM = _theme("classroom", "Класс",
                   "Тёплый лист тетради, синий и оранжевый — внимание ученика без перегруза",
                   "Пронумерованные шаги, стрелки, подчёркивания маркером", {
                       "bg": "FFFDF8", "surface": "F4F0E6", "surface2": "E8E2D2", "line": "D3CAB5",
                       "ink": "1D2433", "ink2": "3B4458", "muted": "5F6573",
                       "accent": "A8470C", "accent2": "2F6FDB", "accent3": "2E8B5E", "bad": "B3261E"}, False,
                   radius=0.12)

COSMOS = _theme("cosmos", "Космос",
                "Глубокий чёрно-синий и холодный свет звёзд; тёплый оранжевый — главное событие",
                "Орбиты и тела; масштаб — полётом камеры", {
                    "bg": "07080F", "surface": "0F1220", "surface2": "171B30", "line": "272D4A",
                    "ink": "F0F2FA", "ink2": "BFC5DD", "muted": "8A91AE",
                    "accent": "FF9E5E", "accent2": "7FB2FF", "accent3": "E07BE0", "bad": "FF6B6B"}, True,
                radius=0.2)


@dataclass
class Palette:
    theme: Theme
    why: str  # одна строка: почему эта гамма подходит
    tags: list[str] = field(default_factory=list)  # основы слов (регулярные выражения от начала слова)
    reason: str = ""  # заполняет suggest(): why + совпавшие слова темы
    score: float = 0.0

    @property
    def title(self) -> str:
        return self.theme.title

    @property
    def dark(self) -> bool:
        return _lum(self.theme.colors["bg"]) < 0.2


CATALOG: list[Palette] = [
    Palette(LAB, "лабораторный журнал: белая бумага и тонкие линии, вино — единственный яркий цвет",
            ["вин", "лаборат", "хими", "анализ", "эксперимент", "практик", "датасет", "данн", "wine", "lab"]),
    Palette(CELLAR, "погреб и бокал: глубокий фон, цвет вина и золота — тёплая, «вкусная» тема",
            ["вин", "дегустац", "напит", "гастроном", "ресторан", "еда", "кухн", "food"]),
    Palette(BLUEPRINT, "инженерный чертёж: синяя бумага, сетка и оранжевая разметка там, где важно",
            ["инженер", "чертёж", "чертеж", "конструк", "механ", "строит", "архитект", "систем", "engineer"]),
    Palette(INK, "тушь на чёрном: формы как вырезанная бумага, один акцентный цвет — редакционная подача",
            ["дизайн", "искусств", "типограф", "мод[аы]", "фото", "эссе", "культур", "design", "art", "минимал"]),
    Palette(GRID, "мнемосхема диспетчера: тёмно-синий фон, бирюзовые связи, янтарь — внимание",
            ["энерг", "электр", "лэп", "подстанц", "диспетч", "сетев", "ток[аи]?\\b", "россет", "power", "grid",
             "граф", "связ"]),
    Palette(NEURO, "интерфейс ИИ: графит и фиолетовый, мятный — активация, розовый — ошибка",
            ["нейр", "нейросет", "обучен", "модел", "ии\\b", "машинн", "llm", "трансформер", "эмбеддинг", "ai\\b",
             "ml\\b", "классификат", "токен", "вниман"]),
    Palette(REGISTRY, "бумага и чернила: документ, норматив и правка красной печатью",
            ["закон", "норматив", "нд\\b", "документ", "прав[оа]", "юрид", "регламент", "пп\\b", "фз\\b", "договор",
             "суд", "редакц", "текст", "ошибк", "legal", "law"]),
    Palette(CLINIC, "белый и бирюза — гигиена и доверие; коралл сигналит мягче красного",
            ["мед", "клиник", "биол", "здоров", "пациент", "ген", "днк", "фарм", "health", "bio"]),
    Palette(LEDGER, "отчётная бумага, зелёный и золото — деньги, рост, аккуратные цифры",
            ["финанс", "эконом", "банк", "бюджет", "инвест", "рын", "цен", "прибыл", "выручк", "finance", "money"]),
    Palette(FOREST, "хвоя и солнце: природа, климат и медленные циклы",
            ["эколог", "природ", "лес", "климат", "вод", "агро", "сельск", "почв", "eco"]),
    Palette(CLASSROOM, "лист тетради: синий и оранжевый держат внимание без перегруза",
            ["школ", "урок", "учени", "учител", "курс", "лекци", "образов", "студент", "занят", "education"]),
    Palette(COSMOS, "ночное небо: холодный свет и тёплое главное событие, масштаб — полётом камеры",
            ["космос", "физик", "астроном", "квант", "звезд", "звёзд", "ракет", "орбит", "space", "physics"]),
]


def suggest(text: str, k: int = 3, prefer_dark: bool | None = None) -> list[Palette]:
    """k палитр под тему text с причиной. В выдаче есть и светлая, и тёмная гамма (если k ≥ 2);
    prefer_dark ставит первой гамму нужной светлоты."""
    low = text.lower()
    scored = []
    for p in CATALOG:
        hits = []
        for t in p.tags:
            m = re.search(r"\b" + t, low)
            if m:
                word = re.match(r"\w+", low[m.start():]).group(0)
                hits.append(word)
        q = Palette(p.theme, p.why, p.tags, score=len(set(hits)))
        q.reason = q.why[0].upper() + q.why[1:] + (f". В теме: {', '.join(dict.fromkeys(hits))}." if hits else ".")
        scored.append(q)
    neutral = {t.name: k for k, t in enumerate((INK, CLASSROOM, BLUEPRINT, GRID))}  # если тема не узнана
    scored.sort(key=lambda p: (-p.score, neutral.get(p.theme.name, 99),
                               CATALOG.index(next(c for c in CATALOG if c.theme is p.theme))))
    if prefer_dark is not None:
        scored.sort(key=lambda p: (p.dark != prefer_dark) * 0.5 - p.score)
    out = [scored[0]]
    if k >= 2:  # разнообразие: вторая — противоположной светлоты
        other = next((p for p in scored[1:] if p.dark != out[0].dark), None)
        if other:
            out.append(other)
    for p in scored[1:]:
        if len(out) >= k:
            break
        if p not in out:
            out.append(p)
    return out[:k]


def check_catalog() -> list[str]:
    """Контраст каждой темы каталога: текст к фону и карточкам ≥ требуемого. Пусто — всё в порядке."""
    bad = []
    for p in CATALOG:
        for fg, bg, got, need in p.theme.contrast_report():
            if got < need:
                bad.append(f"{p.theme.name}: {fg} на {bg} = {got} < {need}")
    return bad


__all__ = ["CATALOG", "Palette", "suggest", "check_catalog", "GRID", "NEURO", "REGISTRY", "CLINIC", "LEDGER",
           "FOREST", "CLASSROOM", "COSMOS", "contrast"]
