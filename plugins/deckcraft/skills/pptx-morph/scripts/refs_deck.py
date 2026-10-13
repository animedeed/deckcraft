"""Устройство колоды-референса: переходы, автопереходы, объекты, пары Morph и шкала анимаций по слайдам.

    python refs_deck.py DECK.pptx [--slides 3-7] [--objects] [--json OUT.json]

Без --objects печатает сводку слайда (переход, пары с соседями, эффекты); с --objects — ещё и каждый объект
(имя, тип, x, y, w, h в дюймах, поворот, 3D, заливка). Протокол — pptx-design/references/references-protocol.md.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

from lxml import etree

NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
      "p14": "http://schemas.microsoft.com/office/powerpoint/2010/main",
      "p159": "http://schemas.microsoft.com/office/powerpoint/2015/09/main"}
EMU = 914400


def _slide_order(z: zipfile.ZipFile) -> list[str]:
    pres = etree.fromstring(z.read("ppt/presentation.xml"))
    rels = etree.fromstring(z.read("ppt/_rels/presentation.xml.rels"))
    target = {r.get("Id"): r.get("Target") for r in rels}
    ids = [s.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
           for s in pres.iter("{%s}sldId" % NS["p"])]
    return ["ppt/" + target[i].lstrip("/").replace("ppt/", "") for i in ids]


def _transition(root) -> dict:
    tr = None
    for ac in root.findall("mc:AlternateContent", NS):
        ch = ac.find("mc:Choice", NS)
        if ch is not None and ch.find("p:transition", NS) is not None:
            tr = ch.find("p:transition", NS)
    if tr is None:
        tr = root.find("p:transition", NS)
    if tr is None:
        return {"type": "none"}
    kids = [etree.QName(c).localname for c in tr]
    info = {"type": kids[0] if kids else "none", "spd": tr.get("spd"), "adv_ms": tr.get("advTm"),
            "dur_ms": tr.get("{%s}dur" % NS["p14"])}
    if kids:
        info["attrs"] = dict(tr[0].attrib)
    return {k: v for k, v in info.items() if v not in (None, {})}


def _objects(root) -> list[dict]:
    out = []
    for el in root.iter("{%s}sp" % NS["p"], "{%s}pic" % NS["p"], "{%s}grpSp" % NS["p"], "{%s}cxnSp" % NS["p"],
                        "{%s}graphicFrame" % NS["p"]):
        c = el.find(".//p:cNvPr", NS)
        off, ext = el.find(".//a:xfrm/a:off", NS), el.find(".//a:xfrm/a:ext", NS)
        xfrm = el.find(".//a:xfrm", NS)
        geom = el.find(".//a:prstGeom", NS)
        kind = etree.QName(el).localname
        if geom is not None:
            kind += ":" + geom.get("prst")
        elif el.find(".//a:custGeom", NS) is not None:
            kind += ":custGeom"
        fill = el.find("./p:spPr/a:solidFill/a:srgbClr", NS)
        txt = "".join(el.itertext()).strip() if kind.startswith("sp") else ""
        d = {"id": c.get("id") if c is not None else None, "name": c.get("name") if c is not None else "", "kind": kind}
        if off is not None and ext is not None:
            d.update(x=round(int(off.get("x")) / EMU, 2), y=round(int(off.get("y")) / EMU, 2),
                     w=round(int(ext.get("cx")) / EMU, 2), h=round(int(ext.get("cy")) / EMU, 2))
        if xfrm is not None and xfrm.get("rot"):
            d["rot"] = round(int(xfrm.get("rot")) / 60000, 1)
        rot3d = el.find(".//a:scene3d/a:camera/a:rot", NS)
        if rot3d is not None:
            d["3d"] = {k: round(int(v) / 60000, 1) for k, v in rot3d.attrib.items()}
        if fill is not None:
            d["fill"] = fill.get("val")
        if el.find(".//a:gradFill", NS) is not None:
            d["grad"] = True
        if txt:
            d["text"] = txt[:60]
        out.append(d)
    return out


def _effects(root, names: dict[str, str]) -> list[dict]:
    out = []
    for ctn in root.iter("{%s}cTn" % NS["p"]):
        if ctn.get("presetClass") is None:
            continue
        tgt = ctn.find(".//p:spTgt", NS)
        delay = 0  # задержка складывается из условий самого узла и всех родительских cTn
        node = ctn
        while node is not None:
            if etree.QName(node).localname == "cTn":
                for c in node.findall("p:stCondLst/p:cond", NS):
                    if (c.get("delay") or "").isdigit() and c.get("evt") is None:
                        delay += int(c.get("delay"))
            node = node.getparent()
        durs = [int(c.get("dur")) for c in ctn.iter("{%s}cTn" % NS["p"]) if (c.get("dur") or "").isdigit()]
        out.append({"class": ctn.get("presetClass"), "preset": ctn.get("presetID"), "subtype": ctn.get("presetSubtype"),
                    "node": ctn.get("nodeType"), "delay": delay,
                    "dur_ms": max(durs) if durs else None, "repeat": ctn.get("repeatCount"),
                    "target": names.get(tgt.get("spid"), tgt.get("spid")) if tgt is not None else None})
    return out


def analyze(path: Path, rng: tuple[int, int] | None = None) -> list[dict]:
    with zipfile.ZipFile(path) as z:
        order = _slide_order(z)
        slides = []
        for i, name in enumerate(order, 1):
            root = etree.fromstring(z.read(name))
            objs = _objects(root)
            names = {o["id"]: o["name"] for o in objs}
            slides.append({"slide": i, "transition": _transition(root), "objects": objs,
                           "effects": _effects(root, names)})
    for i, s in enumerate(slides):
        cur = {o["name"] for o in s["objects"] if o["name"].startswith("!!")}
        prev = {o["name"] for o in slides[i - 1]["objects"] if o["name"].startswith("!!")} if i else set()
        s["pairs_prev"] = len(cur & prev)
        s["morph_names"] = len(cur)
    if rng:
        slides = [s for s in slides if rng[0] <= s["slide"] <= rng[1]]
    return slides


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("deck")
    ap.add_argument("--slides", help="диапазон, например 3-7")
    ap.add_argument("--objects", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()
    rng = tuple(int(x) for x in a.slides.split("-")) if a.slides else None
    if rng and len(rng) == 1:
        rng = (rng[0], rng[0])
    slides = analyze(Path(a.deck), rng)
    for s in slides:
        tr = s["transition"]
        tr_s = tr["type"] + (f" {tr.get('dur_ms')} мс" if tr.get("dur_ms") else "") + \
            (f" {tr['attrs']}" if tr.get("attrs") else "") + (f" авто {tr['adv_ms']} мс" if tr.get("adv_ms") else "")
        kinds = {}
        for o in s["objects"]:
            k = o["kind"].split(":")[0]
            kinds[k] = kinds.get(k, 0) + 1
        print(f"— слайд {s['slide']}: переход {tr_s}; объектов {len(s['objects'])} {kinds}; "
              f"!!-имён {s['morph_names']}, пар с прошлым {s['pairs_prev']}; эффектов {len(s['effects'])}")
        for e in s["effects"]:
            print(f"    эффект {e['class']}/{e['preset']} → {e['target']} задержка {e['delay']} мс, "
                  f"{e['dur_ms']} мс{', повтор ' + e['repeat'] if e['repeat'] else ''}")
        if a.objects:
            for o in s["objects"]:
                extra = {k: v for k, v in o.items() if k not in ("id", "name", "kind")}
                print(f"    {o['name'][:38]:38s} {o['kind']:22s} {json.dumps(extra, ensure_ascii=False)}")
    if a.json:
        Path(a.json).write_text(json.dumps(slides, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
