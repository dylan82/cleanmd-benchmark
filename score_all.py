import re, json
import os
HERE = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(HERE, 'pdfs')
GT_DIR = os.path.join(HERE, 'gt')
OUT_DIR = os.path.join(HERE, 'out')
gt = json.load(open(GT_DIR + '/others.json'))
gt['rfc9110'] = json.load(open(GT_DIR + '/rfc9110.json'))
TOOLS = ['cleanmd', 'markitdown', 'pymupdf4llm']
DOCS = ['rfc9110', 'bert', 'thinkpython2', 'scotus', 'nist-cyber']
def norm(s): return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()
def headings(md):
    out = []
    for l in md.split('\n'):
        m = re.match(r'^(#{1,6})\s+(.*)$', l)
        if m: out.append((len(m.group(1)), re.sub(r'[*_`]', '', m.group(2)).strip()))
    return out
def section_score(md, secs):
    heads = headings(md); found = {}
    for lvl, t in heads:
        m = re.match(r'^(Appendix [A-Z]|\d+(?:\.\d+)*|[A-E](?:\.\d+)+)\.?\s+(.+)$', t)
        if m: found.setdefault(m.group(1), (lvl, m.group(2)))
    correct = depth_ok = 0
    tops = [found[s['num']][0] for s in secs if s['num'] in found and '.' not in s['num'] and not s['num'].startswith('Appendix')]
    off = (max(set(tops), key=tops.count) - 1) if tops else None
    for s in secs:
        if s['num'] in found:
            lvl, title = found[s['num']]
            if norm(title)[:18] == norm(s['title'])[:18]:
                correct += 1
                depth = 0 if s['num'].startswith('Appendix') else s['num'].count('.')
                if off is not None and lvl == depth + 1 + off: depth_ok += 1
    missing = [s['num'] for s in secs if not (s['num'] in found and norm(found[s['num']][1])[:18] == norm(s['title'])[:18])]
    return dict(headings=len(heads), sections_found=correct, sections_total=len(secs), depth_ok=depth_ok, missing_sections=missing)
def fence_stats(md):
    n = len(re.findall(r'^\s*```', md, re.M)) // 2
    blocks = re.findall(r'```[^\n]*\n(.*?)```', md, re.S)
    return n, blocks
def table_stats(md):
    lines = md.split('\n'); tables = 0; rows = 0; prose_cells = 0; i = 0
    while i < len(lines):
        if re.match(r'^\s*\|?\s*:?-{3,}', lines[i]) and i > 0 and lines[i-1].strip().startswith('|'):
            tables += 1; j = i + 1
            while j < len(lines) and lines[j].strip().startswith('|'):
                rows += 1
                for cell in lines[j].strip().strip('|').split('|'):
                    w = cell.strip().split()
                    if len(w) >= 7 and re.search(r'[a-z]{3,}\s+[a-z]{3,}\s+[a-z]{3,}', cell) : prose_cells += 1
                j += 1
            i = j
        else: i += 1
    return dict(tables=tables, table_rows=rows, prose_cells=prose_cells)
def time_of(path):
    try:
        for l in open(path):
            if l.startswith('real'): return float(l.split()[1])
    except FileNotFoundError: return None
results = {}
for doc in DOCS:
    results[doc] = {}
    for tool in TOOLS:
        try: md = open(f'{OUT_DIR}/{doc}.{tool}.md', encoding='utf-8', errors='replace').read()
        except FileNotFoundError: results[doc][tool] = None; continue
        r = dict(chars=len(md), seconds=time_of(f'{OUT_DIR}/{doc}.{tool}.time'))
        if doc == 'scotus':
            heads = headings(md)
            marks = [t for _, t in heads if re.fullmatch(r'(?:I|II|III|IV|V|VI|[A-H]|[1-9])', t)]
            total = len(gt['scotus']['markers'])
            # Marcatore fuso: fine frase + marcatore + parola capitalizzata ("laws. I Our").
            # Solo romani e lettere: le cifre collidono con i richiami di nota
            # ("… at 5. 3 The …") e gonfierebbero il conteggio per tutti.
            fused = len(re.findall(r'[.:;]\s+(?:I|II|III|IV|V|VI|[A-H])\s+[A-Z][a-z]', md))
            # Testate correnti promosse a heading (il falso positivo tipico su una sentenza).
            running = sum(1 for _, t in heads if re.search(r'Syllabus|LOPER BRIGHT|Opinion of the Court|, J\., (?:concurring|dissenting)|Cite as:', t))
            r.update(headings=len(heads), markers_as_headings=len(marks), markers_total=total, fused_markers=fused,
                     markers_unaccounted=max(0, total - len(marks) - fused), running_header_headings=running)
        else:
            sc = section_score(md, gt[doc]['sections'])
            r.update(sc)
        n, blocks = fence_stats(md); r['fences'] = n
        r['single_line_fences'] = sum(1 for b in blocks if b.strip().count('\n') == 0)
        r['fence_markers_odd'] = (len(re.findall(r'^\s*```', md, re.M)) % 2) == 1
        if doc == 'rfc9110':
            r['footer_lines'] = len(re.findall(r'Standards Track\s+(?:\[?Page \d+\]?)', md))
        if doc == 'rfc9110': r['abnf_one_block'] = any('Accept =' in b and 'Via =' in b for b in blocks)
        if doc == 'thinkpython2': r['operators_block_fenced'] = any('x != y' in b and 'x >= y' in b for b in blocks)
        r.update(table_stats(md))
        results[doc][tool] = r
json.dump(results, open(OUT_DIR + '/results.json', 'w'), indent=1)
for doc in DOCS:
    print(f'== {doc}')
    for tool in TOOLS:
        print(f'  {tool:12}', results[doc][tool])
