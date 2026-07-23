#!/bin/bash
# Run INSIDE the HTRC Data Capsule (secure mode) to download the Who's Who volumes.
# Uses download.py (SSL-verify-disabled wrapper) instead of `htrc download`, which
# fails with 'None None' due to the HTRC stale-cert verification error.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST=/media/secure_volume/vols
PY="${PY:-/opt/anaconda/bin/python}"
mkdir -p "$DEST"
"$PY" "$HERE/download.py" "$HERE/ids.txt" "$DEST"
echo "--- pages downloaded:"
find "$DEST" -name "*.txt" 2>/dev/null | wc -l
echo "--- volume dirs:"
find "$DEST" -maxdepth 4 -name "*.txt" -printf '%h\n' 2>/dev/null | sort -u | wc -l
