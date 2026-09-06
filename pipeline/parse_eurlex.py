"""Parse Regulation (EU) 2024/1689 (the AI Act) from the Publications Office Cellar into
structured JSONL: articles (with chapter/section, numbered paragraphs and lettered points),
recitals, annexes and the Article 3 definitions.

Source: the official English XHTML served by Cellar with content negotiation —
  http://publications.europa.eu/resource/celex/32024R1689  (Accept: application/xhtml+xml, Accept-Language: eng)
Reuse: Commission Decision 2011/833/EU on the reuse of Commission documents. Attribution: © European Union,
1998–2026, https://eur-lex.europa.eu. Article anchors link to https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng#art_N.

    .venv/bin/python pipeline/parse_eurlex.py            # uses work/32024R1689.en.xhtml if present, else fetches
    .venv/bin/python pipeline/parse_eurlex.py --celex 02024R1689-20240712   # a consolidated version, when one exists
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

import httpx
from lxml import etree, html

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
DATA = ROOT / "data"
UA = "SafeLegalAI-Bot/1.0 (+https://safelegalai.com/datasets; hello@safelegalai.com)"
ELI = "https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng"
# lxml.html drops the XHTML namespace, so tags are plain names
XHTML = ""


def fetch(celex: str) -> Path:
    dest = WORK / f"{celex}.en.xhtml"
    if dest.exists():
        return dest
    WORK.mkdir(exist_ok=True)
    with httpx.Client(headers={"User-Agent": UA, "Accept": "application/xhtml+xml", "Accept-Language": "eng"}, follow_redirects=True, timeout=120) as c:
        r = c.get(f"http://publications.europa.eu/resource/celex/{celex}")
        r.raise_for_status()
        dest.write_bytes(r.content)
    return dest


def text_of(el) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def norm_id(s: str) -> str:
    return s.replace("\u2019", "'")


def parse(path: Path):
    tree = html.parse(str(path))
    root = tree.getroot()
    by_id = {el.get("id"): el for el in root.iter() if el.get("id")}

    # ---- chapters and sections: map every article id to its chapter/section titles
    def title_after(el):
        t = el.find(".//div[@class='eli-title']")
        return text_of(t) if t is not None else None

    consolidated = "Consolidated TEXT" in (root.findtext(".//title") or "")

    chapters = {}
    for cid, el in by_id.items():
        if re.fullmatch(r"cpt_[IVX]+", cid):
            num = cid.split("_")[1]
            heading = el.find(".//p[@class='oj-ti-section-1']")
            chapters[cid] = {"number": num, "title": title_after(el), "label": text_of(heading) if heading is not None else f"CHAPTER {num}"}

    def container(el, pattern):
        p = el.getparent()
        while p is not None:
            pid = p.get("id") or ""
            if re.fullmatch(pattern, pid):
                return pid
            p = p.getparent()
        return None

    # ---- articles
    articles = []
    def art_key(cid):
        m = re.fullmatch(r"art_(\d+)([a-z]*)", cid)
        return (int(m.group(1)), m.group(2))

    for cid, el in sorted(((k, v) for k, v in by_id.items() if re.fullmatch(r"art_\d+[a-z]*", k)), key=lambda kv: art_key(kv[0])):
        n_num, n_suffix = art_key(cid)
        n = f"{n_num}{n_suffix}"
        title = title_after(el)
        chap_id = container(el, r"cpt_[IVX]+")
        sect_id = container(el, r"cpt_[IVX]+\.sct_\d+")
        chapter = chapters.get(chap_id, {}) if chap_id else {}
        section_title = title_after(by_id[sect_id]) if sect_id and sect_id in by_id else None
        section_num = sect_id.split(".sct_")[1] if sect_id else None
        # A paragraph container is either a numbered div (id 001.002) or, for articles without
        # numbered paragraphs (Art. 3 definitions), the article div itself. Walk direct children in
        # order: oj-normal <p> = text, <table> = lettered/numbered points.
        def collect(node):
            texts, points = [], []
            for ch in node:
                cls = ch.get("class") or ""
                if ch.tag == "p" and "modref" in cls:
                    continue  # ▼M1 amendment markers (consolidated texts)
                if ch.tag == "p" and ("oj-normal" in cls or cls.startswith("norm")):
                    texts.append(text_of(ch))
                elif ch.tag == "div" and "grid-container" in cls:
                    marker = text_of(ch.find(".//div[@class='list grid-list-column-1']") or ch)
                    body = ch.find(".//div[@class='grid-list-column-2']")
                    if body is not None:
                        points.append({"marker": marker.strip("() "), "text": text_of(body)})
                elif ch.tag == "div" and cls == "norm inline-element":
                    t2, p2 = collect(ch)
                    if not t2 and not p2:
                        texts.append(text_of(ch))
                    else:
                        texts += t2
                        points += p2
                elif ch.tag == "table":
                    for tr in ch.iter("tr"):
                        tds = [td for td in tr if td.tag == "td"]
                        if len(tds) >= 2:
                            marker = text_of(tds[0])
                            if re.fullmatch(r"\(?[a-z0-9ivx]+\)?", marker):
                                points.append({"marker": marker.strip("()"), "text": text_of(tds[1])})
                elif ch.tag == "div" and not (ch.get("class") or "").startswith("eli-title"):
                    t2, p2 = collect(ch)
                    texts += t2
                    points += p2
            return texts, points

        paragraphs = []
        para_divs = [c for c in el if c.tag == "div" and re.fullmatch(r"\d{3}\.\d{3}", c.get("id") or "")]
        norm_divs = [c for c in el if c.tag == "div" and (c.get("class") or "") == "norm"]
        if consolidated and norm_divs:
            for child in norm_divs:
                marker = child.find("span[@class='no-parag']")
                num = None
                if marker is not None:
                    m = re.match(r"^(\d+[a-z]?)\.", text_of(marker))
                    num = m.group(1) if m else None
                texts, points = collect(child)
                if not texts and not points:
                    continue
                paragraphs.append({"number": int(num) if num and num.isdigit() else num, "text": texts[0] if texts else "", "points": points, "tail": " ".join(texts[1:])})
        elif para_divs:
            for child in para_divs:
                texts, points = collect(child)
                if not texts and not points:
                    continue
                first = texts[0] if texts else ""
                m = re.match(r"^(\d+)\.\s+(.*)$", first, re.S)
                paragraphs.append({"number": int(m.group(1)) if m else None, "text": m.group(2) if m else first, "points": points, "tail": " ".join(texts[1:])})
        else:
            texts, points = collect(el)
            paragraphs = [{"number": None, "text": texts[0] if texts else "", "points": points, "tail": " ".join(texts[1:])}]
        full = "\n".join(
            (f"{p['number']}. " if p["number"] else "") + p["text"] + ("".join(f"\n({pt['marker']}) {pt['text']}" for pt in p["points"])) + (f"\n{p['tail']}" if p["tail"] else "")
            for p in paragraphs
        )
        articles.append(
            {
                "article": n_num if not n_suffix else n,
                "id": f"art_{n}",
                "title": title,
                "chapter": chapter.get("number"),
                "chapter_title": chapter.get("title"),
                "section": section_num,
                "section_title": section_title,
                "paragraph_count": len(paragraphs),
                "paragraphs": paragraphs,
                "text": full,
                "word_count": len(full.split()),
                "url": f"{ELI}#art_{n}",
            }
        )

    # ---- recitals
    recitals = []
    for cid, el in by_id.items():
        if re.fullmatch(r"rct_\d+", cid):
            n = int(cid.split("_")[1])
            t = text_of(el)
            t = re.sub(rf"^\(\s*{n}\s*\)\s*", "", t)
            recitals.append({"recital": n, "id": cid, "text": t, "url": f"{ELI}#{cid}"})
    recitals.sort(key=lambda r: r["recital"])

    # ---- annexes
    annexes = []
    for cid, el in by_id.items():
        if re.fullmatch(r"anx_[IVX]+", cid):
            num = cid.split("_")[1]
            head = el.find(".//p[@class='oj-doc-ti']")
            title_el = el.find(".//p[@class='oj-ti-annex']") if el.find(".//p[@class='oj-ti-annex']") is not None else None
            # the annex title is usually the second 'oj-doc-ti' p; take all doc-ti paragraphs
            titles = [text_of(p) for p in el.iter(f"{XHTML}p") if (p.get("class") or "") in ("oj-doc-ti", "oj-ti-annex", "title-annex-1", "title-annex-2")]
            # annex bodies use oj-normal paragraphs, headed sub-sections, and (Annex VI) inline enumerations
            body = []
            for node in el.iter():
                cls = node.get("class") or ""
                if node.tag == "p" and ("oj-normal" in cls or "oj-ti-grseq-1" in cls or cls == "norm" or "title-gr-seq" in cls):
                    body.append(text_of(node))
                elif node.tag == "div" and "oj-enumeration-spacing" in cls:
                    body.append(text_of(node))
            annexes.append({"annex": num, "id": cid, "title": " — ".join(t for t in titles[1:] if t) or (titles[0] if titles else None), "text": "\n".join(body), "url": f"{ELI}#{cid}"})
    roman = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12, "XIII": 13}
    annexes.sort(key=lambda a: roman.get(a["annex"], 99))

    # ---- definitions (Article 3)
    definitions = []
    art3 = next((a for a in articles if a["article"] == 3), None)
    if art3:
        for p in art3["paragraphs"]:
            for pt in p["points"]:
                # ‘term’ means …  |  ‘term’, for the purpose of …, means …  |  ‘term’ means: (a) …
                m = re.match(r"^[‘'\"“](.+?)[’'\"”](?:,[^:]*?)?\s+means:?\s*(.*)$", pt["text"], re.S)
                if m:
                    definitions.append({"number": int(pt["marker"]) if pt["marker"].isdigit() else pt["marker"], "term": m.group(1), "definition": m.group(2).rstrip(";."), "url": f"{ELI}#art_3"})

    return articles, recitals, annexes, definitions


def write_jsonl(path: Path, rows):
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--celex", default="32024R1689")
    a = ap.parse_args()
    src = fetch(a.celex)
    articles, recitals, annexes, definitions = parse(src)
    DATA.mkdir(exist_ok=True)
    write_jsonl(DATA / "articles.jsonl", articles)
    write_jsonl(DATA / "recitals.jsonl", recitals)
    write_jsonl(DATA / "annexes.jsonl", annexes)
    write_jsonl(DATA / "definitions.jsonl", definitions)
    manifest = {
        "regulation": "Regulation (EU) 2024/1689 (Artificial Intelligence Act)",
        "celex": a.celex,
        "source": f"http://publications.europa.eu/resource/celex/{a.celex}",
        "source_format": "application/xhtml+xml (Cellar, Publications Office of the European Union)",
        "eli": ELI,
        "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
        "parsed": date.today().isoformat(),
        "counts": {"articles": len(articles), "recitals": len(recitals), "annexes": len(annexes), "definitions": len(definitions)},
        "reuse": "Commission Decision 2011/833/EU — attribution: © European Union, 1998–2026, https://eur-lex.europa.eu",
    }
    (DATA / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["counts"]))


if __name__ == "__main__":
    sys.exit(main())
