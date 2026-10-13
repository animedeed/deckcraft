"""Дизайн-система колоды: цвета по ролям, шрифты, шкала кегля, сетка, режим плотности.

Цвет задаётся ролью, а не числом: в описании слайдов пишут fill="accent", col="ink2".
Тема — единственное место, где роли превращаются в hex. Смена темы перекрашивает всю колоду.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

SLIDE_W, SLIDE_H = 13.333, 7.5  # дюймы, 16:9

# Шрифты, которые есть в Office на Windows и Mac, и их метрически совместимые замены для проверки и видео.
# Метрическая совместимость = одинаковая ширина символов, поэтому проверка переносов здесь совпадёт с PowerPoint.
SAFE_FONTS = {
    "Calibri": "Carlito",
    "Arial": "Liberation Sans",
    "Times New Roman": "Liberation Serif",
    "Courier New": "Liberation Mono",
}
# Шрифты с характером без метрической замены: использовать с запасом ширины ~10% (проверка приблизительная).
APPROX_FONTS = {"Georgia": "DejaVu Serif", "Consolas": "DejaVu Sans Mono", "Segoe UI": "DejaVu Sans",
                "Cambria": "DejaVu Serif", "Bahnschrift": "DejaVu Sans"}


def _lum(hex_color: str) -> float:
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4))
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    """Контраст WCAG 2.x между двумя цветами hex без '#'."""
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def mix(a: str, b: str, t: float) -> str:
    """Смешение цветов: t=0 -> a, t=1 -> b."""
    ca = [int(a[i:i + 2], 16) for i in (0, 2, 4)]
    cb = [int(b[i:i + 2], 16) for i in (0, 2, 4)]
    return "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(ca, cb))


@dataclass(frozen=True)
class TypeScale:
    """Кегли в pt. «Крупнее — тоньше»: display и h1 обычного начертания, мелкий текст — полужирные метки."""
    display: float = 60
    h1: float = 36
    h2: float = 26
    lead: float = 22
    body: float = 18
    small: float = 15
    caption: float = 13
    code: float = 14
    label: float = 12  # метки разделов, подписи осей; меньше 12 не используется
    line: float = 1.12  # межстрочный множитель для основного текста


@dataclass(frozen=True)
class Grid:
    """12 колонок по ширине 13,333 дюйма."""
    margin_x: float = 0.65
    margin_top: float = 0.55
    margin_bottom: float = 0.5
    columns: int = 12
    gutter: float = 0.25

    @property
    def col_w(self) -> float:
        return (SLIDE_W - 2 * self.margin_x - (self.columns - 1) * self.gutter) / self.columns

    def x(self, col: int) -> float:
        """Левая граница колонки col (1..12)."""
        return self.margin_x + (col - 1) * (self.col_w + self.gutter)

    def w(self, span: int) -> float:
        """Ширина span колонок вместе с промежутками."""
        return span * self.col_w + (span - 1) * self.gutter

    def span(self, col: int, span: int) -> tuple[float, float]:
        return self.x(col), self.w(span)

    @property
    def content_w(self) -> float:
        return SLIDE_W - 2 * self.margin_x


@dataclass(frozen=True)
class Density:
    """Режим плотности: speaker — одна мысль на слайд; reading — самодостаточные слайды с пояснениями."""
    name: str = "reading"
    max_bullets: int = 6
    max_words_per_slide: int = 90
    min_body_pt: float = 15
    min_any_pt: float = 12


SPEAKER = Density("speaker", max_bullets=3, max_words_per_slide=35, min_body_pt=22, min_any_pt=14)
READING = Density("reading", max_bullets=6, max_words_per_slide=90, min_body_pt=15, min_any_pt=12)


@dataclass(frozen=True)
class Theme:
    name: str
    title: str
    thesis: str  # визуальный тезис одной фразой
    colors: dict = field(default_factory=dict)
    head_font: str = "Calibri"
    body_font: str = "Calibri"
    mono_font: str = "Courier New"
    head_bold: bool = False
    head_caps_labels: bool = True
    scale: TypeScale = TypeScale()
    grid: Grid = Grid()
    density: Density = READING
    radius: float = 0.08  # скругление карточек, дюймы; 0 — острые углы
    motif: str = ""

    def c(self, token: str | None) -> str | None:
        """Роль -> hex. Принимает и готовый hex из 6 символов."""
        if token is None:
            return None
        if token in self.colors:
            return self.colors[token]
        if len(token) == 6 and all(ch in "0123456789abcdefABCDEF" for ch in token):
            return token.upper()
        raise KeyError(f"нет цвета {token!r} в теме {self.name}")

    def qa_font(self, font: str) -> str:
        return SAFE_FONTS.get(font) or APPROX_FONTS.get(font) or "DejaVu Sans"

    def font(self, role: str) -> str:
        return {"head": self.head_font, "body": self.body_font, "mono": self.mono_font}.get(role, role)

    def contrast_report(self) -> list[tuple[str, str, float, float]]:
        """Пары «текст на фоне», которые встречаются в колоде, с минимальным требуемым контрастом."""
        pairs = [("ink", "bg", 4.5), ("ink2", "bg", 4.5), ("muted", "bg", 4.5), ("accent", "bg", 4.5),
                 ("ink", "surface", 4.5), ("ink2", "surface", 4.5), ("muted", "surface", 4.5),
                 ("accent", "surface", 4.5), ("ink2", "surface2", 4.5), ("muted", "surface2", 4.5),
                 ("code_ink", "code_bg", 4.5), ("code_com", "code_bg", 4.5), ("on_accent", "accent", 4.5)]
        out = []
        for fg, bg, need in pairs:
            if fg in self.colors and bg in self.colors:
                out.append((fg, bg, round(contrast(self.colors[fg], self.colors[bg]), 2), need))
        return out

    def with_density(self, density: Density) -> "Theme":
        return replace(self, density=density)


# ----------------------------------------------------------------------------- готовые направления

LAB = Theme(
    name="lab", title="Лаборатория",
    thesis="Лабораторный журнал: белая бумага, тонкие линии, крупная типографика, вино — единственный яркий цвет",
    colors={
        "bg": "FBFAF8", "surface": "F1EFEA", "surface2": "E6E2DA", "line": "CFC9BE",
        "ink": "16171B", "ink2": "3E4048", "muted": "66625B",
        "accent": "8E1F33", "on_accent": "FFFFFF", "accent2": "4F6B2A", "accent3": "B8860B",
        "good": "2F6B3A", "warn": "A86A00", "bad": "A3272F",
        "code_bg": "1E1F24", "code_ink": "E8E6E1", "code_kw": "F29E74", "code_str": "A5D6A7",
        "code_com": "8C8A86", "code_num": "8FC1E3", "flow": "8E1F33", "red_wine": "8E1F33", "white_wine": "B8860B",
    },
    head_font="Calibri", body_font="Calibri", mono_font="Courier New", radius=0.0,
    motif="Тонкие линейки и номера-«колонтитулы» как в лабораторном журнале; данные — точками и столбиками",
)

CELLAR = Theme(
    name="cellar", title="Погреб",
    thesis="Тёмный погреб: глубокий фон, светящиеся потоки и цифры цвета вина и золота",
    colors={
        "bg": "121015", "surface": "1D1A21", "surface2": "2A2630", "line": "3A3540",
        "ink": "F3EEE7", "ink2": "C9C2B8", "muted": "9A93A0",
        "accent": "E25A70", "on_accent": "12090B", "accent2": "D9A441", "accent3": "7FB685",
        "good": "7FB685", "warn": "D9A441", "bad": "E06C75",
        "code_bg": "0B0A0D", "code_ink": "E9E4DC", "code_kw": "D9A441", "code_str": "9CCB9F",
        "code_com": "8E8794", "code_num": "E7859A", "flow": "D9A441", "red_wine": "E25A70", "white_wine": "D9A441",
    },
    head_font="Calibri", body_font="Calibri", mono_font="Courier New", radius=0.12,
    motif="Мягкие светящиеся узлы и точки-потоки на тёмном; круг-«бокал» как сквозной якорь",
)

BLUEPRINT = Theme(
    name="blueprint", title="Чертёж",
    thesis="Инженерный чертёж: синяя бумага, сетка, тонкие белые линии, оранжевая разметка там, где важно",
    colors={
        "bg": "0F2238", "surface": "152C47", "surface2": "1C3858", "line": "2E4D70",
        "ink": "EAF2FA", "ink2": "B7CBE0", "muted": "8FA8C4",
        "accent": "FF8A3D", "on_accent": "1A0E05", "accent2": "4FD1C5", "accent3": "F2C14E",
        "good": "4FD1C5", "warn": "F2C14E", "bad": "FF6B6B",
        "code_bg": "0A1828", "code_ink": "DCE8F5", "code_kw": "FF8A3D", "code_str": "7EE0D2",
        "code_com": "8FA8C4", "code_num": "F2C14E", "flow": "4FD1C5", "red_wine": "FF6B6B", "white_wine": "F2C14E",
    },
    head_font="Arial", body_font="Arial", mono_font="Courier New", radius=0.0,
    motif="Сетка-миллиметровка, размерные линии и моноширинные метки; потоки — бирюзовые пакеты",
)

INK = Theme(
    name="ink", title="Тушь",
    thesis="Тушь на чёрном: многослойные белые и серые формы, как вырезанная бумага; янтарь — единственный цвет",
    colors={
        "bg": "0B0B0D", "surface": "151518", "surface2": "1F1F24", "line": "34343B",
        "ink": "F4F4F2", "ink2": "C9C9C4", "muted": "8E8E89",
        "accent": "F5A300", "on_accent": "0B0B0D", "accent2": "E9E7E1", "accent3": "6F7A86",
        "good": "7FD1B9", "warn": "F5A300", "bad": "FF6B6B",
        "code_bg": "060607", "code_ink": "EDEDEA", "code_kw": "F5A300", "code_str": "9FD8C4",
        "code_com": "8E8E89", "code_num": "F2B880", "flow": "F5A300",
    },
    head_font="Calibri", body_font="Calibri", mono_font="Courier New", head_bold=True, radius=0.14,
    motif="Цветок из многослойных лепестков — указатель темы у края экрана; лепесток раскрывается в панель",
)

THEMES = {t.name: t for t in (LAB, CELLAR, BLUEPRINT, INK)}
