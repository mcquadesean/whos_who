#!/bin/bash
# Segment every downloaded volume into per-person entry CSVs. No model needed.
# Run INSIDE the capsule after dl.sh. Resumable (skips volumes already segmented).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${PY:-/opt/anaconda/bin/python}"
VOLS=/media/secure_volume/vols
OUT=/media/secure_volume/parsed
mkdir -p "$OUT"
cd "$HERE"

ok=0; miss=0; skip=0
while IFS=, read -r htid series year rights title; do
    [ "$htid" = "htid" ] && continue
    [ -z "$htid" ] && continue
    enc=$(echo "$htid" | sed 's/:/+/g; s|/|=|g')
    dir=$(dirname "$(find "$VOLS" -path "*$enc*" -name "*.txt" 2>/dev/null | head -1)")
    out="$OUT/${enc}_${year}.csv"
    if [ -z "$dir" ] || [ ! -d "$dir" ]; then
        echo "MISSING: $htid ($series $year)"; miss=$((miss+1)); continue
    fi
    if [ -s "$out" ]; then skip=$((skip+1)); continue; fi
    echo "=== $htid ($series $year) ==="
    "$PY" parse_whoswho.py "$dir" --htid "$htid" --series "$series" --year "$year" --out "$out"
    ok=$((ok+1))
done < whos_who_ht_manifest.csv
echo; echo "segmented: $ok | skipped(done): $skip | missing: $miss  -> $OUT"
