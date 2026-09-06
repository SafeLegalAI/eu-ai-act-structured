---
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
  - config_name: articles
    data_files:
      - split: train
        path: data/articles.parquet
  - config_name: recitals
    data_files:
      - split: train
        path: data/recitals.parquet
  - config_name: annexes
    data_files:
      - split: train
        path: data/annexes.parquet
  - config_name: definitions
    data_files:
      - split: train
        path: data/definitions.parquet
  - config_name: obligations
    default: true
    data_files:
      - split: train
        path: data/obligations.parquet
---

# EU AI Act, structured

**Regulation (EU) 2024/1689 (the Artificial Intelligence Act) as tables: every article, recital, annex and definition, 503 obligations coded by actor, risk tier, application date and penalty basis, plus milestones, national competent authorities and fine tiers.**

Built 2026-09-06 by [SafeLegalAI](https://safelegalai.com) (Cognesio LLP) from the official English text served by the Publications Office of the European Union (Cellar, CELEX 32024R1689). Canonical pages: [safelegalai.com/topics/eu-ai-act](https://safelegalai.com/topics/eu-ai-act) · pipeline and issues: [https://github.com/SafeLegalAI/eu-ai-act-structured](https://github.com/SafeLegalAI/eu-ai-act-structured).

## Tables

| config | rows | what a row is |
|---|---|---|
| `articles` | 113 | one article: number, title, chapter, section, numbered paragraphs with lettered points (JSON), flattened text, EUR-Lex anchor |
| `recitals` | 180 | one recital |
| `annexes` | 13 | one annex: title and text |
| `definitions` | 68 | one Article 3 definition: number, term, definition |
| `obligations` | 503 | **one distinct obligation, prohibition, right or institutional duty**, coded by SafeLegalAI from the article text: `actor[]`, `obligation_type`, `risk_tier`, `applies_from` (+ `applies_from_basis`), `penalty_basis`, `legal_practice_relevance` (+ note), `cross_references[]`, and the Regulation's operative words in `quote` (verbatim, ≤ 60 words; every quote is machine-checked against the parsed text) |
| `milestones` | 0 | one dated milestone: entry into force, staged application, transitional dates, Commission deadlines — with legislative status (`past`, `scheduled`, `proposed`, `deferred`) and official source |
| `authorities` | 0 | one national competent authority under Article 70, per Member State, with role and designation status |
| `penalties` | 0 | one fine tier from Articles 99–101: conduct, maximum fixed amount, turnover percentage, rule |

### Obligations by risk tier

| `risk_tier` | rows |
|---|---|
| `high-risk` | 317 |
| `not-tier-specific` | 97 |
| `gpai` | 36 |
| `gpai-systemic-risk` | 22 |
| `prohibited-practice` | 17 |
| `all-ai-systems` | 7 |
| `transparency-risk` | 7 |

### Obligations by application date (Article 113 as written; see `milestones` for any deferral)

| `applies_from` | rows |
|---|---|
| 2024-08-01 | 1 |
| 2025-02-02 | 31 |
| 2025-08-02 | 124 |
| 2026-08-02 | 344 |
| 2027-08-02 | 3 |

146 rows are coded `legal_practice_relevance: high` — the provisions that reach a law firm, chambers, in-house team or court deploying AI, a court as public-authority deployer, or a legal-AI vendor as provider (including Annex III point 8, AI systems intended to assist a judicial authority).

## What is the Regulation's and what is ours

The text (`articles`, `recitals`, `annexes`, `definitions`, every `quote`) is the European Union's, reused under [Commission Decision 2011/833/EU](https://eur-lex.europa.eu/eli/dec/2011/833/oj) — attribution: *© European Union, 1998–2026, https://eur-lex.europa.eu*. Only the official text at EUR-Lex is authentic; this dataset is a convenience and may lag amendments.

The coding (`actor`, `obligation_type`, `risk_tier`, `applies_from`, `penalty_basis`, `legal_practice_relevance`, `summary`, `legal_practice_note`) is SafeLegalAI's, released **CC BY 4.0** — attribute *SafeLegalAI (safelegalai.com), published by Cognesio LLP*. It is descriptive, not legal advice; it records what the Regulation says, not what anyone should do. Corrections: [safelegalai.com/report](https://safelegalai.com/report).

## Method

1. `pipeline/parse_eurlex.py` fetches the ELI-structured XHTML from Cellar and parses chapters, sections, articles, paragraphs, points, recitals, annexes and definitions (deterministic).
2. Three coding passes (Arts 1–28, 29–70, 71–113 + annexes) wrote one row per distinct duty using only the parsed text, quoting the operative words; a fourth pass compiled milestones, authorities and penalties from official Commission and national sources.
3. `pipeline/build_release.py` merges, checks every quote is a verbatim substring of the parsed article/annex text, and writes JSONL, CSV and Parquet.
4. Human review: SafeLegalAI's editor re-opens a sample of rows before each release; the `legal_practice_relevance` column in particular is editorial coding.

## Use

```python
from datasets import load_dataset
ob = load_dataset("safelegalaidata/eu-ai-act-structured", "obligations")["train"]
firm = ob.filter(lambda r: r["legal_practice_relevance"] == "high" and "deployer" in r["actor"])
```

## Cite

> SafeLegalAI (Cognesio LLP), "EU AI Act, structured", v0.1.0, 2026-09-06. https://huggingface.co/datasets/safelegalaidata/eu-ai-act-structured — text © European Union, reused under Decision 2011/833/EU; coding CC BY 4.0.

## Disclaimer and notices

Provided "as is", without warranty of any kind (CC BY 4.0 §5; Apache-2.0 §7). Not legal advice; Cognesio LLP is not a law firm. Only the Official Journal text of Regulation (EU) 2024/1689 is authentic; this dataset may lag amendments and corrigenda. Every coding column is SafeLegalAI's good-faith reading of the text for comparison — not an interpretation of the law you may rely on, and not a statement of how any authority will apply it. Application dates follow Article 113 as written unless the `milestones` table records an amending act published in the Official Journal; check `milestones` before relying on a date. Names of institutions and authorities identify them only. Full terms, notice-and-takedown and governing law (England and Wales): https://safelegalai.com/disclaimer · repository DISCLAIMER.md.

## Manifest

```json
{
  "regulation": "Regulation (EU) 2024/1689 (Artificial Intelligence Act)",
  "celex": "32024R1689",
  "source": "http://publications.europa.eu/resource/celex/32024R1689",
  "source_format": "application/xhtml+xml (Cellar, Publications Office of the European Union)",
  "eli": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng",
  "source_sha256": "8f0b656302f9864cc87e040c371f209a9d65ae1a6cecc25ca5eb737e872d721a",
  "parsed": "2026-09-05",
  "counts": {
    "articles": 113,
    "recitals": 180,
    "annexes": 13,
    "definitions": 68,
    "obligations": 503,
    "milestones": 0,
    "authorities": 0,
    "penalties": 0
  },
  "reuse": "Commission Decision 2011/833/EU \u2014 attribution: \u00a9 European Union, 1998\u20132026, https://eur-lex.europa.eu",
  "version": "0.1.0",
  "built": "2026-09-06",
  "contentSha256": "dc01ca740f279ecfac219c3572be5d0ae2001dd8235b1543378eb7c4b19f9ef8",
  "canonical": "https://safelegalai.com/topics/eu-ai-act",
  "repository": "https://github.com/SafeLegalAI/eu-ai-act-structured",
  "license_text": "Commission Decision 2011/833/EU (\u00a9 European Union)",
  "license_coding": "CC BY 4.0 (SafeLegalAI, Cognesio LLP)"
}
```
