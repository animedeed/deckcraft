"""XML переходов и анимаций слайда.

* transition_xml — любой из 53 нативных переходов (presets.TRANSITIONS), Morph — с запасным затуханием.
* timing_xml     — одна временная шкала слайда: появление anim_*, петли и эффекты библиотеки presets (Fx).

Все эффекты запускаются «с предыдущим» от начала слайда, без щелчков. Зацикливание — repeatCount="indefinite"
на узле эффекта (в интерфейсе PowerPoint: «Повторение: до окончания слайда»).
"""

from __future__ import annotations

from dataclasses import dataclass, field

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"


MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
P14 = "http://schemas.microsoft.com/office/powerpoint/2010/main"


def transition_xml(kind: str, dur_ms: int, mode: str = "byObject", adv_ms: int | None = None,
                   opts: dict | None = None) -> str:
    """Переход к слайду: любой ключ presets.TRANSITIONS, 'none' (без перехода) или '' (то же).

    Элементы без префикса (fade, push, wipe …) — часть ISO-схемы; длительность p14:dur добавляется в ветке
    mc:Choice Requires="p14". Переходы p14/p15/p159 (vortex, curtains, morph …) — в mc:Choice с запасным
    затуханием в mc:Fallback для версий PowerPoint, которые их не знают.
    """
    from .presets import NS_URI, TRANSITIONS

    adv = f' advTm="{adv_ms}"' if adv_ms is not None else ""
    if kind in ("none", ""):
        return f'<p:transition xmlns:p="{P_NS}"{adv}/>' if adv else ""
    if kind not in TRANSITIONS:
        raise KeyError(f"неизвестный переход {kind!r}; есть: {', '.join(TRANSITIONS)}")
    prefix, el, attrs = TRANSITIONS[kind]
    attrs = dict(attrs)
    if kind == "morph":
        attrs["option"] = mode
    attrs.update(opts or {})
    a = "".join(f' {k}="{v}"' for k, v in attrs.items())
    req = prefix or "p14"
    ns = f' xmlns:p14="{P14}"' + (f' xmlns:{prefix}="{NS_URI[prefix]}"' if prefix and prefix != "p14" else "")
    tag = f"{prefix}:{el}" if prefix else f"p:{el}"
    fallback = "<p:fade/>" if prefix else f"<p:{el}{a}/>"
    return (f'<mc:AlternateContent xmlns:mc="{MC}">'
            f'<mc:Choice{ns} Requires="{req}">'
            f'<p:transition xmlns:p="{P_NS}" spd="slow" p14:dur="{dur_ms}"{adv}><{tag}{a}/></p:transition></mc:Choice>'
            f'<mc:Fallback><p:transition xmlns:p="{P_NS}" spd="slow"{adv}>{fallback}</p:transition></mc:Fallback>'
            '</mc:AlternateContent>')


@dataclass
class Effect:
    """Один эффект на шкале слайда; delay — мс от начала шкалы слайда."""
    kind: str  # appear | show | flow | pulse | ripple | spin | blink
    spid: int
    delay: int
    dur: int
    repeat: bool = False
    path: str = ""  # для flow: относительный путь «M 0 0 L dx dy … E» в долях размера слайда
    scale: float = 1.0
    has_text: bool = False
    extra: dict = field(default_factory=dict)


@dataclass
class FxCall:
    """Эффект из библиотеки presets на шкале слайда (delay — мс от начала шкалы)."""
    fx: object  # presets.Fx
    spid: int
    delay: int
    has_text: bool = False


class _Ids:
    def __init__(self, start: int = 3) -> None:
        self.n = start - 1

    def __call__(self) -> int:
        self.n += 1
        return self.n


def _tgt(spid: int) -> str:
    return f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>'


def _effect_xml(e: Effect, ids: _Ids) -> str:
    rep = ' repeatCount="indefinite"' if e.repeat else ""
    a = ids()
    head = lambda preset, cls, extra="": (  # noqa: E731
        f'<p:par><p:cTn id="{a}" presetID="{preset}" presetClass="{cls}" presetSubtype="0"{rep}{extra} fill="hold" '
        f'{"grpId=\"0\" " if e.has_text or cls == "entr" else ""}nodeType="withEffect">'
        f'<p:stCondLst><p:cond delay="{e.delay}"/></p:stCondLst><p:childTnLst>')
    tail = "</p:childTnLst></p:cTn></p:par>"

    if e.kind == "appear":  # рецепт pptx-morph: видимость + затухание 500 мс + подъём на 4% высоты
        return (head(42, "entr") +
                f'<p:set><p:cBhvr><p:cTn id="{ids()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
                f'{_tgt(e.spid)}<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr>'
                f'<p:to><p:strVal val="visible"/></p:to></p:set>'
                f'<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="{ids()}" dur="{e.dur}"/>{_tgt(e.spid)}'
                f'</p:cBhvr></p:animEffect>'
                f'<p:anim calcmode="lin" valueType="num"><p:cBhvr><p:cTn id="{ids()}" dur="{e.dur}" decel="100000" fill="hold"/>'
                f'{_tgt(e.spid)}<p:attrNameLst><p:attrName>ppt_y</p:attrName></p:attrNameLst></p:cBhvr><p:tavLst>'
                f'<p:tav tm="0"><p:val><p:strVal val="#ppt_y+.04"/></p:val></p:tav>'
                f'<p:tav tm="100000"><p:val><p:strVal val="#ppt_y"/></p:val></p:tav></p:tavLst></p:anim>' + tail)
    if e.kind == "show":  # «Появление» (entr 1): объект скрыт, пока эффект не начался (в том числе во время Morph)
        return (head(1, "entr") +
                f'<p:set><p:cBhvr><p:cTn id="{ids()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
                f'{_tgt(e.spid)}<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr>'
                f'<p:to><p:strVal val="visible"/></p:to></p:set>' + tail)
    if e.kind == "flow":  # путь перемещения с повтором: точка бежит по ломаной и начинает заново
        return (head(0, "path") +
                f'<p:animMotion origin="layout" path="{e.path}" pathEditMode="relative" ptsTypes="">'
                f'<p:cBhvr><p:cTn id="{ids()}" dur="{e.dur}" fill="hold"/>{_tgt(e.spid)}'
                f'<p:attrNameLst><p:attrName>ppt_x</p:attrName><p:attrName>ppt_y</p:attrName></p:attrNameLst></p:cBhvr>'
                f'</p:animMotion>' + tail)
    if e.kind == "pulse":  # «Увеличение/уменьшение» туда и обратно
        k = int(round(e.scale * 100000))
        return (head(6, "emph", ' autoRev="1"') +
                f'<p:animScale><p:cBhvr><p:cTn id="{ids()}" dur="{e.dur}" fill="hold"/>{_tgt(e.spid)}</p:cBhvr>'
                f'<p:by x="{k}" y="{k}"/></p:animScale>' + tail)
    if e.kind == "ripple":  # кольцо растёт и одновременно гаснет; цикл начинается с исходного размера
        k = int(round(e.scale * 100000))
        return (head(6, "emph") +
                f'<p:animScale><p:cBhvr><p:cTn id="{ids()}" dur="{e.dur}" fill="hold"/>{_tgt(e.spid)}</p:cBhvr>'
                f'<p:by x="{k}" y="{k}"/></p:animScale>'
                f'<p:animEffect transition="out" filter="fade"><p:cBhvr><p:cTn id="{ids()}" dur="{e.dur}"/>{_tgt(e.spid)}'
                f'</p:cBhvr></p:animEffect>' + tail)
    if e.kind == "spin":  # вращение на 360° с постоянной скоростью
        return (head(8, "emph") +
                f'<p:animRot by="{-21600000 if e.scale < 0 else 21600000}"><p:cBhvr><p:cTn id="{ids()}" dur="{e.dur}" fill="hold"/>{_tgt(e.spid)}'
                f'<p:attrNameLst><p:attrName>r</p:attrName></p:attrNameLst></p:cBhvr></p:animRot>' + tail)
    if e.kind == "blink":  # «Мерцание»: скрыт первую половину цикла, виден вторую
        return (head(35, "emph") +
                f'<p:anim calcmode="discrete" valueType="str"><p:cBhvr override="childStyle">'
                f'<p:cTn id="{ids()}" dur="{e.dur}" fill="hold"/>{_tgt(e.spid)}'
                f'<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr><p:tavLst>'
                f'<p:tav tm="0"><p:val><p:strVal val="hidden"/></p:val></p:tav>'
                f'<p:tav tm="50000"><p:val><p:strVal val="visible"/></p:val></p:tav></p:tavLst></p:anim>' + tail)
    raise ValueError(f"неизвестный эффект {e.kind}")


def _fx_xml(c: FxCall, ids: _Ids) -> str:
    from .presets import instantiate

    xml, nid, _, _ = instantiate(c.fx, c.spid, c.delay, ids.n + 1)
    ids.n = nid - 1
    return xml.replace(f' xmlns:p="{P_NS}"', "", 1)


def timing_xml(effects: list) -> str:
    """effects — Effect (петли, появление anim_*) и FxCall (библиотека presets), в любом порядке."""
    if not effects:
        return ""
    ids = _Ids(5)
    outer, inner = 3, 4  # id групп; эффекты нумеруются с 5
    body = "".join(_fx_xml(e, ids) if isinstance(e, FxCall) else _effect_xml(e, ids)
                   for e in sorted(effects, key=lambda e: e.delay))
    text_targets = sorted({e.spid for e in effects if e.has_text and (isinstance(e, FxCall) or e.kind == "appear")})
    bld = ("<p:bldLst>" + "".join(f'<p:bldP spid="{s}" grpId="0" animBg="1"/>' for s in text_targets) + "</p:bldLst>"
           if text_targets else "")
    return (f'<p:timing xmlns:p="{P_NS}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">'
            f'<p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
            f'<p:par><p:cTn id="{outer}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/>'
            f'<p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst><p:childTnLst>'
            f'<p:par><p:cTn id="{inner}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
            f'{body}</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn>'
            f'<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
            f'<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>'
            f'</p:seq></p:childTnLst></p:cTn></p:par></p:tnLst>{bld}</p:timing>')


def motion_path(points: list[tuple[float, float]], slide_w: float, slide_h: float) -> str:
    """Ломаная в дюймах слайда -> путь animMotion относительно первой точки, в долях ширины/высоты слайда."""
    x0, y0 = points[0]
    parts = ["M 0 0"] + [f"L {(x - x0) / slide_w:.5f} {(y - y0) / slide_h:.5f}" for x, y in points[1:]]
    return " ".join(parts) + " E"
