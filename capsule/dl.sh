#!/bin/bash
# Run INSIDE the HTRC Data Capsule (secure mode) to download the Who's Who volumes.
# Prereq: ids.txt (337 htids) present in this directory; htrc toolkit configured.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST=/media/secure_volume/vols
mkdir -p "$DEST"
echo "downloading $(wc -l < "$HERE/ids.txt") volumes -> $DEST"
htrc download -o "$DEST" "$HERE/ids.txt"
echo "--- pages downloaded:"
find "$DEST" -name "*.txt" | wc -l
echo "--- volumes present:"
find "$DEST" -maxdepth 4 -name "*.txt" -printf '%h\n' | sort -u | wc -l
