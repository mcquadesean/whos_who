"""Summarize the segmented volumes and pick one best copy per edition, so the expensive
LLM extraction runs once per edition, not once per duplicate scan.

Duplicate detection is content-aware: within a (series, year) group, volumes are clustered
by the SURNAME RANGE they cover. Multiple scans of the same single-volume edition share a
range (kept: the one with the most entries). A genuine multi-volume set (A-K vs L-Z, same
year, different people) has disjoint ranges -> all parts are kept.

Reads /media/secure_volume/parsed, copies the winners to /media/secure_volume/dedup.
Run: bash dedup.sh
"""
import csv
import glob
import os
import shutil
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PARSED = "/media/secure_volume/parsed"
DEDUP = "/media/secure_volume/dedup"

csv.field_size_limit(10 ** 8)


def enc(h):
    return h.replace(":", "+").replace("/", "=")


man = {}
for r in csv.DictReader(open(os.path.join(HERE, "whos_who_ht_manifest.csv"))):
    man[enc(r["htid"])] = (r["series_id"], r["year"])


def profile(path):
    surs = []
    n = 0
    for row in csv.DictReader(open(path, newline="")):
        n += 1
        s = (row.get("surname") or "").strip().upper()
        if s and s[0].isalpha():
            surs.append(s[0])
    surs.sort()
    if not surs:
        return n, None, None
    k = max(1, len(surs) // 20)
    return n, surs[k], surs[-k]           # 5th / 95th percentile first-letter


info = {}
for p in sorted(glob.glob(PARSED + "/*.csv")):
    base = os.path.basename(p)[:-4]
    enchtid, _, year = base.rpartition("_")
    sy = man.get(enchtid, ("?", year))
    n, lo, hi = profile(p)
    info[p] = (sy[0], sy[1], n, lo, hi)

# ---- summary ----
tot = sum(v[2] for v in info.values())
by_series = defaultdict(int)
zeros = []
for p, (sid, yr, n, lo, hi) in info.items():
    by_series[sid] += n
    if n == 0:
        zeros.append((sid, yr, os.path.basename(p)))
print("=== segmentation summary ===")
print("volumes: {}   total person entries: {:,}".format(len(info), tot))
print("by series:", {k: by_series[k] for k in sorted(by_series)})
print("zero-yield volumes: %d (index/supplement/mis-match — expected)" % len(zeros))

# ---- dedup ----
groups = defaultdict(list)
for p, (sid, yr, n, lo, hi) in info.items():
    if n > 0:
        groups[(sid, yr)].append((p, n, lo, hi))

kept, removed, multivol = [], 0, []
for (sid, yr), vols in groups.items():
    clusters = []
    for p, n, lo, hi in sorted(vols, key=lambda x: -x[1]):
        for cl in clusters:
            if lo and hi and cl["lo"] and cl["hi"] and max(lo, cl["lo"]) <= min(hi, cl["hi"]):
                cl["members"].append((p, n))
                break
        else:
            clusters.append({"lo": lo, "hi": hi, "members": [(p, n)]})
    if len(clusters) > 1:
        multivol.append((sid, yr, len(clusters)))
    for cl in clusters:
        best = max(cl["members"], key=lambda x: x[1])
        kept.append(best[0])
        removed += len(cl["members"]) - 1

os.makedirs(DEDUP, exist_ok=True)
for f in glob.glob(DEDUP + "/*.csv"):
    os.remove(f)
for p in kept:
    shutil.copy(p, DEDUP)
kept_entries = sum(info[p][2] for p in kept)

print("\n=== dedup result ===")
print("distinct editions kept: %d" % len(groups))
print("best copies kept: %d   duplicate scans removed: %d" % (len(kept), removed))
print("multi-volume editions (kept all parts): %d %s" % (len(multivol), multivol[:8]))
print("entries in kept set: {:,}  -> {}".format(kept_entries, DEDUP))
