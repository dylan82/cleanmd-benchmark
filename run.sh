#!/usr/bin/env bash
# Benchmark PDF → Markdown (R3D-801): riproduce da zero i numeri della pagina
# /benchmarks/pdf-to-markdown. Tutto pubblico e deterministico: 5 PDF
# scaricati dalle fonti originali, 3 convertitori eseguiti in locale,
# ground truth costruita dai sommari ufficiali (RFC .txt, ToC dei PDF) o
# dal markup dell'edizione Cornell LII (SCOTUS), punteggi calcolati da score_all.py.
#
# Prerequisiti: node (repo installato con `npm install`), python3 ≥ 3.10,
# curl. I convertitori concorrenti finiscono in un venv locale.
# Uso: scripts/benchmark/run.sh           (≈ 2 minuti, ~30 MB di download)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
PDFS="$HERE/pdfs"; OUT="$HERE/out"; VENV="$HERE/.venv"
mkdir -p "$PDFS" "$OUT"

# 1. Corpus: documenti pubblici, generi diversi, nessuno scelto a posteriori.
# (liste parallele, non array associativi: il bash 3.2 di macOS non li ha)
NAMES="rfc9110 bert thinkpython2 scotus nist-cyber"
url_of() {
  case "$1" in
    rfc9110) echo "https://www.rfc-editor.org/rfc/rfc9110.pdf" ;;
    bert) echo "https://arxiv.org/pdf/1810.04805" ;;
    thinkpython2) echo "https://greenteapress.com/thinkpython2/thinkpython2.pdf" ;;
    scotus) echo "https://www.supremecourt.gov/opinions/23pdf/22-451_7m58.pdf" ;;
    nist-cyber) echo "https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf" ;;
  esac
}
fetch() { # fetch <url> <dest>: fallisce su HTTP ≥ 400 e se il file non è un PDF
  curl -sSfL -A "Mozilla/5.0" -o "$2" "$1"
  head -c 5 "$2" | grep -q '%PDF-' || { echo "non è un PDF: $1" >&2; rm -f "$2"; exit 1; }
}
for name in $NAMES; do
  [ -s "$PDFS/$name.pdf" ] || fetch "$(url_of "$name")" "$PDFS/$name.pdf"
done
[ -s "$PDFS/rfc9110.txt" ] || curl -sSfL -o "$PDFS/rfc9110.txt" "https://www.rfc-editor.org/rfc/rfc9110.txt"
# SCOTUS ground truth: the Cornell LII edition of the opinion (HTML markup, see gt_build.py).
if [ ! -s "$PDFS/scotus-lii.html" ]; then
  curl -sSfL -A "Mozilla/5.0" -o "$PDFS/scotus-lii.html" "https://www.law.cornell.edu/supremecourt/text/22-451"
  grep -q 'LOPER BRIGHT ENTERPRISES v. RAIMONDO' "$PDFS/scotus-lii.html" || { echo "LII page unexpected" >&2; rm -f "$PDFS/scotus-lii.html"; exit 1; }
fi

# 2. Convertitori concorrenti (versioni bloccate: sono quelle della pagina).
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q "markitdown[pdf]==0.1.7" "pymupdf4llm==1.28.2"
fi
for name in $NAMES; do
  f="$PDFS/$name.pdf"
  { /usr/bin/time -p "$VENV/bin/markitdown" "$f" -o "$OUT/$name.markitdown.md"; } 2> "$OUT/$name.markitdown.time" || true
  { /usr/bin/time -p "$VENV/bin/python" -c "import pymupdf4llm; open('$OUT/$name.pymupdf4llm.md','w').write(pymupdf4llm.to_markdown('$f'))"; } 2> "$OUT/$name.pymupdf4llm.time" || true
done
# Pandoc non legge PDF (è solo formato di output): escluso per costruzione.

# 3. CleanMD: stesso motore del browser, eseguito in Node via vitest. Fuori
# da questo repo il motore non è disponibile: il kit pubblico include gli
# output CleanMD già prodotti (out/*.cleanmd.md); in alternativa convertire i
# PDF su https://cleanmd.dev (free) e salvare i .md in out/<nome>.cleanmd.md.
if [ -f "$ROOT/tests/benchmark/convert.test.ts" ]; then
  (cd "$ROOT" && BENCH=1 npx vitest run tests/benchmark/convert.test.ts >/dev/null)
fi

# 4. Ground truth indipendente + punteggi.
"$VENV/bin/python" "$HERE/gt_build.py"
"$VENV/bin/python" "$HERE/score_all.py"
cp "$OUT/results.json" "$HERE/results.json"
cp "$OUT/results.json" "$ROOT/src/lib/benchmark-results.json"
echo "Risultati in $HERE/results.json (copiati in src/lib/benchmark-results.json)"

# 5. Kit pubblico riproducibile, servito da cleanmd.dev (il repo è privato):
# script, ground truth, risultati e gli output CleanMD grezzi, così ogni
# claim della pagina è verificabile leggendo i .md.
KIT="$ROOT/public/benchmarks/cleanmd-benchmark-kit.zip"
mkdir -p "$(dirname "$KIT")"; rm -f "$KIT"
(cd "$HERE/.." && zip -qr "$KIT" benchmark/README.md benchmark/run.sh benchmark/gt_build.py benchmark/score_all.py benchmark/gt benchmark/results.json benchmark/out/*.cleanmd.md -x "benchmark/.venv/*")
echo "Kit pubblico: $KIT"
