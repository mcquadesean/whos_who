"""Dump raw OCR lines from the volumes that collapsed to 0 entries, so we can see how
their name-headers are actually formatted (and why NAME_HEADER_RE misses them).
Run: bash peek.sh
"""
import csv
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VOLS = "/media/secure_volume/vols"
TARGETS = [("WWA", "2004"), ("WWW", "2008"), ("WWAW", "1959")]


def enc(h):
    return h.replace(":", "+").replace("/", "=")


allpaths = subprocess.check_output('find %s -name "*.txt"' % VOLS,
                                   shell=True).decode().splitlines()
rows = list(csv.DictReader(open(os.path.join(HERE, "whos_who_ht_manifest.csv"))))

for sid, year in TARGETS:
    m = [r for r in rows if r["series_id"] == sid and r["year"] == year]
    if not m:
        print("no manifest row for %s %s" % (sid, year))
        continue
    htid = m[0]["htid"]
    e = enc(htid)
    pages = sorted(p for p in allpaths if e in p and os.path.basename(p)[0].isdigit())
    print("\n" + "=" * 70)
    print("%s %s  htid=%s  (%d pages)" % (sid, year, htid, len(pages)))
    print("=" * 70)
    if not pages:
        print("  NO PAGES FOUND for this htid")
        continue
    mid = pages[len(pages) // 2]
    lines = [ln.rstrip() for ln in open(mid, errors="replace").read().splitlines() if ln.strip()]
    print("  mid page: %s  (%d non-empty lines)" % (os.path.basename(mid), len(lines)))
    for ln in lines[:35]:
        print("  | " + ln[:110])
