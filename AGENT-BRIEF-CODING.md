# Agent brief — coding the EU AI Act into obligations (read fully)

You are coding one slice of **SafeLegalAI's `eu-ai-act-structured` dataset**. The Regulation's text is already parsed, offline, in `data/articles.jsonl` (one line per article: `article`, `title`, `chapter`, `chapter_title`, `section`, `section_title`, `paragraphs[]` with `number`, `text`, `points[]`, `tail`; `text` is the flattened article). Also available: `data/recitals.jsonl`, `data/annexes.jsonl`, `data/definitions.jsonl`. **Work from these files — do not fetch the Regulation from the web** (EUR-Lex blocks bots; the parsed text is the official Cellar XHTML).

## The rule
**Quote the Regulation; code conservatively.** `quote` is verbatim. `summary` is a plain-English restatement of what the text says, not what anyone should do. When a provision creates several distinct duties (e.g. Art. 26 has twelve paragraphs each a separate deployer duty; Art. 5(1) has eight prohibited practices as points), write one row per duty/point. When a provision is institutional (Commission powers, Board composition) code it too — `obligation_type: governance-institutional` / `enforcement-power` / `delegated-or-implementing-act` — so the table covers the whole Act. Definitions (Art. 3) are NOT rows (they have their own file); Art. 3 gets no rows. Recitals are not rows either; cite them in `cross_references` where they explain a duty.

## Application dates (do this carefully)
Article 113 sets staged application: general application 2 August 2026; Chapters I and II from 2 February 2025 (Art. 113(a)); Chapter III Section 4, Chapter V, Chapter VII, Chapter XII and Article 78 from 2 August 2025 except Article 101 (Art. 113(b)); Article 6(1) and the corresponding obligations from 2 August 2027 (Art. 113(c)). Read Art. 113 in `data/articles.jsonl` yourself and apply it: a row's `applies_from` is determined by the chapter/section/article it sits in. **Before coding, one agent (the "milestones" agent) verifies whether any amending act in force on 2026-09-06 changed these dates** (the Commission's 2025 "Digital Omnibus" proposal sought to defer high-risk obligations; you must check its actual legislative status on official sources — eur-lex.europa.eu via web_search results, digital-strategy.ec.europa.eu, the Official Journal — and NOT assume it passed). Coding agents: use the Art. 113 dates as written and put `applies_from_basis` = the Art. 113 point; the milestones agent's findings will be reconciled afterwards by the coordinator. If you happen to confirm an amendment from an official source, say so in your final report.

## Actors and tiers
`actor` is who the duty falls on (array). `risk_tier`: `prohibited-practice` (Art. 5), `high-risk` (Ch. III), `transparency-risk` (Art. 50), `gpai` / `gpai-systemic-risk` (Ch. V), `all-ai-systems` (e.g. Art. 4 AI literacy), `not-tier-specific` (governance, penalties, scope).

## Legal-practice relevance (the column that makes this dataset ours)
For each row ask: does this reach (a) a law firm / chambers / in-house legal team / court that *deploys* AI, (b) a legal-AI vendor as *provider*, (c) a court or public body as *public-authority deployer*? High: Art. 4 (AI literacy — every deployer), Art. 26 (deployer duties, incl. 26(6) six-month log retention), Art. 50 (transparency: chatbots, synthetic content), Art. 5 (prohibited practices), Annex III point 8 (administration of justice — AI assisting judicial authorities is high-risk) and the Ch. III provider duties for vendors of such systems, Art. 27 (FRIA for public bodies), Art. 99 penalties. Medium: registration, conformity, GPAI duties as they reach vendors. Low/none: notified-body mechanics, Board composition, amendments to other acts. Write `legal_practice_note` descriptively.

## Output
Append one JSON object per line to **the file named in your task** under `work/agents/`, conforming to `schema/obligation.schema.json` (read it: `cat schema/obligation.schema.json`). `url` = `https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng#art_<n>`. Validate: `python3 -c "import json;[json.loads(l) for l in open('work/agents/<file>')]"` and check required keys/enums. Expect ~4–10 rows per substantive article; institutional articles 1–3 rows.

## When done
Reply with a short report only: rows written; rows per chapter; any article you could not code and why; any amendment to Art. 113 dates you confirmed from an official source (with URL). Do not paste rows.

## Addendum (2026-09-06, after verification): the text is now the CONSOLIDATED version

`data/articles.jsonl`, `data/definitions.jsonl` and `data/annexes.jsonl` now hold the **consolidated text as of 27 July 2026** (CELEX 02024R1689-20260727), i.e. Regulation (EU) 2024/1689 as amended by **Regulation (EU) 2026/1744 (Digital Omnibus on AI)**, in force 27 July 2026 (OJ L 2026/1744, 24.7.2026; Commission: https://digital-strategy.ec.europa.eu/en/news/ai-omnibus-enters-force). The text as enacted is in `data/articles_as_enacted.jsonl`; a per-article diff is in `data/amendments.jsonl`. Articles may carry letter suffixes (`"4a"`, `"60a"`, `"75a"`–`"75d"`) and points may too (`(ba)`, `(bb)`, `1a`, `1b`).

**Application dates — Article 113 as amended** (read it in `data/articles.jsonl`):
- Chapters I–II: 2025-02-02 (Art. 113(a)), **except** Art. 5(1) points (ba) and (bb) and Art. 5(1a)–(1b): 2026-12-02 (basis "Art. 113(a) as amended by Reg. (EU) 2026/1744").
- Chapter III Section 4, Chapter V, Chapter VII, Chapter XII, Art. 78: 2025-08-02 (Art. 113(b)), except Art. 101.
- **Chapter III Sections 1–3 (Arts 6–27), except Art. 6(5)**: 2027-12-02 for Art. 6(2)/Annex III high-risk (basis "Art. 113(c)(i) as amended"), 2028-08-02 for Art. 6(1)/Annex I high-risk (basis "Art. 113(c)(ii) as amended"). Where a duty applies to both, write the row once with 2027-12-02 and note the Annex I date in `transitional_note`.
- Arts 102–110: 2026-07-27 (Art. 113(d) as amended).
- Everything else: 2026-08-02 (Art. 113 second subparagraph).
- Art. 111(2) as amended: public-authority high-risk systems must comply by 2030-08-02; Art. 111(4): synthetic-content systems on the market before 2 Aug 2026 comply with Art. 50(2) by 2026-12-02.
Set `applies_from_as_enacted` / `applies_from_basis_as_enacted` on every row too (what Art. 113 said before the Omnibus).

For `obligation_id` on inserted articles use e.g. `art-4a-1`, `art-75a-2-b`. The `article` field is an integer for numbered articles and a string for suffixed ones (`"4a"`).
