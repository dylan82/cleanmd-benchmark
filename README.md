# CleanMD PDF → Markdown benchmark

The scripts, ground truth and results behind [cleanmd.dev/benchmarks/pdf-to-markdown](https://cleanmd.dev/benchmarks/pdf-to-markdown): five public PDFs of different genres, three converters run with default options, scored against a ground truth that never comes from any tool's output.

I built CleanMD, so read the numbers with that in mind. Everything needed to check them is here, including the runs where CleanMD loses.

## Reproduce

```
./run.sh
```

About two minutes on a laptop: bash 3.2 or newer, python3 3.10 or newer, curl, and about 30 MB of downloads. The script fetches the five PDFs from their original sources (they are not in this repo), installs the two competing converters at pinned versions into a local virtualenv, builds the ground truth, and writes `results.json`.

CleanMD's engine is not open source, so `run.sh` cannot execute it here. Two options:

- use the raw CleanMD outputs in `out/*.cleanmd.md`, produced by the exact engine version named in `results.json` and on the page, or
- convert the five PDFs yourself on [cleanmd.dev](https://cleanmd.dev) (free, no account) and save each result as `out/<id>.cleanmd.md` before `score_all.py` runs.

The competing converters' outputs are regenerated on every run.

## Corpus

| id | document | why it is here |
|---|---|---|
| `rfc9110` | RFC 9110, *HTTP Semantics* (IETF, 194 pages) | 291 numbered sections, ABNF grammar and ASCII diagrams, running footer with page numbers |
| `bert` | BERT (arXiv 1810.04805, 16 pages) | two-column paper with results tables and captions beside them |
| `thinkpython2` | *Think Python*, 2nd edition (Green Tea Press, 292 pages) | technical book: table of contents, 500+ code listings, operator tables |
| `scotus` | *Loper Bright Enterprises v. Raimondo* (Supreme Court of the United States, 114 pages) | legal opinion: parts I/II/III and sub-parts A/B/C set as single centered characters at body size |
| `nist-cyber` | NIST Cybersecurity Framework 2.0, CSWP 29 (32 pages) | standard with table of contents, appendices, and tables with multi-line cells |

## Tools

- CleanMD, the same client-side engine that runs in the browser, executed in Node for timing.
- MarkItDown 0.1.7 (Microsoft), `markitdown file.pdf`.
- pymupdf4llm 1.28.2 (Artifex), `pymupdf4llm.to_markdown(file)`.

Pandoc is not in the table because it cannot read PDF; for Pandoc, PDF is an output format. No options, no post-processing: the default output of each tool.

## Ground truth

Built by `gt_build.py` into `gt/`, from the documents themselves:

- RFC 9110: the 291 numbered sections from the table of contents of the official `rfc9110.txt`.
- Think Python: the 126 entries of the book's own table of contents (pages 13 to 17 of the PDF).
- BERT: the 29 numbered sections, read as the lines set in the Medium weight that start with a section number.
- SCOTUS: the 31 part markers (I, II, A, B, 1 …) of the opinion of the Court, the Gorsuch concurrence and the Kagan dissent, read from the markup of the [Cornell LII edition](https://www.law.cornell.edu/supremecourt/text/22-451), where each marker is its own centered heading element. `run.sh` downloads that page; it is not redistributed here. The first run of this benchmark defined the markers geometrically instead (a single token, centered, at 11pt), which is also the rule CleanMD uses to detect them. That definition is now only a cross-check that attaches page numbers, and `gt_build.py` stops if the two lists ever disagree. On the current document they agree 31 for 31.
- NIST: the 8 top-level entries of the document's table of contents (5 sections and 3 appendices).

## Metrics

Computed by `score_all.py`, the same keys as `results.json`:

- `sections_found` / `sections_total`: ground-truth sections present as Markdown headings with their number and the first 18 letters or digits of their title, at any level; `missing_sections` lists the rest.
- `depth_ok`: of the sections found, how many sit at the level implied by the depth of their numbering, allowing a constant offset per document.
- `fences`, `single_line_fences`, `fence_markers_odd`: closed ``` blocks, how many are a single line, and whether the fence markers come in an odd count (an unclosed fence). `abnf_one_block` (RFC): the collected ABNF comes out as one block. `operators_block_fenced` (Think Python): the `x != y … x >= y` listing is a fence.
- `markers_as_headings`, `fused_markers`, `markers_unaccounted`, `running_header_headings` (SCOTUS): part markers rendered as headings; roman or letter markers swallowed into the following paragraph (`… laws. I Our …`; digits are excluded because they collide with footnote references); the rest; running page headers promoted to headings.
- `tables`, `table_rows`, `prose_cells`: GFM tables (informative: more is not better), their rows, and cells that contain a sentence of prose, meaning seven or more words with three consecutive lowercase words. That is the signal of a fake or contaminated table, and a lower bound, since Title Case does not count.
- `footer_lines` (RFC): lines of the running footer (`Standards Track … Page N`) left in the text.
- `seconds`: wall-clock conversion time on the same laptop, one run. CleanMD in Node, not in the browser.

## Where CleanMD loses

From `results.json` as published:

- Think Python: pymupdf4llm emits more fences, 657 against 569. Of its fences, 328 are single-line ones (CleanMD: 52), and the operator listing that opens §5.2 is a fence only in CleanMD. Still, on the raw count it wins.
- Prose cells: MarkItDown has 0 prose cells on NIST where CleanMD has 23, and 0 on RFC 9110 where CleanMD has 11. Part of CleanMD's NIST count is by design, since it keeps the Tier table of Appendix B as a table with paragraph-length cells, but the metric is the metric.
- History, because it matters: the first run (11 September 2026, CleanMD 0.84.0) scored 280 of 291 sections on RFC 9110 and pymupdf4llm won that row with 290. The 11 misses were bold headings whose glyphs came from two font subsets; fixed the same day and re-measured. The page keeps that changelog.

The CI of the CleanMD repository checks that the page reports at least one metric where a competitor beats CleanMD on its own, and that every sentence on the page is generated from the numbers rather than written by hand.

## Layout of this repo

```
run.sh          download corpus, run competitors, build ground truth, score
gt_build.py     ground truth from the documents (and the LII page for SCOTUS)
score_all.py    metrics → results.json
gt/             the ground truth as built (rfc9110.json, others.json)
results.json    the numbers on the page
out/            raw CleanMD outputs, one per document (competitor outputs are regenerated)
```

`pdfs/`, `.venv/` and the competitor outputs are ignored by git. The scripts are the same files that ship in the kit downloadable from the page; their inline comments are in Italian, this README is the reference in English.

## License

MIT for everything in this repository. The PDFs belong to their publishers and are downloaded from their original sources; the Cornell LII page is downloaded for the ground truth and not redistributed.
