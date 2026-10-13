"""Каталог выбора для брифа колоды: мотивы, системы навигации, языки движения, переходы между разделами.

Каждый пункт: ключ, название, одна строка «почему / когда», теги темы, превью (вариант лаборатории lab/f_*.py — из
него делается GIF для витрины-опроса). Подбор по теме — как у палитр:

    from morphkit.catalog import suggest_motifs, auto_brief
    suggest_motifs("Оценка качества вина по химическому анализу", k=3)   # -> [Choice(...), ...] с причиной
    brief = auto_brief("Мониторинг нагрузки в электросетях", sections=[...])  # «решаю сам»

Правила (pptx-design/references/structure.md): одна система навигации на колоду; один тип перехода между разделами;
язык движения — свой у каждого раздела, внутри раздела повторяется; мотив живёт всю колоду в разных ролях.
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
    Choice("agenda", "Карта доклада → шапка", "карточки разделов; текущая вырастает в шапку, остальные ждут за краем "
           "(приём защиты ВКР)", ["защит", "вкр", "доклад", "отчёт", "отчет", "курс"], None),
    Choice("menu", "Меню сайта", "строка разделов сверху, подсветка переезжает (как на сайте продукта)",
           ["сайт", "продукт", "стартап", "сервис", "приложен", "интерфейс"], None),
    Choice("counter", "Метка блока + счётчик", "«Блок 2 — Данные» и «9|27»: строго и спокойно",
           ["техн", "инженер", "архитект", "длинн", "лекци", "урок", "семинар", "занят"], None),
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
    Choice("pointer_turn", "Поворот указателя", "мотив у края поворачивается к следующему разделу", [], None),
    Choice("agenda_grow", "Карточка → шапка", "карта доклада: карточка раздела вырастает, остальные уезжают", [], None),
    Choice("ripen", "Деление / созревание", "в навигаторе заливается следующая часть", [], ("f_wine", "bunch_ripen")),
    Choice("camera", "Камера в глубину", "камера пролетает к следующему слою мира", [], ("f_depth", "dive_frames")),
]


def _match(choices: list[Choice], text: str, k: int) -> list[Choice]:
    low = text.lower()
    out = []
    for c in choices:
        hits = []
        for t in c.tags:
            m = re.search(r"\b" + t, low)
            if m:
                hits.append(re.match(r"\w+", low[m.start():]).group(0))
        q = Choice(**{**asdict(c), "preview": c.preview})
        q.score = len(set(hits))
        q.reason = c.why[0].upper() + c.why[1:] + (f". В теме: {', '.join(dict.fromkeys(hits))}." if hits else ".")
        out.append(q)
    out.sort(key=lambda c: (-c.score, choices.index(next(x for x in choices if x.key == c.key))))
    return out[:k]


def suggest_motifs(text: str, k: int = 3) -> list[Choice]:
    return _match(MOTIFS, text, k)


def suggest_navigation(text: str, k: int = 2) -> list[Choice]:
    return _match(NAVIGATION, text, k)


def suggest_motion(section: str, k: int = 2) -> list[Choice]:
    return _match(MOTION, section, k)


def auto_brief(topic: str, sections: list[str], audience: str = "", minutes: int = 10) -> dict:
    """«Решаю сам»: палитра, мотив, навигация, переход между разделами и язык движения каждого раздела — с причиной.
    Языки движения соседних разделов не повторяются."""
    pal = suggest_palettes(topic, k=3)
    motif = suggest_motifs(topic, k=3)
    nav = suggest_navigation(topic + " " + audience, k=2)
    # «мотив у края» — только у мотивов с формой-указателем (лепесток, ягода, сегмент кольца, зубец, комета, луч)
    pointer_ok = motif[0].key in POINTER_MOTIFS and motif[0].score > 0
    nav = [c for c in nav if c.key != "motif" or pointer_ok]
    nav_key = nav[0].key if nav and nav[0].score > 0 else ("motif" if pointer_ok else "agenda")
    trans = {"motif": "ripen" if motif[0].key in ("bunch", "glass") else "pointer_turn", "agenda": "agenda_grow",
             "menu": "agenda_grow", "counter": "camera"}[nav_key]
    langs, prev, used = [], None, {}
    for s in sections:
        cand = [c for c in suggest_motion(s, k=len(MOTION)) if c.key != prev]
        # совпадение с темой раздела важнее; без совпадения — язык, который в колоде ещё не звучал
        cand.sort(key=lambda c: (-c.score, used.get(c.key, 0), [m.key for m in MOTION].index(c.key)))
        pick = cand[0]
        langs.append({"section": s, "motion": pick.key, "title": pick.title, "reason": pick.reason})
        used[pick.key] = used.get(pick.key, 0) + 1
        prev = pick.key
    return {"topic": topic, "audience": audience, "minutes": minutes,
            "palette": {"key": pal[0].theme.name, "title": pal[0].title, "reason": pal[0].reason,
                        "alternatives": [{"key": p.theme.name, "title": p.title, "reason": p.reason} for p in pal[1:]]},
            "motif": {"key": motif[0].key, "title": motif[0].title, "reason": motif[0].reason,
                      "alternatives": [{"key": m.key, "title": m.title} for m in motif[1:]]},
            "navigation": {"key": nav_key, "title": next(c.title for c in NAVIGATION if c.key == nav_key)},
            "transition": {"key": trans, "title": next(c.title for c in TRANSITIONS if c.key == trans)},
            "sections": langs}


__all__ = ["Choice", "MOTIFS", "POINTER_MOTIFS", "NAVIGATION", "MOTION", "TRANSITIONS", "suggest_motifs", "suggest_navigation",
           "suggest_motion", "auto_brief"]
