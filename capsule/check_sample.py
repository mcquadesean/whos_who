"""Cross-volume drop check. Segments the earliest + latest volume of every series and
reports what the release filter would DROP — so we can verify nothing real is being lost
(esp. modern/terse entries that may lack b./s./m. markers). Prints the SHORTEST dropped
blocks (the ones most likely to be borderline real entries, not obvious paratext).

Run: bash check.sh
"""
import csv
import os
import re
import subprocess
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parse_whoswho as pw       # noqa: E402
import filter_release as fr      # noqa: E402

VOLS = "/media/secure_volume/vols"
MAXW = 250


def enc(h):
    return h.replace(":", "+").replace("/", "=")


print("indexing downloaded pages ...")
allpaths = subprocess.check_output('find %s -name "*.txt"' % VOLS,
                                   shell=True).decode().splitlines()


def find_dir(htid):
    e = enc(htid)
    for p in allpaths:
        if e in p:
            return os.path.dirname(p)
    return None


rows = [r for r in csv.DictReader(open(os.path.join(HERE, "whos_who_ht_manifest.csv")))
        if r["year"]]
by = defaultdict(list)
for r in rows:
    by[r["series_id"]].append(r)

sample = []
for sid, rs in sorted(by.items()):
    rs = sorted(rs, key=lambda r: int(r["year"]))
    for i in {0, len(rs) - 1}:
        sample.append(rs[i])

print("checking %d sample volumes (earliest + latest per series)\n" % len(sample))
dropped = []
per = []
for r in sample:
    d = find_dir(r["htid"])
    if not d:
        per.append((r["series_id"], r["year"], "MISSING-DIR", 0, 0))
        continue
    recs = pw.parse_volume(d, r["htid"], r["series_id"], r["year"])
    k = dr = 0
    for rec in recs:
        t = rec["raw_entry"]
        n = len(t.split())
        if n > MAXW and fr.is_prose(t):
            dr += 1
            dropped.append((n, r["series_id"], r["year"], re.sub(r"\s+", " ", t)[:100]))
        else:
            k += 1
    per.append((r["series_id"], r["year"], "ok", k, dr))

print("\n=== per-volume kept / dropped ===")
for sid, yr, st, k, dr in per:
    tag = "" if st == "ok" else st
    print("  %-6s %s  kept=%-7d dropped=%-4d %s" % (sid, yr, k, dr, tag))

show = min(45, len(dropped))
print("\n=== %d SHORTEST dropped blocks (the borderline ones) ===" % show)
print("(should all be paratext: geographic index / school ads. flag any that read as a real person)\n")
for n, sid, yr, prev in sorted(dropped)[:show]:
    print("  %dw [%s %s] %s" % (n, sid, yr, prev))
print("\ntotal dropped across %d sample volumes: %d" % (len(sample), len(dropped)))
