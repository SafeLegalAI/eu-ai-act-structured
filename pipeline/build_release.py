"""Build the release bundle: merge the coded obligation slices, write JSONL + CSV + Parquet for
every table, the dataset card and a manifest; optionally push to Hugging Face.

    .venv/bin/python pipeline/build_release.py [--push]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
WORK = ROOT / "work"
HF_ORG = os.environ.get("HF_ORG", "safelegalaidata")
HF_REPO = "eu-ai-act-structured"
SITE = "https://safelegalai.com"
GH = "https://github.com/SafeLegalAI/eu-ai-act-structured"

TABLES = ["articles", "recitals", "annexes", "definitions", "obligations", "milestones", "authorities", "penalties"]


def read_jsonl(p: Path):
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()] if p.exists() else []


def write_jsonl(p: Path, rows):
    with p.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def flat(v):
    return json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v


def write_csv(p: Path, rows):
    if not rows:
        return
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: flat(r.get(k)) for k in cols})


def write_parquet(p: Path, rows):
    if not rows:
        return
    cols = list(dict.fromkeys(k for r in rows for k in r))
    # nested structures (paragraphs, points) go in as JSON strings so the schema stays flat and stable
    simple = [{c: (json.dumps(r.get(c), ensure_ascii=False) if isinstance(r.get(c), (list, dict)) else r.get(c)) for c in cols} for r in rows]
    pq.write_table(pa.Table.from_pylist(simple), p, compression="zstd")


def merge_obligations():
    rows = []
    for f in sorted(WORK.glob("agents/obligations-*.jsonl")):
        rows += read_jsonl(f)
    for r in rows:
        r.pop("_src", None)
    rows.sort(key=lambda r: (r["article"], r.get("paragraph") or 0, str(r.get("point") or ""), r["obligation_id"]))
    write_jsonl(DATA / "obligations.jsonl", rows)
    return rows


def card(counts: dict, manifest: dict) -> str:
    today = date.today().isoformat()
    ob = read_jsonl(DATA / "obligations.jsonl")
    by_tier = {}
    for r in ob:
        by_tier[r["risk_tier"]] = by_tier.get(r["risk_tier"], 0) + 1
    by_date = {}
    for r in ob:
        by_date[r["applies_from"]] = by_date.get(r["applies_from"], 0) + 1
    hi = sum(1 for r in ob if r["legal_practice_relevance"] == "high")
    tiers = "\n".join(f"| `{k}` | {v} |" for k, v in sorted(by_tier.items(), key=lambda kv: -kv[1]))
    dates = "\n".join(f"| {k} | {v} |" for k, v in sorted(by_date.items()))
    configs = "\n".join(f"  - config_name: {t}\n{'    default: true' + chr(10) if t == 'obligations' else ''}    data_files:\n      - split: train\n        path: data/{t}.parquet" for t in TABLES if (DATA / f"{t}.parquet").exists())
    return f"""---
license: cc-by-4.0
pretty_name: "EU AI Act (Regulation (EU) 2024/1689) as structured data — SafeLegalAI"
language:
  - en
size_categories:
  - n<1K
tags:
  - legal
  - law
  - eu-ai-act
  - regulation
  - ai-governance
  - compliance
  - safelegalai
configs:
{configs}
---

# EU AI Act, structured

**Regulation (EU) 2024/1689 (the Artificial Intelligence Act) as tables: every article, recital, annex and definition, {counts['obligations']} obligations coded by actor, risk tier, application date and penalty basis, plus milestones, national competent authorities and fine tiers.**

Built {today} by [SafeLegalAI]({SITE}) (Cognesio LLP) from the official English text served by the Publications Office of the European Union (Cellar, CELEX {manifest['celex']}). Canonical pages: [{SITE.removeprefix("https://")}/topics/eu-ai-act]({SITE}/topics/eu-ai-act) · pipeline and issues: [{GH}]({GH}).

## Tables

| config | rows | what a row is |
|---|---|---|
| `articles` | {counts['articles']} | one article: number, title, chapter, section, numbered paragraphs with lettered points (JSON), flattened text, EUR-Lex anchor |
| `recitals` | {counts['recitals']} | one recital |
| `annexes` | {counts['annexes']} | one annex: title and text |
| `definitions` | {counts['definitions']} | one Article 3 definition: number, term, definition |
| `obligations` | {counts['obligations']} | **one distinct obligation, prohibition, right or institutional duty**, coded by SafeLegalAI from the article text: `actor[]`, `obligation_type`, `risk_tier`, `applies_from` (+ `applies_from_basis`), `penalty_basis`, `legal_practice_relevance` (+ note), `cross_references[]`, and the Regulation's operative words in `quote` (verbatim, ≤ 60 words; every quote is machine-checked against the parsed text) |
| `milestones` | {counts.get('milestones', 0)} | one dated milestone: entry into force, staged application, transitional dates, Commission deadlines — with legislative status (`past`, `scheduled`, `proposed`, `deferred`) and official source |
| `authorities` | {counts.get('authorities', 0)} | one national competent authority under Article 70, per Member State, with role and designation status |
| `penalties` | {counts.get('penalties', 0)} | one fine tier from Articles 99–101: conduct, maximum fixed amount, turnover percentage, rule |

### Obligations by risk tier

| `risk_tier` | rows |
|---|---|
{tiers}

### Obligations by application date (Article 113 as written; see `milestones` for any deferral)

| `applies_from` | rows |
|---|---|
{dates}

{hi} rows are coded `legal_practice_relevance: high` — the provisions that reach a law firm, chambers, in-house team or court deploying AI, a court as public-authority deployer, or a legal-AI vendor as provider (including Annex III point 8, AI systems intended to assist a judicial authority).

## What is the Regulation's and what is ours

The text (`articles`, `recitals`, `annexes`, `definitions`, every `quote`) is the European Union's, reused under [Commission Decision 2011/833/EU](https://eur-lex.europa.eu/eli/dec/2011/833/oj) — attribution: *© European Union, 1998–2026, https://eur-lex.europa.eu*. Only the official text at EUR-Lex is authentic; this dataset is a convenience and may lag amendments.

The coding (`actor`, `obligation_type`, `risk_tier`, `applies_from`, `penalty_basis`, `legal_practice_relevance`, `summary`, `legal_practice_note`) is SafeLegalAI's, released **CC BY 4.0** — attribute *SafeLegalAI ({SITE.removeprefix("https://")}), published by Cognesio LLP*. It is descriptive, not legal advice; it records what the Regulation says, not what anyone should do. Corrections: [{SITE.removeprefix("https://")}/report]({SITE}/report).

## Method

1. `pipeline/parse_eurlex.py` fetches the ELI-structured XHTML from Cellar and parses chapters, sections, articles, paragraphs, points, recitals, annexes and definitions (deterministic).
2. Three coding passes (Arts 1–28, 29–70, 71–113 + annexes) wrote one row per distinct duty using only the parsed text, quoting the operative words; a fourth pass compiled milestones, authorities and penalties from official Commission and national sources.
3. `pipeline/build_release.py` merges, checks every quote is a verbatim substring of the parsed article/annex text, and writes JSONL, CSV and Parquet.
4. Human review: SafeLegalAI's editor re-opens a sample of rows before each release; the `legal_practice_relevance` column in particular is editorial coding.

## Use

```python
from datasets import load_dataset
ob = load_dataset("{HF_ORG}/{HF_REPO}", "obligations")["train"]
firm = ob.filter(lambda r: r["legal_practice_relevance"] == "high" and "deployer" in r["actor"])
```

## Cite

> SafeLegalAI (Cognesio LLP), "EU AI Act, structured", v{manifest['version']}, {today}. https://huggingface.co/datasets/{HF_ORG}/{HF_REPO} — text © European Union, reused under Decision 2011/833/EU; coding CC BY 4.0.

## Manifest

```json
{json.dumps(manifest, indent=2)}
```
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--version", default="0.1.0")
    a = ap.parse_args()
    merge_obligations()
    counts = {}
    for t in TABLES:
        rows = read_jsonl(DATA / f"{t}.jsonl")
        counts[t] = len(rows)
        if rows:
            write_csv(DATA / f"{t}.csv", rows)
            write_parquet(DATA / f"{t}.parquet", rows)
    base = json.loads((DATA / "manifest.json").read_text())
    content = hashlib.sha256(b"".join((DATA / f"{t}.jsonl").read_bytes() for t in TABLES if (DATA / f"{t}.jsonl").exists())).hexdigest()
    manifest = {**base, "version": a.version, "built": date.today().isoformat(), "counts": counts, "contentSha256": content, "canonical": f"{SITE}/topics/eu-ai-act", "repository": GH, "license_text": "Commission Decision 2011/833/EU (© European Union)", "license_coding": "CC BY 4.0 (SafeLegalAI, Cognesio LLP)"}
    (DATA / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (ROOT / "README.md").write_text(card(counts, manifest), encoding="utf-8")
    print(json.dumps(counts))
    if a.push:
        from huggingface_hub import HfApi

        api = HfApi(token=os.environ.get("HF_TOKEN"))
        repo_id = f"{HF_ORG}/{HF_REPO}"
        api.create_repo(repo_id, repo_type="dataset", exist_ok=True)
        api.upload_folder(repo_id=repo_id, repo_type="dataset", folder_path=str(DATA), path_in_repo="data", commit_message=f"v{a.version} — {counts}")
        api.upload_file(path_or_fileobj=str(ROOT / "README.md"), path_in_repo="README.md", repo_id=repo_id, repo_type="dataset", commit_message=f"card v{a.version}")
        print(f"pushed https://huggingface.co/datasets/{repo_id}")


if __name__ == "__main__":
    main()
