#!/bin/bash
# Run the LLM extractor over every segmented CSV. Model server MUST be running
# (see runbook). Resumable per volume. Run INSIDE the capsule (secure mode).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${PY:-python3}"
PARSED=/media/secure_volume/parsed
OUT=/media/secure_volume/llm_out
SERVER="${SERVER:-http://localhost:8000}"
MODEL="${MODEL:-local}"
mkdir -p "$OUT"
cd "$HERE"

if ! curl -sf "$SERVER/v1/models" >/dev/null 2>&1; then
    echo "model server not reachable at $SERVER — start it first (see runbook)"; exit 1
fi

ok=0
for csv in "$PARSED"/*.csv; do
    [ -e "$csv" ] || continue
    base=$(basename "$csv" .csv)
    out="$OUT/${base}.jsonl"
    echo "=== $base ==="
    "$PY" extract_whoswho_llm.py --in "$csv" --out "$out" --server "$SERVER" --model "$MODEL"
    ok=$((ok+1))
done
echo; echo "extracted $ok volume(s) -> $OUT"
