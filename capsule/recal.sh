#!/bin/bash
# One-shot calibration: segment one downloaded volume + run the release filter,
# so we can eyeball kept vs dropped. Run in secure mode: bash recal.sh
HERE="$(cd "$(dirname "$0")" && pwd)"
PY=/opt/anaconda/bin/python
D=$(dirname "$(find /media/secure_volume/vols -name '*.txt' | head -1)")
echo "VOLUME: $D"
rm -rf /tmp/p /tmp/r; mkdir -p /tmp/p /tmp/r
cd "$HERE"
"$PY" parse_whoswho.py "$D" --htid cal --series WWA --year 1926 --out /tmp/p/test.csv
"$PY" filter_release.py --in-dir /tmp/p --out-dir /tmp/r --max-words 400
