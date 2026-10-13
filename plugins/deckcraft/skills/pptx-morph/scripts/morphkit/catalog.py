"""Каталог выбора для брифа презентации: мотивы, системы навигации, языки движения, переходы между разделами.

Каждый пункт: ключ, название, одна строка «почему / когда», теги темы, превью (вариант лаборатории lab/f_*.py — из
него делается GIF для витрины-опроса). Подбор по теме — как у палитр:

    from morphkit.catalog import suggest_motifs, auto_brief
    suggest_motifs("Оценка качества вина по химическому анализу", k=3)   # -> [Choice(...), ...] с причиной
    brief = auto_brief("Мониторинг нагрузки в электросетях", sections=[...])  # «решаю сам»

Правила (pptx-design/references/structure.md): одна система навигации на презентацию; один тип перехода между разделами;
язык движения — свой у каждого раздела, внутри раздела повторяется; мотив живёт всю презентацию в разных ролях.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from .palette import suggest as suggest_palettes


@dataclass
class Choice:
    key: str
    title: str
    why: str  # одна строка: что даёт и когда уместно
    tags: list[str] = field(default_factory=list)  # основы слов темы (регулярные выражения от начала слова)
    preview: tuple[str, str] | None = None  # (семейство лаборатории, ключ варианта)
    reason: str = ""
    score: float = 0.0
    hits: list[str] = field(default_factory=list)


MOTIFS: list[Choice] = [
    Choice("bunch", "Гроздь и бокалы", "ягоды — точки данных и навигатор с «созреванием» тем; бокал — уровень = доля",
           ["вин", "дегустац", "напит", "виноград", "гастроном", "еда", "wine"], ("f_wine", "seq_bunch")),
    Choice("glass", "Бокал", "жидкость — значение и прогресс; наклон и налив — переход «данные → модель»",
           ["вин", "напит", "бар", "жидк", "объём", "wine"], ("f_wine", "seq_glass")),
    Choice("flower", "Цветок из слоёв", "лепесток = раздел; деления — темы; лепестки = значения; уходит в 3D-фон",
           ["дизайн", "искусств", "природ", "цвет", "мод[аы]", "эстет", "культур", "design"], ("f_living", "seq_flower")),
    Choice("ring", "Кольцо с бегущим сегментом", "увеличенный кусок кольца едет к теме и раскрывается в панель",
           ["цикл", "этап", "kpi", "план", "процесс", "год", "квартал", "стратег"], ("f_rings", "seq_ring")),
    Choice("venn", "Пересечения", "части задачи и общая зона; области становятся панелями и карточками",
           ["подход", "метод", "сравн", "исследован", "аналог", "обзор", "пересеч", "гипотез"], ("f_venn", "seq_story")),
    Choice("platform", "Изометрическая платформа", "слои системы: слой выдвигается панелью, стопка → столбики",
           ["архитект", "систем", "платформ", "сервис", "модул", "стек", "erp", "backend", "инфраструкт"],
           ("f_iso", "seq_platform")),
    Choice("energy", "Линия электропередачи", "провода → синусоиды → векторы фаз; опоры как навигатор",
           ["энерг", "электр", "лэп", "подстанц", "сет[ьи]", "россет", "ток[аи]?\\b", "power"], ("f_energy", "seq_energy")),
    Choice("docs", "Пачка документов", "листы, правки, штампы, лупа над строкой; пункты связываются",
           ["документ", "норматив", "нд\\b", "закон", "регламент", "прав[оа]", "договор", "пп\\b", "фз\\b", "редакц"],
           ("f_docs", "seq_docs")),
    Choice("neural", "Нейросеть и токены", "фраза → токены → векторы → слои → дуги внимания → найденная ошибка",
           ["нейр", "нейросет", "ии\\b", "модел", "обучен", "текст", "токен", "llm", "ml\\b", "классификат"],
           ("f_neural", "seq_neural")),
    Choice("tree", "Дерево и кольца роста", "ветви растут из родителей; срез — кольца лет; лист — иерархия",
           ["эколог", "природ", "лес", "рост", "развит", "истори", "биолог", "климат"], ("f_nature", "seq_nature")),
    Choice("hexmap", "Сотовая карта", "регионы-соты: теплокарта → 3D → рейтинг → вафля",
           ["регион", "гео", "рын", "карт", "город", "территор", "филиал", "продаж"], ("f_mosaic", "seq_map")),
    Choice("number", "Число из осколков", "главное число разбивается на доли, кольцо, столбики и собирается",
           ["результат", "kpi", "выручк", "прибыл", "рост", "метрик", "показател", "итог"], ("f_shatter", "seq_number")),
    Choice("radar", "Радар", "луч находит сигналы, захват раскрывается в панель; сигналы → радиальные столбики",
           ["анализ", "поиск", "мониторинг", "конкурент", "рын", "риск", "обнаруж"], ("f_radar", "seq_radar")),
    Choice("orbit", "Орбиты и комета", "комета-курсор идёт по этапам, переходит на внешнюю орбиту — рост",
           ["космос", "физик", "клиент", "путь", "воронк", "удержан", "орбит"], ("f_orbit", "seq_journey")),
    Choice("gears", "Механизм", "зубец = месяц, зубцы → выручка; передача — шаги процесса",
           ["производств", "механ", "процесс", "автоматизац", "завод", "инженер"], ("f_gears", "seq_machine")),
    Choice("globe", "Глобус", "карта сворачивается в глобус, поворот к городу — география и выход на рынки",
           ["мир", "глобал", "страны", "экспорт", "международ", "рынк"], ("f_sphere", "seq_globe")),
]

NAVIGATION: list[Choice] = [
    Choice("agenda", "Карта доклада → ряд рамок", "карточки разделов складываются в ряд рамок наверху, "
           "дальше едет только подсветка (приём защиты ВКР)", ["защит", "вкр", "доклад", "отчёт", "отчет", "курс"], ("f_nav", "agenda")),
    Choice("menu", "Меню сайта", "строка разделов сверху, подсветка переезжает (как на сайте продукта)",
           ["сайт", "продукт", "стартап", "сервис", "приложен", "интерфейс"], ("f_nav", "menu")),
    Choice("counter", "Метка блока + счётчик", "«Блок 2 — Данные» и «9|27»: строго и спокойно",
           ["техн", "инженер", "архитект", "длинн", "лекци", "урок", "семинар", "занят"], ("f_nav", "counter")),
    Choice("motif", "Мотив у края с делениями", "часть мотива смотрит на заголовок; деления — пройденные темы раздела",
           ["концепт", "образ", "вин", "природ", "дизайн"], ("f_wine", "bunch_ripen")),
]

MOTION: list[Choice] = [
    Choice("dots", "Поле точек", "образцы, люди, пары: поле → группы → столбики; «след» отсеянных",
           ["данн", "выборк", "образц", "пар", "клиент", "люд"], ("f_shatter", "to_dots")),
    Choice("fragments", "Части и сборка", "целое распадается и собирается в данные; область уходит по орбите в панель",
           ["состав", "част", "структур", "компонент"], ("f_venn", "orbit_piece")),
    Choice("circle", "По кругу", "увеличенный сегмент обходит кольцо, прогресс по кругу, комета по этапам",
           ["цикл", "этап", "шаг", "прогресс", "итерац"], ("f_rings", "magnifier")),
    Choice("depth", "Пространство и 3D", "экран раскладывается на слои, план наклоняется, полёт сквозь рамки",
           ["архитект", "слой", "уровн", "устрой", "систем"], ("f_depth", "ui_explode")),
    Choice("flow", "Сигнал по связям", "веер связей проявляется, по рёбрам бежит сигнал",
           ["сет[ьи]", "граф", "связ", "модел", "поток", "передач"], ("f_stringart", "network")),
    Choice("growth", "Рост и сравнение", "столбики растут и перестраиваются; кривая рисуется; доли перетекают",
           ["результат", "метрик", "сравн", "динамик", "обучен"], ("f_data", "bars_pie")),
    Choice("lens", "Лупа и прожектор", "лупа едет по полю/тексту и показывает деталь; прожектор на строке",
           ["ошибк", "проверк", "аудит", "детал", "поиск"], ("f_docs", "magnifier")),
    Choice("fold", "Развороты и сгибы", "лист раскрывается, конверт, развёртка складывается в куб",
           ["план", "итог", "письм", "предложен", "продукт"], ("f_cube", "net_fold")),
]

POINTER_MOTIFS = {"flower", "bunch", "glass", "ring", "orbit", "gears", "radar"}

TRANSITIONS: list[Choice] = [
    Choice("pointer_turn", "Поворот указателя", "мотив у края поворачивается к следующему разделу", [], ("f_nav", "pointer")),
    Choice("agenda_grow", "Карта → ряд рамок", "карта доклада складывается в ряд рамок наверху, едет только подсветка", [], ("f_nav", "agenda")),
    Choice("ripen", "Деление / созревание", "в навигаторе заливается следующая часть", [], ("f_wine", "bunch_ripen")),
    Choice("camera", "Камера в глубину", "камера пролетает к следующему слою мира", [], ("f_depth", "dive_frames")),
]


EN_TAGS = {  # основы английских слов темы
    "bunch": ["wine", "tasting", "grape", "food", "drink"], "glass": ["wine", "drink", "liquid", "volume", "bar"],
    "flower": ["design", "art", "nature", "colou?r", "fashion", "aesthet", "cultur"],
    "ring": ["cycle", "stage", "kpi", "plan", "process", "year", "quarter", "strateg"],
    "venn": ["approach", "method", "compar", "research", "overlap", "hypothes", "review"],
    "platform": ["architect", "system", "platform", "service", "module", "stack", "erp", "backend", "infrastruct"],
    "energy": ["energy", "electric", "power", "grid", "substation", "current"],
    "docs": ["document", "regulat", "law", "policy", "contract", "revision", "legal"],
    "neural": ["neural", "ai\\b", "model", "train", "text", "token", "llm", "ml\\b", "classif", "typo"],
    "tree": ["ecolog", "nature", "forest", "growth", "history", "biolog", "climate"],
    "hexmap": ["region", "geo", "market", "map", "city", "territor", "branch", "sales"],
    "number": ["result", "kpi", "revenue", "profit", "growth", "metric", "total"],
    "radar": ["analys", "search", "monitor", "competit", "risk", "detect"],
    "orbit": ["space", "physic", "customer", "journey", "funnel", "retention", "orbit"],
    "gears": ["manufactur", "mechan", "process", "automat", "factory", "engineer"],
    "globe": ["world", "global", "countr", "export", "international"],
    "agenda": ["defen[cs]e", "thesis", "report", "course", "talk"], "menu": ["website", "product", "startup", "service", "app", "interface"],
    "counter": ["technical", "engineer", "architect", "lecture", "lesson", "seminar", "class"],
    "motif": ["concept", "image", "wine", "nature", "design"],
    "dots": ["data", "sample", "pair", "customer", "people"], "fragments": ["composition", "part", "structure", "component"],
    "circle": ["cycle", "stage", "step", "progress", "iteration"], "depth": ["architect", "layer", "level", "device", "system"],
    "flow": ["network", "graph", "link", "model", "flow", "transfer"], "growth": ["result", "metric", "compar", "dynamic", "train"],
    "lens": ["error", "check", "audit", "detail", "search", "typo"], "fold": ["plan", "summary", "letter", "proposal", "product"],
}
for _c in MOTIFS + NAVIGATION + MOTION:
    _c.tags = list(_c.tags) + [t for t in EN_TAGS.get(_c.key, []) if t not in _c.tags]


def _match(choices: list[Choice], text: str, k: int, lang: str | None = None) -> list[Choice]:
    low = text.lower()
    out = []
    for c in choices:
        hits = []
        for t in c.tags:
            m = re.search(r"\b" + t, low)
            if m:
                hits.append(re.match(r"\w+", low[m.start():]).group(0))
        from .i18n import tr, ui
        q = Choice(**{**asdict(c), "preview": c.preview, "title": tr(c.title, lang), "why": tr(c.why, lang)})
        q.score = len(set(hits))
        q.hits = list(dict.fromkeys(hits))
        q.reason = q.why[0].upper() + q.why[1:] + (f". {ui('topic_words', lang)}: {', '.join(q.hits)}." if hits else ".")
        out.append(q)
    out.sort(key=lambda c: (-c.score, choices.index(next(x for x in choices if x.key == c.key))))
    return out[:k]


def suggest_motifs(text: str, k: int = 3, lang: str | None = None) -> list[Choice]:
    return _match(MOTIFS, text, k, lang)


def suggest_navigation(text: str, k: int = 2, lang: str | None = None) -> list[Choice]:
    return _match(NAVIGATION, text, k, lang)


def suggest_motion(section: str, k: int = 2, lang: str | None = None) -> list[Choice]:
    return _match(MOTION, section, k, lang)


def localized(choices: list[Choice], lang: str | None = None) -> list[Choice]:
    """Копии пунктов каталога с названием и причиной на языке lang."""
    from .i18n import tr
    return [Choice(**{**asdict(c), "preview": c.preview, "title": tr(c.title, lang), "why": tr(c.why, lang)}) for c in choices]


def auto_brief(topic: str, sections: list[str], audience: str = "", minutes: int = 10, lang: str | None = None) -> dict:
    """«Решаю сам»: палитра, мотив, навигация, переход между разделами и язык движения каждого раздела — с причиной.
    Языки движения соседних разделов не повторяются."""
    from .i18n import get_lang, tr
    lang = lang or get_lang()
    pal = suggest_palettes(topic, k=3, lang=lang)
    motif = suggest_motifs(topic, k=3, lang=lang)
    nav = suggest_navigation(topic + " " + audience, k=2, lang=lang)
    # «мотив у края» — только у мотивов с формой-указателем (лепесток, ягода, сегмент кольца, зубец, комета, луч)
    pointer_ok = motif[0].key in POINTER_MOTIFS and motif[0].score > 0
    nav = [c for c in nav if c.key != "motif" or pointer_ok]
    nav_key = nav[0].key if nav and nav[0].score > 0 else ("motif" if pointer_ok else "agenda")
    trans = {"motif": "ripen" if motif[0].key in ("bunch", "glass") else "pointer_turn", "agenda": "agenda_grow",
             "menu": "agenda_grow", "counter": "camera"}[nav_key]
    langs, prev, used = [], None, {}
    for s in sections:
        cand = [c for c in suggest_motion(s, k=len(MOTION), lang=lang) if c.key != prev]
        # совпадение с темой раздела важнее; без совпадения — язык, который в презентации ещё не звучал
        cand.sort(key=lambda c: (-c.score, used.get(c.key, 0), [m.key for m in MOTION].index(c.key)))
        pick = cand[0]
        langs.append({"section": s, "motion": pick.key, "title": pick.title, "reason": pick.reason, "hits": pick.hits})
        used[pick.key] = used.get(pick.key, 0) + 1
        prev = pick.key
    return {"topic": topic, "audience": audience, "minutes": minutes, "lang": lang,
            "palette": {"key": pal[0].theme.name, "title": tr(pal[0].title, lang), "reason": pal[0].reason, "hits": pal[0].hits,
                        "alternatives": [{"key": p.theme.name, "title": tr(p.title, lang), "reason": p.reason} for p in pal[1:]]},
            "motif": {"key": motif[0].key, "title": motif[0].title, "reason": motif[0].reason, "hits": motif[0].hits,
                      "alternatives": [{"key": m.key, "title": m.title} for m in motif[1:]]},
            "navigation": {"key": nav_key, "title": tr(next(c.title for c in NAVIGATION if c.key == nav_key), lang)},
            "transition": {"key": trans, "title": tr(next(c.title for c in TRANSITIONS if c.key == trans), lang)},
            "sections": langs}



def localize_brief(brief: dict, lang: str) -> dict:
    """Тот же бриф (те же ключи и совпавшие слова темы) с подписями и причинами на языке lang —
    для переключателя языка на странице опроса. Тему, разделы и аудиторию на втором языке даёт brief["alt"][lang]
    ({"topic", "audience", "sections": [...]}, их пишет Claude при создании брифа); без него они остаются как
    написал пользователь. У каждого раздела key — исходное название: выбор на странице хранится по нему."""
    from .i18n import tr, ui
    from .palette import CATALOG

    def why(choices, key, hits):
        w = tr(next((c.why for c in choices if c.key == key), ""), lang)
        if not w:
            return ""
        return w[0].upper() + w[1:] + (f". {ui('topic_words', lang)}: {', '.join(hits)}." if hits else ".")

    def title(choices, key):
        return tr(next((c.title for c in choices if c.key == key), key), lang)

    pals = {p.theme.name: p for p in CATALOG}

    def pal(key, hits=()):
        p = pals.get(key)
        if p is None:
            return {"key": key, "title": key, "reason": ""}
        w = tr(p.why, lang)
        return {"key": key, "title": tr(p.title, lang),
                "reason": w[0].upper() + w[1:] + (f". {ui('topic_words', lang)}: {', '.join(hits)}." if hits else ".")}

    b = brief
    alt = (b.get("alt") or {}).get(lang) or {}
    names = alt.get("sections") or []

    def words(tags, text, fallback):
        """Topic words on the page's language: matched in the translated text if there is one."""
        if not text:
            return list(fallback or [])
        low, hits = text.lower(), []
        for t in tags:
            m = re.search(r"\b" + t, low)
            if m:
                hits.append(re.match(r"\w+", low[m.start():]).group(0))
        return list(dict.fromkeys(hits))

    tags_of = lambda choices, key: next((c.tags for c in choices if c.key == key), [])  # noqa: E731
    ph = words(pals[b["palette"]["key"]].tags if b["palette"]["key"] in pals else [], alt.get("topic"),
               b["palette"].get("hits"))
    mh = words(tags_of(MOTIFS, b["motif"]["key"]), alt.get("topic"), b["motif"].get("hits"))
    out = dict(b, lang=lang)
    out["palette"] = {**pal(b["palette"]["key"], ph), "hits": ph,
                      "alternatives": [pal(a["key"]) for a in b["palette"].get("alternatives", [])]}
    m = b["motif"]
    out["motif"] = {"key": m["key"], "title": title(MOTIFS, m["key"]), "hits": mh,
                    "reason": why(MOTIFS, m["key"], mh),
                    "alternatives": [{"key": a["key"], "title": title(MOTIFS, a["key"])} for a in m.get("alternatives", [])]}
    out["navigation"] = {"key": b["navigation"]["key"], "title": title(NAVIGATION, b["navigation"]["key"])}
    out["transition"] = {"key": b["transition"]["key"], "title": title(TRANSITIONS, b["transition"]["key"])}
    secs = []
    for k, s_ in enumerate(b.get("sections", [])):
        nm = names[k] if k < len(names) and names[k] else ""
        hh = words(tags_of(MOTION, s_["motion"]), nm, s_.get("hits"))
        secs.append(dict(s_, key=s_.get("key") or s_["section"], section=nm or s_["section"], hits=hh,
                         title=title(MOTION, s_["motion"]), reason=why(MOTION, s_["motion"], hh)))
    out["sections"] = secs
    out["topic"] = alt.get("topic") or b["topic"]
    out["audience"] = alt.get("audience") or b.get("audience", "")
    return out


__all__ = ["Choice", "localize_brief", "MOTIFS", "POINTER_MOTIFS", "NAVIGATION", "MOTION", "TRANSITIONS", "suggest_motifs", "suggest_navigation",
           "suggest_motion", "auto_brief", "localized", "EN_TAGS"]
