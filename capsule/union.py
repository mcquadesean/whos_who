"""Build the release set = the corpus-wide UNION of unique entries.

One streaming pass over every segmented volume:
  - drop paratext (long prose: prefaces / ads / notices), via filter_release.is_prose
  - drop byte-identical duplicate entries across the WHOLE corpus (whitespace-normalized
    exact match) -> removes duplicate scans whose OCR happens to be identical

OCR-variant near-duplicates (same person, different OCR) are KEPT here on purpose and
reconciled later on the extracted structured fields. Per-volume output files are retained
(provenance + extraction parallelism), globally deduped. Low memory: only a set of hashes.

Reads /media/secure_volume/parsed -> writes /media/secure_volume/release
Run: bash union.sh
"""
import csv
import glob
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import filter_release as fr   # noqa: E402

csv.field_size_limit(10 ** 8)
PARSED = "/media/secure_volume/parsed"
OUT = "/media/secure_volume/release"
MAXW = 250

os.makedirs(OUT, exist_ok=True)
for f in glob.glob(OUT + "/*.csv"):
    os.remove(f)

seen = set()
tot = kept = para = dup = 0
for p in sorted(glob.glob(PARSED + "/*.csv")):
    out_rows = []
    with open(p, newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        for row in reader:
            tot += 1
            t = row.get("raw_entry", "")
            if len(t.split()) > MAXW and fr.is_prose(t):
                para += 1
                continue
            norm = re.sub(r"\s+", " ", t).strip()
            h = hashlib.md5(norm.encode("utf-8", "replace")).digest()
            if h in seen:
                dup += 1
                continue
            seen.add(h)
            out_rows.append(row)
            kept += 1
    with open(os.path.join(OUT, os.path.basename(p)), "w", newline="") as g:
        w = csv.DictWriter(g, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(out_rows)

print("=== release union ===")
print("total segmented entries:      {:,}".format(tot))
print("  dropped paratext (prose):   {:,}".format(para))
print("  dropped exact-dup entries:  {:,}".format(dup))
print("  UNIQUE entries kept:        {:,}".format(kept))
print("-> {} ({} volume files)".format(OUT, len(glob.glob(OUT + "/*.csv"))))
