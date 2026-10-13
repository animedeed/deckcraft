"""Работа с СУЩЕСТВУЮЩЕЙ презентацией: загрузить .pptx как есть и улучшить общими операциями, не перерисовывая.

Правило из показов пользователя: удачное у автора не заменять своим. Фигуры, граф, документы, композиция
остаются фигура в фигуру; меняются только движение и тайминг, добавляются эффекты и петли.

    from morphkit.existing import Deck
    d = Deck("deck.pptx")
    d.speed(max_morph_ms=900, max_fade_ms=500)          # быстрые переходы
    d.inline_service_slides()                           # служебные автослайды -> рост внутри следующего слайда
    d.text_policy()                                     # изменённый текст гаснет и появляется, а не переливается
    d.retime(first_ms=150)                              # анимации — сразу после перехода
    d.stagger(2, d.names(2, "!!fan"), "entrance_rise_up")  # листы входят по очереди слева направо
    d.loops(15, [Loop("ripple", target="!!wtag", period=1.6, color="F5A300")])
    d.flow_on(16, ["!!we_instr", "!!we_form"], color="F5A300")
    print(d.report()); d.save("deck_v4.pptx")

Номера слайдов — с 1, как в PowerPoint. Операции, удаляющие слайды, сдвигают номера: вызывай их первыми.
"""

from __future__ import annotations

import copy
import io
import math
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.util import Emu

from .anim import Effect, FxCall, timing_xml, transition_xml
from .model import Loop, O
from .presets import Fx, duration_ms, instantiate
from .profile import DEFAULT, DeckProfile
from .theme import SLIDE_H, SLIDE_W, Theme

NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
      "p14": "http://schemas.microsoft.com/office/powerpoint/2010/main",
      "p159": "http://schemas.microsoft.com/office/powerpoint/2015/09/main"}
P = "{%s}" % NS["p"]
A = "{%s}" % NS["a"]
EMU = 914400


@dataclass
class Shape:
    """Фигура существующего слайда: имя, тип, геометрия в дюймах, текст, ссылка на XML."""
    name: str
    spid: int
    kind: str  # sp:roundRect | cxnSp:line | pic | grpSp | sp:custGeom …
    x: float
    y: float
    w: float
    h: float
    rot: float
    flip_h: bool
    flip_v: bool
    text: str
    el: etree._Element

    def as_obj(self) -> O:
        return O(self.name, "rect", self.x, self.y, self.w, self.h, rot=self.rot)

    def center(self) -> tuple[float, float]:
        return self.x + self.w / 2, self.y + self.h / 2

    def endpoints(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Начало и конец соединителя с учётом отражений."""
        x0, x1 = (self.x + self.w, self.x) if self.flip_h else (self.x, self.x + self.w)
        y0, y1 = (self.y + self.h, self.y) if self.flip_v else (self.y, self.y + self.h)
        return (x0, y0), (x1, y1)


class Deck:
    def __init__(self, path: str | Path, theme: Theme | None = None, profile: DeckProfile | None = None):
        self.path = Path(path)
        self.prs = Presentation(str(path))
        from .theme import LAB
        self.theme = theme or LAB  # цвета новых объектов задаются hex (роли — по переданной теме)
        self.profile = profile or DEFAULT
        self.log: list[str] = []
        self._extra: dict[int, list] = {}  # номер слайда -> эффекты/петли, которые надо вписать в шкалу при сохранении
        self._anchor: dict[str, tuple[str, str]] = {}  # имя петли -> (имя фигуры-якоря, "after" | "before")

    # ------------------------------------------------------------------ чтение
    @property
    def slides(self):
        return list(self.prs.slides)

    def _root(self, i: int):
        return self.slides[i - 1]._element

    def shapes(self, i: int) -> list[Shape]:
        out = []
        for el in self._root(i).iter(P + "sp", P + "cxnSp", P + "pic", P + "grpSp", P + "graphicFrame"):
            c = el.find(".//p:cNvPr", NS)
            xfrm = el.find("./p:spPr/a:xfrm", NS)
            if xfrm is None:
                xfrm = el.find("./p:grpSpPr/a:xfrm", NS)
            if c is None or xfrm is None or xfrm.find("a:off", NS) is None:
                continue
            off, ext = xfrm.find("a:off", NS), xfrm.find("a:ext", NS)
            geom = el.find("./p:spPr/a:prstGeom", NS)
            kind = etree.QName(el).localname + (":" + geom.get("prst") if geom is not None else
                                                (":custGeom" if el.find("./p:spPr/a:custGeom", NS) is not None else ""))
            text = "\n".join("".join(t.text or "" for t in p.iter(A + "t")) for p in el.iter(A + "p")).strip() \
                if el.find("./p:txBody", NS) is not None else ""
            out.append(Shape(c.get("name"), int(c.get("id")), kind, int(off.get("x")) / EMU, int(off.get("y")) / EMU,
                             int(ext.get("cx")) / EMU, int(ext.get("cy")) / EMU, int(xfrm.get("rot", 0)) / 60000,
                             xfrm.get("flipH") == "1", xfrm.get("flipV") == "1", text, el))
        return out

    def by_name(self, i: int) -> dict[str, Shape]:
        return {s.name: s for s in self.shapes(i)}

    def names(self, i: int, prefix: str) -> list[str]:
        """Имена с префиксом, упорядоченные слева направо (затем сверху вниз)."""
        sh = [s for s in self.shapes(i) if s.name.startswith(prefix)]
        return [s.name for s in sorted(sh, key=lambda s: (round(s.x, 2), round(s.y, 2)))]

    def transition(self, i: int) -> dict:
        root = self._root(i)
        tr, choice = None, False
        for ac in root.findall("mc:AlternateContent", NS):
            ch = ac.find("mc:Choice", NS)
            if ch is not None and ch.find("p:transition", NS) is not None:
                tr, choice = ch.find("p:transition", NS), True
        if tr is None:
            tr = root.find("p:transition", NS)
        if tr is None:
            return {"kind": "none", "dur": 0, "mode": "byObject", "adv": None}
        kid = tr[0] if len(tr) else None
        kind = etree.QName(kid).localname if kid is not None else "none"
        dur = tr.get("{%s}dur" % NS["p14"])
        spd = {"fast": 500, "med": 750, "slow": 1000}.get(tr.get("spd", "med"), 750)
        return {"kind": kind, "dur": int(dur) if dur else spd, "mode": kid.get("option", "byObject") if kid is not None else
                "byObject", "adv": tr.get("advTm"), "attrs": dict(kid.attrib) if kid is not None else {}}

    def to_slides(self) -> list:
        """Эскиз презентации для предпросмотра движения (morphkit.motion.preview): фигуры → O с цветами из XML.
        Приближение: картинки — серые рамки, группы не разворачиваются, градиенты — первым цветом."""
        from .model import Slide

        from pptx.opc.constants import RELATIONSHIP_TYPE as RT
        scheme = {}
        try:
            th = etree.fromstring(self.prs.slide_masters[0].part.part_related_by(RT.THEME).blob)
            for el in th.find(".//a:clrScheme", NS):
                c = el.find("a:srgbClr", NS)
                c = c.get("val") if c is not None else (el.find("a:sysClr", NS).get("lastClr") if
                                                       el.find("a:sysClr", NS) is not None else None)
                if c:
                    scheme[etree.QName(el).localname] = c.upper()
        except (KeyError, AttributeError, TypeError):
            pass
        for a, b in (("tx1", "dk1"), ("bg1", "lt1"), ("tx2", "dk2"), ("bg2", "lt2")):
            if b in scheme:
                scheme[a] = scheme[b]

        def _rgb(node):
            if node is None:
                return None
            c = node.find(".//a:srgbClr", NS)
            if c is not None:
                return c.get("val").upper()
            c = node.find(".//a:schemeClr", NS)  # оттенки lumMod/lumOff не учитываются — эскиз
            return scheme.get(c.get("val")) if c is not None else None

        kinds = {"ellipse": "oval", "roundRect": "rrect", "line": "line", "straightConnector1": "line",
                 "triangle": "tri", "hexagon": "hex", "chevron": "chevron"}
        out = []
        for i in range(1, len(self.slides) + 1):
            root, objs = self._root(i), []
            bg = _rgb(root.find("./p:cSld/p:bg", NS)) or self.theme.c("bg")
            for s in self.shapes(i):
                if s.kind.startswith("grpSp"):
                    continue
                el, prst = s.el, s.kind.split(":", 1)[1] if ":" in s.kind else ""
                sp = el.find("./p:spPr", NS)
                fill = _rgb(sp.find("a:solidFill", NS)) if sp is not None else None
                if fill is None and sp is not None and sp.find("a:gradFill", NS) is not None:
                    fill = _rgb(sp.find("a:gradFill", NS))
                ln_el = sp.find("a:ln", NS) if sp is not None else None
                ln = _rgb(ln_el.find("a:solidFill", NS)) if ln_el is not None else None
                lw = int(ln_el.get("w", 12700)) / 12700 if ln_el is not None else 0.0
                kind = kinds.get(prst, "rect")
                if s.kind.startswith("pic"):
                    objs.append(O(s.name, "rect", s.x, s.y, s.w, s.h, rot=s.rot, fill="9AA0A6", fa=0.35))
                    continue
                if kind == "line" or s.kind.startswith("cxnSp"):
                    (x0, y0), (x1, y1) = s.endpoints()
                    objs.append(O(s.name, "line", x0, y0, x1 - x0, y1 - y0, ln=ln or "888888", lw=lw or 1.0))
                    continue
                if fill or ln:
                    objs.append(O(s.name, kind, s.x, s.y, s.w, s.h, rot=s.rot, fill=fill, ln=ln, lw=lw if ln else 0))
                if s.text:
                    r = el.find(".//a:rPr", NS)
                    sz = int(r.get("sz")) / 100 if r is not None and r.get("sz") else 18
                    col = _rgb(r) if r is not None else None
                    ppr, body = el.find(".//a:pPr", NS), el.find(".//a:bodyPr", NS)
                    al = {"ctr": "c", "r": "r"}.get(ppr.get("algn") if ppr is not None else None, "l")
                    va = {"ctr": "m", "b": "b"}.get(body.get("anchor") if body is not None else None, "t")
                    objs.append(O(s.name + ("#t" if (fill or ln) else ""), "text", s.x, s.y, s.w, s.h, rot=s.rot,
                                  txt=s.text.split("\n"), sz=sz, col=col or self.theme.c("ink"),
                                  b=r is not None and r.get("b") == "1", al=al, va=va))
            seen: dict[str, int] = {}
            for o in objs:  # одинаковые имена в чужих презентациях — обычное дело; пары Morph они всё равно не образуют
                seen[o.name] = seen.get(o.name, 0) + 1
                if seen[o.name] > 1:
                    o.name = f"{o.name}~{seen[o.name]}"
            tr = self.transition(i)
            out.append(Slide(objs, bg=bg, dur=tr["dur"] or 800, transition="morph" if tr["kind"] == "morph" else "fade",
                             mode=tr.get("mode", "byObject"), title=f"слайд {i}"))
        return out

    # ------------------------------------------------------------------ переходы
    def _set_transition(self, i: int, kind: str, dur: int, mode: str = "byObject", adv: str | None = None,
                        attrs: dict | None = None) -> None:
        root = self._root(i)
        for ac in root.findall("mc:AlternateContent", NS):
            if ac.find(".//p:transition", NS) is not None:
                root.remove(ac)
        for tr in root.findall("p:transition", NS):
            root.remove(tr)
        from .presets import TRANSITIONS
        key = {"morph": "morph", "fade": "fade", "push": "push", "wipe": "wipe"}.get(kind, kind)
        if key not in TRANSITIONS:
            key = next((k for k, (_, el, _) in TRANSITIONS.items() if el == kind), "fade")
        opts = {k: v for k, v in (attrs or {}).items() if k != "option"}
        xml = transition_xml(key, dur, mode, int(adv) if adv else None, opts)
        if not xml:
            return
        anchor = root.find("p:clrMapOvr", NS)
        pos = list(root).index(anchor) + 1 if anchor is not None else 2
        root.insert(pos, etree.fromstring(xml))

    def speed(self, max_morph_ms: int | None = None, max_fade_ms: int | None = None,
              camera: dict[int, int] | None = None) -> None:
        """Ограничить длительности переходов (профиль по умолчанию: Morph 0,9 с, затухание 0,6 с).
        camera — {номер слайда: мс} для полётов камеры (до max_camera_ms профиля)."""
        mm = max_morph_ms or self.profile.max_morph_ms
        mf = max_fade_ms or self.profile.max_fade_ms
        for i in range(2, len(self.slides) + 1):
            t = self.transition(i)
            if t["kind"] == "none":
                continue
            limit = (camera or {}).get(i, mm if t["kind"] == "morph" else mf)
            if t["dur"] > limit or (camera and i in camera):
                self._set_transition(i, t["kind"], min(t["dur"], limit) if not camera or i not in camera else limit,
                                     t["mode"], t["adv"], t["attrs"])
                self.log.append(f"слайд {i}: переход {t['kind']} {t['dur']} → {min(t['dur'], limit)} мс")

    # ------------------------------------------------------------------ имена и пары
    def rename(self, i: int, old: str, new: str, follow: bool = True) -> None:
        """Переименовать фигуру на слайде i (и на следующих подряд слайдах, где та же пара продолжается)."""
        k = i
        while k <= len(self.slides):
            sh = self.by_name(k).get(old)
            if sh is None:
                break
            sh.el.find(".//p:cNvPr", NS).set("name", new)
            if not follow:
                break
            k += 1

    def break_pairs(self, i: int, names: list[str], tag: str = "") -> list[str]:
        """Разорвать пары Morph с предыдущим слайдом: объекты слайда i и их продолжения получают новые имена."""
        out = []
        prev = self.by_name(i - 1) if i > 1 else {}
        for n in names:
            if n in prev:
                new = f"{n}~{tag or i}"
                self.rename(i, n, new)
                out.append(new)
            else:
                out.append(n)
        return out

    def split_text(self) -> int:
        """Фигура с текстом И видимой подложкой (карточка, узел) делится на две: подложка сохраняет имя и
        морфится (едет, меняет размер), текст — отдельный прозрачный слой «имя~txt» поверх. Тогда смена текста
        не рвёт движение карточки. Делается для всех слайдов (имена слоёв совпадают — пары сохраняются)."""
        n = 0
        for i in range(1, len(self.slides) + 1):
            root = self._root(i)
            next_id = max(s.spid for s in self.shapes(i)) + 1
            for sh in self.shapes(i):
                if not (sh.name.startswith("!!") and sh.text and sh.kind.startswith("sp") and _has_box(sh.el)):
                    continue
                txt = copy.deepcopy(sh.el)
                c = txt.find(".//p:cNvPr", NS)
                c.set("name", sh.name + "~txt")
                c.set("id", str(next_id))
                next_id += 1
                sp_pr = txt.find("p:spPr", NS)
                for tag in ("solidFill", "gradFill", "noFill", "pattFill", "blipFill", "ln", "effectLst"):
                    for el in sp_pr.findall(A + tag):
                        sp_pr.remove(el)
                geom = sp_pr.find(A + "prstGeom")
                if geom is None:
                    geom = sp_pr.find(A + "custGeom")
                nf = etree.Element(A + "noFill")
                (geom.addnext(nf) if geom is not None else sp_pr.append(nf))
                ln = etree.SubElement(sp_pr, A + "ln")
                etree.SubElement(ln, A + "noFill")
                for t in sh.el.iter(A + "t"):  # в подложке текста больше нет
                    t.text = ""
                sh.el.addnext(txt)
                n += 1
        if n:
            self.log.append(f"текст отделён от подложки у {n} фигур")
        return n

    def text_policy(self) -> None:
        """Изменённый текст не переливается: если у пары Morph другой текст, пара разрывается (старый гаснет,
        новый проявляется). Подложки карточек сначала отделяются от текста (split_text) — они продолжают ехать."""
        self.split_text()
        for i in range(2, len(self.slides) + 1):
            if self.transition(i)["kind"] != "morph":
                continue
            prev = self.by_name(i - 1)
            for s in self.shapes(i):
                p = prev.get(s.name)
                if p is not None and s.name.startswith("!!") and s.text and p.text and s.text != p.text:
                    self.rename(i, s.name, f"{s.name.split('@')[0]}@{i}")
                    self.log.append(f"слайд {i}: «{s.name}» — текст изменился, перелив заменён затуханием")

    def fix_char_modes(self) -> None:
        """Режим «по словам/по буквам» при нескольких текстах на слайде -> «по объектам» (правило профиля)."""
        for i in range(2, len(self.slides) + 1):
            t = self.transition(i)
            texts = [s for s in self.shapes(i) if s.text]
            if t["mode"] in ("byWord", "byChar") and len(texts) > 1 and not self.profile.allow_char_modes:
                self._set_transition(i, t["kind"], t["dur"], "byObject", t["adv"],
                                     {k: v for k, v in t["attrs"].items() if k != "option"})
                self.log.append(f"слайд {i}: режим {t['mode']} при {len(texts)} текстах → byObject")

    # ------------------------------------------------------------------ служебные слайды
    def inline_service_slides(self, grow_ms: int = 600, stagger_ms: int = 60) -> None:
        """Служебный автослайд S (нулевое состояние) перед T удаляется, а рост переносится внутрь T эффектами:
        дуги — вход «Колесо», полосы — «Возникновение» по направлению роста, переехавшие объекты — путь от
        прежнего места, остальное изменившееся — проявление. Навигация назад снова работает."""
        i = 1
        while i < len(self.slides):
            t = self.transition(i)
            if not t["adv"] or i == 1:
                i += 1
                continue
            S, T = self.by_name(i), self.by_name(i + 1)
            fx = []
            delay = 0.15
            for name, sh in T.items():
                z = S.get(name)
                if z is None or not name.startswith("!!"):
                    continue
                d_pos = abs(sh.x - z.x) + abs(sh.y - z.y)
                d_size = abs(sh.w - z.w) + abs(sh.h - z.h)
                adj_changed = sh.kind.endswith("blockArc") and _adj(sh.el) != _adj(z.el)
                if not (d_pos > 0.02 or d_size > 0.02 or adj_changed or (sh.text != z.text)):
                    continue
                if adj_changed:
                    _arc_unrotate(sh)
                    fx.append(Fx("entrance_wheel", name, start="at", delay=delay, dur=0.9, options={"amount": "1"}))
                elif sh.kind.startswith("cxnSp") or (z.w < 0.05 and sh.w > 0.1 and abs(sh.h - z.h) < 0.05):
                    direction = "left" if not sh.flip_h else "right"
                    fx.append(Fx("entrance_wipe", name, start="at", delay=delay, dur=grow_ms / 1000,
                                 options={"direction": direction}))
                elif z.h < 0.05 and sh.h > 0.1 and abs(sh.w - z.w) < 0.05:
                    fx.append(Fx("entrance_wipe", name, start="at", delay=delay, dur=grow_ms / 1000,
                                 options={"direction": "down" if abs(sh.y + sh.h - (z.y + z.h)) < 0.05 else "up"}))
                elif d_pos > 0.05:
                    dx, dy = (z.x + z.w / 2) - (sh.x + sh.w / 2), (z.y + z.h / 2) - (sh.y + sh.h / 2)
                    path = f"M {dx / SLIDE_W:.5f} {dy / SLIDE_H:.5f} L 0 0 E"
                    fx.append(Fx("entrance_appear", name, start="at", delay=delay))
                    fx.append(Fx("path_custom", name, start="with", dur=grow_ms / 1000, path=path))
                else:
                    fx.append(Fx("entrance_fade", name, start="at", delay=delay, dur=0.4))
                delay += stagger_ms / 1000
            prev_name = self.by_name(i - 1) if i > 1 else {}
            renamed = {}
            for f in fx:  # у растущих объектов не должно быть пары со слайдом перед S (иначе вход «проявит» дважды)
                if f.target in prev_name and f.target not in renamed:
                    renamed[f.target] = f"{f.target}~g{i}"
                    self.rename(i + 1, f.target, renamed[f.target])
                f.target = renamed.get(f.target, f.target)
            self._extra.setdefault(i + 1, []).extend(fx)
            self._delete_slide(i)
            self._extra = {(k - 1 if k > i else k): v for k, v in self._extra.items()}
            self.log.append(f"служебный слайд {i} удалён, рост ({len(fx)} эффектов) перенесён в следующий")

    def _delete_slide(self, i: int) -> None:
        lst = self.prs.slides._sldIdLst
        sid = list(lst)[i - 1]
        self.prs.part.drop_rel(sid.get("{%s}id" % NS["r"]))
        lst.remove(sid)

    # ------------------------------------------------------------------ эффекты и петли
    def fx(self, i: int, effects: list[Fx]) -> None:
        self._extra.setdefault(i, []).extend(effects)

    def stagger(self, i: int, names: list, effect: str = "entrance_rise_up", delay: float = 0.15,
                step: float = 0.06, dur: float | None = 0.45, options: dict | None = None) -> None:
        """Вход объектов по очереди (порядок — как в names, обычно слева направо). Элемент names — имя или
        список имён (группа входит вместе: строка таблицы, карточка с подписью). «имя» и «имя~txt» — всегда
        одна группа. Пары с прошлым слайдом рвутся."""
        groups: list[list[str]] = []
        for item in names:
            g = self.break_pairs(i, [item] if isinstance(item, str) else list(item), tag=f"s{i}")
            base = g[0].split("~txt")[0]
            if isinstance(item, str) and groups and groups[-1][0].split("~txt")[0] == base:
                groups[-1].extend(g)
            else:
                groups.append(g)
        self.fx(i, [Fx(effect, n, start="at", delay=delay + k * step, dur=dur, options=dict(options or {}))
                    for k, g in enumerate(groups) for n in g])

    def loops(self, i: int, loops: list[Loop]) -> None:
        self._extra.setdefault(i, []).extend(loops)

    def flow_on(self, i: int, connectors: list[str], n: int = 3, period: float = 1.8, color: str = "F5A300",
                size: float = 0.14, reverse: bool = False, name: str = "sig", stop_at_shapes: bool = True,
                margin: float = 0.08, source: tuple[float, float] | None = None) -> None:
        """Сигнал строго по существующим соединителям (геометрия с учётом отражений) — одна система петель.
        Точки лежат сразу над своей линией и ПОД карточками; путь обрывается на краю фигуры, в которую входит
        линия (stop_at_shapes), — точки не пролетают поверх текста."""
        sh = self.by_name(i)
        boxes = [s for s in sh.values() if s.kind.startswith("sp") and not s.kind.endswith(("ellipse", "line"))
                 and s.w > 0.6 and s.h > 0.3]
        if source is None and len(connectors) > 1:
            source = common_point([sh[c] for c in connectors])
        lps = []
        for c in connectors:
            s = sh[c]
            a, b = s.endpoints()
            if source is not None:  # сигнал идёт от узла-источника, как бы ни был нарисован соединитель
                if math.dist(b, source) < math.dist(a, source):
                    a, b = b, a
            elif reverse:
                a, b = b, a
            if stop_at_shapes:
                b = _clip_to_boxes(a, b, boxes, margin)
                a = _clip_to_boxes(b, a, boxes, margin)
            nm = f"{name}_{len(lps)}"
            lps.append(Loop("flow", points=[a, b], n=n, period=period, color=color, size=size, name=nm))
            self._anchor[nm] = (c, "after")
        self.loops(i, lps)

    def ripple(self, i: int, target: str, color: str = "F5A300", period: float = 1.6, scale: float = 1.9,
               name: str = "rip") -> None:
        """Круги на воде вокруг фигуры (кольцо лежит под ней)."""
        self._anchor[name] = (target, "before")
        self.loops(i, [Loop("ripple", target=target, period=period, scale=scale, color=color, name=name)])

    def remove(self, slides: list[int], names: list[str]) -> None:
        """Удалить фигуры (и их текстовые слои ~txt) на перечисленных слайдах."""
        for i in slides:
            for s in self.shapes(i):
                if s.name in names or s.name.split("~")[0] in names:
                    s.el.getparent().remove(s.el)
            self.log.append(f"слайд {i}: удалено {', '.join(names)}")

    def hide_zero_lines(self, min_len: float = 0.03, dots: bool = False) -> int:
        """Фигура нулевого размера (её «вырастит» Morph на следующем слайде) видна на экране как точка или
        чёрточка: у линии — точка, у листа/столбика нулевой ширины — контур-палочка. Делаем её прозрачной:
        Morph проявит её одновременно с ростом. Фигуры 0 × 0 (схлопнувшиеся точки поля) по умолчанию не
        трогаются: их маленький «остаток» на месте — часть приёма «99 → 15» (dots=True — скрыть и их)."""
        n = 0
        for i in range(1, len(self.slides) + 1):
            for s in self.shapes(i):
                if s.kind.startswith("cxnSp"):
                    if s.w >= min_len or s.h >= min_len:
                        continue
                elif min(s.w, s.h) >= min_len or s.text:
                    continue
                elif max(s.w, s.h) < min_len and not dots:
                    continue
                clrs = [c for path in ("./p:spPr/a:solidFill/a:srgbClr", "./p:spPr/a:solidFill/a:schemeClr",
                                       "./p:spPr/a:ln/a:solidFill/a:srgbClr", "./p:spPr/a:ln/a:solidFill/a:schemeClr")
                        for c in s.el.findall(path, NS)]
                for clr in clrs:
                    for a in clr.findall(A + "alpha"):
                        clr.remove(a)
                    etree.SubElement(clr, A + "alpha").set("val", "0")
                n += bool(clrs)
        self.log.append(f"скрыто фигур нулевого размера: {n}")
        return n

    def regroup(self, i: int, prefix: str, cols: int, step: float | None = None,
                step_y: float | None = None) -> None:
        """Оставшиеся (ненулевые) фигуры с префиксом собираются в плотную сетку от верхнего левого угла поля
        (например, 15 точек из 99 после фильтра). Morph перевезёт их на новые места."""
        sh = [s for s in self.shapes(i) if s.name.startswith(prefix)]
        live = sorted([s for s in sh if s.w > 0.02], key=lambda s: (round(s.y, 2), s.x))
        if not live:
            return
        x0, y0 = min(s.x for s in sh), min(s.y for s in sh)
        xs = sorted({round(s.x, 3) for s in live})
        step = step or (xs[1] - xs[0] if len(xs) > 1 else live[0].w * 1.6)
        step_y = step_y or step
        for k, s in enumerate(live):
            off = s.el.find("./p:spPr/a:xfrm/a:off", NS)
            off.set("x", str(int((x0 + (k % cols) * step) * EMU)))
            off.set("y", str(int((y0 + (k // cols) * step_y) * EMU)))
        self.log.append(f"слайд {i}: {len(live)} фигур {prefix}* собраны в сетку по {cols}")

    def set_line(self, i: int, name: str, p1: tuple[float, float], p2: tuple[float, float]) -> None:
        """Соединитель name на слайде i ведётся из p1 в p2 (дюймы; отражения выставляются сами)."""
        el = self.by_name(i)[name].el
        xfrm = el.find("./p:spPr/a:xfrm", NS)
        for a in ("rot", "flipH", "flipV"):
            xfrm.attrib.pop(a, None)
        if p2[0] < p1[0]:
            xfrm.set("flipH", "1")
        if p2[1] < p1[1]:
            xfrm.set("flipV", "1")
        xfrm.find("a:off", NS).set("x", str(int(min(p1[0], p2[0]) * EMU)))
        xfrm.find("a:off", NS).set("y", str(int(min(p1[1], p2[1]) * EMU)))
        xfrm.find("a:ext", NS).set("cx", str(int(abs(p2[0] - p1[0]) * EMU)))
        xfrm.find("a:ext", NS).set("cy", str(int(abs(p2[1] - p1[1]) * EMU)))
        for tag in ("stCxn", "endCxn"):  # иначе PowerPoint перепроложит линию по старым точкам привязки
            for c in el.iter(A + tag):
                c.getparent().remove(c)

    def rewire(self, edges: dict[str, tuple[str, str]], slides: list[int] | None = None, gap: float = 0.0) -> int:
        """Ребро name соединяет фигуры (a, b) на каждом слайде, где есть все три: от края a (карточки) до центра
        b (точки; если b крупная — до её края). Геометрия считается заново на каждом слайде, поэтому камера
        (масштаб и сдвиг мира) и Morph между слайдами сохраняются."""
        n = 0
        for i in slides or range(1, len(self.slides) + 1):
            sh = self.by_name(i)
            for e, (a, b) in edges.items():
                if not all(k in sh for k in (e, a, b)):
                    continue
                A_, B_ = sh[a], sh[b]
                ca, cb = A_.center(), B_.center()
                p1 = _border_point(A_, cb, gap)
                p2 = cb if max(B_.w, B_.h) < 0.25 else _border_point(B_, ca, gap)
                self.set_line(i, e, p1, p2)
                n += 1
        self.log.append(f"переподключено рёбер (по всем слайдам): {n}")
        return n

    def move(self, i: int, name: str, x: float | None = None, y: float | None = None) -> None:
        """Переставить фигуру (и её текстовый слой ~txt) на слайде i."""
        sh = self.by_name(i)
        for n in (name, f"{name}~txt"):
            if n in sh:
                off = sh[n].el.find("./p:spPr/a:xfrm/a:off", NS)
                if x is not None:
                    off.set("x", str(int(x * EMU)))
                if y is not None:
                    off.set("y", str(int(y * EMU)))

    def line_style_like(self, i: int, names: list[str], like: etree._Element) -> None:
        """Стиль линии (a:ln целиком) у соединителей names — как у образца like (копия элемента a:ln)."""
        sh = self.by_name(i)
        for n in names:
            if n in sh:
                sp = sh[n].el.find("./p:spPr", NS)
                old = sp.find("a:ln", NS)
                new = copy.deepcopy(like)
                (old.addprevious(new), sp.remove(old)) if old is not None else sp.append(new)

    def add(self, i: int, objs: list[O], before: str | None = None) -> None:
        """Добавить новые объекты движка (O) на слайд i — сверху или под фигуру before. Имена «!!…» на соседних
        слайдах образуют пары Morph, как в обычной сборке."""
        from .build import add_object
        slide = self.slides[i - 1]
        ref = self.by_name(i)[before].el if before else None
        for o in sorted(objs, key=lambda o: o.z):
            sh = add_object(slide, o, self.theme)
            if ref is not None:
                ref.addprevious(sh._element)
        self.log.append(f"слайд {i}: добавлено объектов {len(objs)}")

    def stack_under(self, i: int, groups: list[list[str]]) -> None:
        """Порядок слоёв: каждая следующая группа уходит ПОД предыдущую (карточки «выезжают из-под» соседа)."""
        for prev, cur in zip(groups, groups[1:]):
            sh = self.by_name(i)
            first = min((sh[n].el for n in prev if n in sh), key=lambda el: list(el.getparent()).index(el))
            for n in cur:
                if n in sh:
                    first.addprevious(sh[n].el)

    # ------------------------------------------------------------------ шкала времени
    def retime(self, first_ms: int = 150, step_ms: int | None = None) -> None:
        """Анимации каждого слайда стартуют через first_ms после перехода (шкала стартует после перехода).
        Относительные интервалы сохраняются (или выравниваются на step_ms)."""
        for i in range(1, len(self.slides) + 1):
            effects = self._collect(i)
            if not effects:
                continue
            t0 = min(d for d, _ in effects)
            order = sorted(effects, key=lambda e: e[0])
            for k, (d, node) in enumerate(order):
                new = first_ms + (k * step_ms if step_ms is not None else d - t0)
                node.set("__delay", str(new))
            self._rebuild_timing(i, [(int(n.get("__delay")), n) for _, n in effects])
            self.log.append(f"слайд {i}: {len(effects)} эффектов, старт {t0} → {first_ms} мс")

    def shift(self, i: int, ms: int) -> None:
        """Сдвинуть уже существующие анимации слайда на ms (освободить начало шкалы под новый вход)."""
        effects = self._collect(i)
        if effects:
            self._rebuild_timing(i, [(d + ms, n) for d, n in effects])
            self.log.append(f"слайд {i}: {len(effects)} эффектов сдвинуты на {ms} мс")

    def _collect(self, i: int) -> list[tuple[int, etree._Element]]:
        """Узлы эффектов (cTn с presetClass) и их полные задержки от начала шкалы (только автостарт с начала слайда)."""
        root = self._root(i)
        timing = root.find("p:timing", NS)
        if timing is None:
            return []
        out = []
        for ctn in timing.iter(P + "cTn"):
            if ctn.get("presetClass") is None:
                continue
            delay, node = 0, ctn
            while node is not None and etree.QName(node).localname != "timing":
                if etree.QName(node).localname == "cTn":
                    for c in node.findall("p:stCondLst/p:cond", NS):
                        if (c.get("delay") or "").isdigit() and c.get("evt") is None:
                            delay += int(c.get("delay"))
                node = node.getparent()
            out.append((delay, ctn))
        return out

    def _rebuild_timing(self, i: int, effects: list[tuple[int, etree._Element]], extra_xml: str = "",
                        extra_bld: set[int] | None = None) -> None:
        """Шкала заново в формате движка: одна группа «с предыдущим» от начала слайда, эффекты с задержками."""
        root = self._root(i)
        old = root.find("p:timing", NS)
        bld = set(extra_bld or set())
        if old is not None:
            for b in old.iter(P + "bldP"):
                bld.add(int(b.get("spid")))
        body = []
        for d, node in sorted(effects, key=lambda e: e[0]):
            n = copy.deepcopy(node)
            if "__delay" in n.attrib:
                del n.attrib["__delay"]
            n.set("nodeType", "withEffect")
            st = n.find("p:stCondLst", NS)
            for c in list(st):
                st.remove(c)
            etree.SubElement(st, P + "cond").set("delay", str(d))
            par = etree.Element(P + "par")
            par.append(n)
            body.append(etree.tostring(par, encoding="unicode"))
        P_URI = NS["p"]
        inner = "".join(body) + extra_xml
        bld_xml = ("<p:bldLst>" + "".join(f'<p:bldP spid="{s}" grpId="0" animBg="1"/>' for s in sorted(bld)) +
                   "</p:bldLst>") if bld else ""
        xml = (f'<p:timing xmlns:p="{P_URI}" xmlns:a="{NS["a"]}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" '
               f'restart="never" nodeType="tmRoot"><p:childTnLst><p:seq concurrent="1" nextAc="seek"><p:cTn id="2" '
               f'dur="indefinite" nodeType="mainSeq"><p:childTnLst><p:par><p:cTn id="3" fill="hold"><p:stCondLst>'
               f'<p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst>'
               f'<p:childTnLst><p:par><p:cTn id="4" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst>'
               f'<p:childTnLst>{inner}</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par></p:childTnLst>'
               f'</p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>'
               f'</p:prevCondLst><p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>'
               f'</p:nextCondLst></p:seq></p:childTnLst></p:cTn></p:par></p:tnLst>{bld_xml}</p:timing>')
        new = etree.fromstring(xml)
        n = 1
        for ctn in new.iter(P + "cTn"):  # сквозная нумерация id
            ctn.set("id", str(n))
            n += 1
        for tn in new.iter(P + "tn"):
            tn.set("val", "2")
        if old is not None:
            root.replace(old, new)
        else:
            ext = root.find("p:extLst", NS)
            if ext is not None:
                ext.addprevious(new)
            else:
                root.append(new)

    def _apply_extra(self) -> None:
        from .build import add_object, expand_loops, loop_effects
        from .presets import Fx as _Fx
        for i, items in sorted(self._extra.items()):
            slide = self.slides[i - 1]
            fxs = [x for x in items if isinstance(x, _Fx)]
            lps = [x for x in items if isinstance(x, Loop)]
            spids = {s.name: s.spid for s in self.shapes(i)}
            effects: list = []
            if lps:
                proxies = [s.as_obj() for s in self.shapes(i)]
                from .model import Slide as _Slide
                extra, plans = expand_loops(_Slide(proxies, loops=lps), proxies, self.theme)
                by = self.by_name(i)
                for o in sorted(extra, key=lambda o: o.z):
                    sh = add_object(slide, o, self.theme)
                    spids[o.name] = sh.shape_id
                    lp_name = next((lp.name for lp in lps if o.name.startswith(f"loop_{lp.name}_")), None)
                    anchor = self._anchor.get(lp_name)
                    if anchor and anchor[0] in by:
                        target = by[anchor[0]].el
                        (target.addnext if anchor[1] == "after" else target.addprevious)(sh._element)
                effects += loop_effects(plans, spids, 150)
            texts = {s.spid for s in self.shapes(i) if s.text}
            for f in fxs:
                if f.target not in spids:
                    raise KeyError(f"слайд {i}: нет объекта {f.target}")
                effects.append(FxCall(f, spids[f.target], 0, spids[f.target] in texts))
            # время: Fx по своим правилам старта, петли — с их задержками
            t_prev, t_end, calls = 0, 0, []
            for e in effects:
                if isinstance(e, FxCall):
                    f = e.fx
                    lag = int(round(f.delay * 1000))
                    start = {"with": t_prev + lag, "after": t_end + lag, "at": lag}[f.start]
                    e.delay = start
                    if not f.repeat:
                        t_end = max(t_end, start + duration_ms(f))
                    t_prev = start
                calls.append(e)
            tm = timing_xml(calls)
            inner = tm[tm.index("<p:childTnLst>", tm.index('nodeType="mainSeq"')):]
            inner = re.search(r'<p:cTn id="4" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
                              r'(.*)</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par></p:childTnLst>', tm, re.S)
            body = inner.group(1) if inner else ""
            body = body.replace(f' xmlns:p="{NS["p"]}"', "")
            self._rebuild_timing(i, self._collect(i), extra_xml=body,
                                 extra_bld={e.spid for e in calls if isinstance(e, FxCall) and e.has_text})
        self._extra = {}

    # ------------------------------------------------------------------ сохранение и отчёт
    def save(self, out: str | Path) -> Path:
        self._apply_extra()
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        self.prs.save(str(out))
        return out

    def report(self) -> list[str]:
        """Проверка по профилю на готовой презентации: автослайды, длительности, режимы по буквам, дубли текста."""
        issues = []
        for i in range(1, len(self.slides) + 1):
            t = self.transition(i)
            if t["adv"] and not self.profile.allow_auto:
                issues.append(f"[error] слайд {i}: служебный автослайд")
            if i > 1 and t["kind"] == "morph" and t["dur"] > self.profile.max_camera_ms:
                issues.append(f"[warn ] слайд {i}: Morph {t['dur']} мс")
            texts = [s for s in self.shapes(i) if s.text]
            if t["mode"] in ("byWord", "byChar") and len(texts) > 1 and not self.profile.allow_char_modes:
                issues.append(f"[error] слайд {i}: режим {t['mode']} при {len(texts)} текстах")
        return issues


def _has_box(el) -> bool:
    """Видна ли у фигуры подложка (заливка или контур), а не только текст."""
    sp_pr = el.find("p:spPr", NS)
    if sp_pr is None:
        return False
    if sp_pr.find(A + "solidFill") is not None or sp_pr.find(A + "gradFill") is not None:
        return True
    ln = sp_pr.find(A + "ln")
    return ln is not None and ln.find(A + "noFill") is None and (ln.find(A + "solidFill") is not None)


def _adj(el) -> dict:
    return {g.get("name"): g.get("fmla") for g in el.iter(A + "gd")}


def _arc_unrotate(sh: Shape) -> None:
    """Дуга blockArc с поворотом -> та же дуга без поворота (углы регуляторов + поворот): эффект «Колесо»
    начинается на 12 часах и идёт по часовой стрелке вместе с дугой."""
    if not sh.rot:
        return
    rot = int(round(sh.rot * 60000))
    for g in sh.el.iter(A + "gd"):
        if g.get("name") in ("adj1", "adj2"):
            v = int(g.get("fmla").split()[1])
            g.set("fmla", f"val {(v + rot) % 21600000}")
    sh.el.find("./p:spPr/a:xfrm", NS).attrib.pop("rot", None)


def _border_point(s: Shape, toward: tuple[float, float], gap: float = 0.0) -> tuple[float, float]:
    """Точка на границе прямоугольника фигуры s по лучу из её центра к точке toward."""
    cx, cy = s.center()
    dx, dy = toward[0] - cx, toward[1] - cy
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return cx, cy
    t = min((s.w / 2) / abs(dx) if dx else math.inf, (s.h / 2) / abs(dy) if dy else math.inf)
    L = math.hypot(dx, dy)
    t += gap / L
    return cx + dx * t, cy + dy * t


def plan_edges(sources: dict[str, tuple[float, float]], targets: dict[str, tuple[float, float]],
               group_of, per_source: int = 2, improve: bool = True,
               obstacles: dict[str, tuple[float, float, float, float]] | None = None) -> dict[str, list[str]]:
    """Распутать связи: каждому источнику — per_source целей из РАЗНЫХ ближайших групп (узлов), каждая цель —
    не больше одного ребра, суммарная длина минимальна (паросочетание минимальной длины почти не даёт
    пересечений). Возвращает {источник: [цели]}."""
    from scipy.optimize import linear_sum_assignment
    import numpy as np
    groups: dict = {}
    for t, p in targets.items():
        groups.setdefault(group_of(t), []).append(p)
    centroid = {g: (sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps)) for g, ps in groups.items()}
    rows = []
    for s_, p in sources.items():
        near = sorted(centroid, key=lambda g: math.dist(p, centroid[g]))[:per_source]
        rows += [(s_, g) for g in near]
    tnames = list(targets)
    cost = np.array([[math.dist(sources[s_], targets[t]) + (0 if group_of(t) == g else 50)
                      for t in tnames] for s_, g in rows])
    r, c = linear_sum_assignment(cost)
    out: dict[str, list[str]] = {s_: [] for s_ in sources}
    for ri, ci in zip(r, c):
        out[rows[ri][0]].append(tnames[ci])
    if improve:
        out = _untangle(out, sources, targets, group_of, obstacles or {})
    return out


def plan_edges_clean(sources, targets, group_of, max_per_source: int = 2,
                     obstacles: dict | None = None, fixed: list | None = None,
                     reserved: set | None = None) -> dict[str, list[str]]:
    """Связи БЕЗ пересечений: сначала каждый источник — к ближайшему узлу (паросочетание минимальной длины),
    затем вторые связи к соседнему узлу, но только те, что ничего не пересекают и не идут под карточками
    (от коротких к длинным). У части источников останется одна связь — лишние рёбра презентации удаляются.
    fixed — уже проложенные отрезки, которые тоже нельзя пересекать; reserved — занятые цели."""
    obstacles = obstacles or {}
    targets = {t: q for t, q in targets.items() if t not in (reserved or set())}
    plan = plan_edges(sources, targets, group_of, per_source=1, obstacles=obstacles)
    used = {t for ts in plan.values() for t in ts}
    geo = [(sources[s_], targets[t]) for s_, ts in plan.items() for t in ts] + list(fixed or [])
    cent: dict = {}
    for t, q in targets.items():
        cent.setdefault(group_of(t), []).append(q)
    cent = {g: (sum(q[0] for q in qs) / len(qs), sum(q[1] for q in qs) / len(qs)) for g, qs in cent.items()}
    cands = []
    for s_, p in sources.items():
        have = {group_of(t) for t in plan[s_]}
        near = set(sorted(cent, key=lambda g: math.dist(p, cent[g]))[:max_per_source])  # только соседние узлы
        for t, q in targets.items():
            if t not in used and group_of(t) not in have and group_of(t) in near:
                cands.append((math.dist(p, q), s_, t))
    for _, s_, t in sorted(cands):
        if len(plan[s_]) >= max_per_source or t in used or group_of(t) in {group_of(x) for x in plan[s_]}:
            continue
        seg = (sources[s_], targets[t])
        if crossings(geo + [seg]) > crossings(geo):
            continue
        if any(o != s_ and _seg_hits_box(seg[0], seg[1], box) for o, box in obstacles.items()):
            continue
        plan[s_].append(t)
        used.add(t)
        geo.append(seg)
    return plan


def _untangle(plan, sources, targets, group_of, obstacles, rounds: int = 30):
    """Локальный поиск: обмен целей между двумя рёбрами или замена цели свободной точкой того же узла, пока
    падает штраф = 10·пересечения + 10·проходы под чужими карточками + длина."""
    def segs(pl):
        return [(s_, t) for s_, ts in pl.items() for t in ts]

    def cost(pl):
        E = segs(pl)
        geo = [(sources[s_], targets[t]) for s_, t in E]
        under = sum(1 for (s_, t), g in zip(E, geo) for o, box in obstacles.items()
                    if o != s_ and _seg_hits_box(g[0], g[1], box))
        return 10 * crossings(geo) + 10 * under + sum(math.dist(a, b) for a, b in geo)

    def ok(pl):
        return all(len({group_of(t) for t in ts}) == len(ts) for ts in pl.values())

    best = cost(plan)
    for _ in range(rounds):
        improved = False
        E = segs(plan)
        used = {t for _, t in E}
        for k in range(len(E)):
            for cand in [("swap", j) for j in range(k + 1, len(E))] + \
                        [("free", t) for t in targets if t not in used and group_of(t) == group_of(E[k][1])]:
                pl = {s_: list(ts) for s_, ts in plan.items()}
                s1, t1 = E[k]
                if cand[0] == "swap":
                    s2, t2 = E[cand[1]]
                    if s1 == s2:
                        continue
                    pl[s1][pl[s1].index(t1)] = t2
                    pl[s2][pl[s2].index(t2)] = t1
                else:
                    pl[s1][pl[s1].index(t1)] = cand[1]
                if not ok(pl):
                    continue
                c = cost(pl)
                if c < best - 1e-6:
                    plan, best, improved = pl, c, True
                    break
            if improved:
                break
        if not improved:
            break
    return plan


def _seg_hits_box(a, b, box) -> bool:
    x, y, w, h = box
    for k in range(1, 20):
        t = k / 20
        px, py = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        if x < px < x + w and y < py < y + h:
            return True
    return False


def route_extra(sources: dict[str, tuple[float, float]], targets: dict[str, tuple[float, float]],
                existing: list, obstacles: dict | None = None) -> dict[str, str]:
    """Дополнительные связи поверх готового графа: каждому источнику — ближайшая свободная цель, при которой
    связь ничего не пересекает и не идёт под карточками; если такой нет — ближайшая с наименьшим числом
    пересечений. Возвращает {источник: цель}."""
    obstacles = obstacles or {}
    segs, used, out = list(existing), set(), {}
    base = crossings(segs)
    for s_, p in sorted(sources.items(), key=lambda kv: min(math.dist(kv[1], q) for q in targets.values())):
        best = None
        for t, q in sorted(targets.items(), key=lambda kv: math.dist(p, kv[1])):
            if t in used:
                continue
            seg = (p, q)
            pen = crossings(segs + [seg]) - base
            pen += sum(1 for o, box in obstacles.items() if o != s_ and _seg_hits_box(p, q, box))
            if best is None or pen < best[0]:
                best = (pen, t, seg)
            if pen == 0:
                break
        _, t, seg = best
        out[s_] = t
        used.add(t)
        segs.append(seg)
        base = crossings(segs)
    return out


def crossings(segs: list[tuple[tuple[float, float], tuple[float, float]]]) -> int:
    """Число пар пересекающихся отрезков (общие концы не считаются)."""
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])
    n = 0
    for k in range(len(segs)):
        for j in range(k + 1, len(segs)):
            (a, b), (c, d) = segs[k], segs[j]
            if min(math.dist(a, c), math.dist(a, d), math.dist(b, c), math.dist(b, d)) < 1e-3:
                continue
            if ccw(a, b, c) * ccw(a, b, d) < 0 and ccw(c, d, a) * ccw(c, d, b) < 0:
                n += 1
    return n


def common_point(shapes: list[Shape]) -> tuple[float, float]:
    """Общий конец нескольких соединителей (узел-источник)."""
    ends = [s.endpoints() for s in shapes]
    cands = [p for pair in ends for p in pair]
    return min(cands, key=lambda p: sum(min(math.dist(p, q) for q in pair) for pair in ends))


def _clip_to_boxes(a: tuple[float, float], b: tuple[float, float], boxes: list[Shape], margin: float):
    """Если конец b внутри фигуры-карточки, обрезать отрезок a→b на её границе (минус margin)."""
    for s in boxes:
        if s.x < b[0] < s.x + s.w and s.y < b[1] < s.y + s.h and not (s.x < a[0] < s.x + s.w and s.y < a[1] < s.y + s.h):
            lo, hi = 0.0, 1.0
            for _ in range(40):  # двоичный поиск точки выхода из прямоугольника
                mid = (lo + hi) / 2
                px, py = a[0] + (b[0] - a[0]) * mid, a[1] + (b[1] - a[1]) * mid
                if s.x < px < s.x + s.w and s.y < py < s.y + s.h:
                    hi = mid
                else:
                    lo = mid
            L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
            t = max(lo - margin / L, 0.0)
            return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
    return b
