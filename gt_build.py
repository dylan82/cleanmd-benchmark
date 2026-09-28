import re, json, pymupdf
import os
HERE = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(HERE, 'pdfs')
GT_DIR = os.path.join(HERE, 'gt')
OUT_DIR = os.path.join(HERE, 'out')
out = {}
# Think Python: TOC lines come as triples: num / "title . . . ." / page
# The title line must start with a letter and each number counts once: with
# pymupdf ≥ 1.28 the page-number line of an entry lands right before the next
# entry's number, so "1" followed by "1.1" would otherwise read as an entry.
doc = pymupdf.open(PDF_DIR + '/thinkpython2.pdf'); secs = []; seen = set()
for p in range(12, 17):
    lines = [l.strip() for l in doc[p].get_text().split('\n')]
    for i, l in enumerate(lines):
        if re.fullmatch(r'\d+(?:\.\d+)?', l) and i + 1 < len(lines):
            t = re.sub(r'(?:\s*\.)+\s*$', '', lines[i + 1]).strip()
            if t and re.match(r'[A-Za-z]', t) and l not in seen:
                seen.add(l); secs.append({'num': l, 'title': t})
out['thinkpython2'] = {'sections': secs}
# SCOTUS markers: the part/sub-part markers (I, II, A, B, 1…) of the opinion of
# the Court, the Gorsuch concurrence and the Kagan dissent, read from the
# markup of the Cornell LII edition (https://www.law.cornell.edu/supremecourt/text/22-451,
# downloaded by run.sh into pdfs/scotus-lii.html, not redistributed): every
# marker is its own centered heading element there (h3.jy-center, and in two
# places h4.jy-center), inside the writing blocks OPINION_4, CONCUR_6 and
# DISSENT_7 (CONCUR_5, Thomas, has none). That list is the ground truth.
# The page geometry (single token centered at 11pt, the rule the first run of
# this benchmark used as ground truth) is kept only as a CROSS-CHECK and to
# attach page numbers: if the two sequences differ the build stops here.
import html as _html
LII = os.path.join(PDF_DIR, 'scotus-lii.html')
MARK = re.compile(r'^(?:I|II|III|IV|V|VI|[A-H]|[1-9])$')
WRITINGS = [('OPINION_4', 'opinion'), ('CONCUR_5', 'concurrence-thomas'), ('CONCUR_6', 'concurrence-gorsuch'), ('DISSENT_7', 'dissent')]
def _strip(s): return _html.unescape(re.sub(r'<[^>]+>', '', s)).replace('\xa0', ' ').strip()
def _level(tok): return 1 if re.fullmatch(r'[IVX]+', tok) else 2 if re.fullmatch(r'[A-H]', tok) else 3
page_html = open(LII, encoding='utf-8').read()
chunks = re.split(r'<[^>]+id="writing-22-451_([A-Z_0-9]+)"[^>]*>', page_html)
by_writing = {chunks[i]: chunks[i + 1] for i in range(1, len(chunks) - 1, 2)}
lii = []
for wid, name in WRITINGS:
    for m in re.finditer(r'<(h[1-6])\s+class="[^"]*jy-center[^"]*"[^>]*>(.*?)</\1>', by_writing.get(wid, ''), re.S):
        tok = _strip(m.group(2))
        if MARK.fullmatch(tok): lii.append({'text': tok, 'writing': name, 'level': _level(tok)})
if not lii: raise SystemExit('SCOTUS: no markers found in the LII HTML (layout changed?)')
doc = pymupdf.open(PDF_DIR + '/scotus.pdf'); geo = []
for p in range(doc.page_count):
    page = doc[p]; W = page.rect.width
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            spans = l['spans']; text = ''.join(s['text'] for s in spans).strip()
            if not MARK.fullmatch(text): continue
            if abs(spans[0]['size'] - 11) > 0.6: continue
            x0, x1 = l['bbox'][0], l['bbox'][2]
            if abs((x0 + x1) / 2 - W / 2) > 8: continue
            geo.append({'page': p + 1, 'text': text})
if [m['text'] for m in lii] != [g['text'] for g in geo]:
    raise SystemExit(f"SCOTUS: LII markers {[m['text'] for m in lii]} != page geometry {[g['text'] for g in geo]}")
markers = [{'page': g['page'], **m} for m, g in zip(lii, geo)]
out['scotus'] = {'markers': markers, 'source': 'Cornell LII HTML (centered heading elements per writing); page numbers from the PDF geometry, which matched the LII sequence 1:1'}
# BERT: bold (Medi) lines; number and title are separate lines → join
doc = pymupdf.open(PDF_DIR + '/bert.pdf'); secs = []
for p in range(doc.page_count):
    seq = []
    for b in doc[p].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            t = ''.join(s['text'] for s in l['spans']).strip(); f = l['spans'][0]['font']; sz = l['spans'][0]['size']
            if 'Medi' in f and sz >= 10.5 and len(t) < 90: seq.append(t)
    for i, t in enumerate(seq):
        m = re.fullmatch(r'(\d+(?:\.\d+)*|[A-E](?:\.\d+)*)', t)
        if m and i + 1 < len(seq) and re.match(r'^[A-Z]', seq[i + 1]): secs.append({'num': t, 'title': seq[i + 1]})
        m2 = re.match(r'^(\d+(?:\.\d+)*|[A-E](?:\.\d+)*)\s+([A-Z].+)$', t)
        if m2: secs.append({'num': m2.group(1), 'title': m2.group(2)})
out['bert'] = {'sections': secs}
# NIST: ToC (top-level + appendices)
doc = pymupdf.open(PDF_DIR + '/nist-cyber.pdf'); secs = []
for p in range(0, 8):
    for line in doc[p].get_text().split('\n'):
        m = re.match(r'^\s*(\d+(?:\.\d+)*)\.\s+(.+?)\s*(?:\.\s*){3,}\s*\d+\s*$', line)
        if m: secs.append({'num': m.group(1), 'title': m.group(2).strip()})
        m = re.match(r'^\s*(Appendix [A-Z])\.\s+(.+?)\s*(?:\.\s*){3,}\s*\d+\s*$', line)
        if m: secs.append({'num': m.group(1), 'title': m.group(2).strip()})
out['nist-cyber'] = {'sections': secs}
json.dump(out, open(GT_DIR + '/others.json', 'w'), indent=1, ensure_ascii=False)
for k, v in out.items(): print(k, {kk: len(vv) for kk, vv in v.items()}, list(v.values())[0][:3], list(v.values())[0][-2:])
