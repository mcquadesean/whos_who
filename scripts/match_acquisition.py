import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scrape_libgen_universe as slu  # noqa: E402
from scan_hathitrust_marquis import classify  # noqa: E402
from enumerate_year_ranges import SERIES as SERIES_VARIANTS, norm  # noqa: E402
from build_target_manifest import RANGES  # noqa: E402

PROC = "/gpfs/kellogg/proj/mke060/shared_sm/whos_who/data/processed"
MANIFEST = os.path.join(PROC, "whos_who_target_manifest.csv")
CANDS = os.path.join(PROC, "whos_who_file_candidates.csv")
UA = slu.UA
YMIN, YMAX = 1890, 2027

TARGETS = {sid: SERIES_VARIANTS[sid] for sid in RANGES if sid in SERIES_VARIANTS}


def one_year(s):
    import re
    ys = [int(y) for y in re.findall(r"\b(1[89]\d\d|20[0-2]\d)\b", str(s or ""))
          if YMIN <= int(y) <= YMAX]
    return ys[-1] if ys else None


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def universe_candidates():
    path = os.path.join(PROC, "whos_who_universe.csv")
    out = []
    if not os.path.exists(path):
        return out
    for r in csv.DictReader(open(path, encoding="utf-8")):
        sid = classify(r["title"])[0]
        if sid not in TARGETS:
            continue
        out.append({
            "series_id": sid, "source": "libgen", "file_id": r["md5"],
            "cand_year": one_year(r["year"]), "access": "open",
            "title": r["title"], "size": r.get("size", ""),
            "ext": r.get("extension", ""),
            "url": "https://libgen.li/ads.php?md5=" + r["md5"],
        })
    return out


def libgen_candidates(sid, variants, max_pages=8, sleep=0.6):
    out = {}
    for v in variants:
        empty = 0
        for page in range(1, max_pages + 1):
            try:
                html = slu.fetch('"%s"' % v, page)
            except Exception as e:
                print(f"  libgen {sid} '{v}' p{page}: {e}", file=sys.stderr)
                time.sleep(sleep * 2)
                continue
            rows = [r for r in slu.parse_rows(html) if slu.WHOSWHO_RE.search(r["title"])]
            if not rows:
                empty += 1
                if empty >= 2:
                    break
                time.sleep(sleep)
                continue
            for r in rows:
                if classify(r["title"])[0] != sid:
                    continue
                out[r["md5"]] = {
                    "source": "libgen", "file_id": r["md5"],
                    "cand_year": one_year(r["year"]), "access": "open",
                    "title": r["title"], "size": r["size"], "ext": r["extension"],
                    "url": "https://libgen.li/ads.php?md5=" + r["md5"],
                }
            time.sleep(sleep)
    return list(out.values())


def ia_candidates(sid, variants):
    out = {}
    for v in variants:
        q = 'title:("%s") AND mediatype:texts' % v
        url = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(
            [("q", q), ("rows", "1000"), ("output", "json"),
             ("fl[]", "identifier"), ("fl[]", "year"), ("fl[]", "title"),
             ("fl[]", "access-restricted-item"), ("fl[]", "format")])
        try:
            d = get_json(url)
        except Exception as e:
            print(f"  IA {sid} '{v}': {e}", file=sys.stderr)
            continue
        for doc in d["response"]["docs"]:
            if classify(doc.get("title", ""))[0] != sid:
                continue
            ident = doc.get("identifier", "")
            if not ident:
                continue
            restricted = str(doc.get("access-restricted-item", "")).lower() == "true"
            out[ident] = {
                "source": "archive.org", "file_id": ident,
                "cand_year": one_year(doc.get("year")),
                "access": "restricted" if restricted else "open",
                "title": (doc.get("title") or "")[:200], "size": "", "ext": "",
                "url": "https://archive.org/details/" + ident,
            }
        time.sleep(0.3)
    return list(out.values())


def ia_broad_sweep():
    """Harvest the whole Marquis 'who's who' pool on IA, classify each item into a
    target series (catches variant/subtitle catalogings the per-series phrase misses)."""
    out = []
    q = 'creator:(marquis) AND title:("who\'s who") AND mediatype:texts'
    url = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(
        [("q", q), ("rows", "2000"), ("output", "json"),
         ("fl[]", "identifier"), ("fl[]", "year"), ("fl[]", "title"),
         ("fl[]", "access-restricted-item")])
    try:
        d = get_json(url)
    except Exception as e:
        print(f"  IA broad sweep: {e}", file=sys.stderr)
        return out
    for doc in d["response"]["docs"]:
        sid = classify(doc.get("title", ""))[0]
        if sid not in TARGETS:
            continue
        ident = doc.get("identifier", "")
        if not ident:
            continue
        restricted = str(doc.get("access-restricted-item", "")).lower() == "true"
        out.append({
            "series_id": sid, "source": "archive.org", "file_id": ident,
            "cand_year": one_year(doc.get("year")),
            "access": "restricted" if restricted else "open",
            "title": (doc.get("title") or "")[:200], "size": "", "ext": "",
            "url": "https://archive.org/details/" + ident,
        })
    return out


def main():
    dedup = {}
    for c in universe_candidates():
        dedup[(c["source"], c["file_id"])] = c
    n_universe = len(dedup)
    n_broad = 0
    for c in ia_broad_sweep():
        dedup[(c["source"], c["file_id"])] = c
        n_broad += 1
    for sid, (name, variants) in TARGETS.items():
        lg = libgen_candidates(sid, variants)
        ia = ia_candidates(sid, variants)
        for c in lg + ia:
            c["series_id"] = sid
            dedup[(c["source"], c["file_id"])] = c
        print(f"{sid:7} libgen={len(lg):3}  IA={len(ia):3}  "
              f"(IA open={sum(1 for c in ia if c['access']=='open')})")
    print(f"(+{n_universe} libgen from universe scrape, +{n_broad} from IA Marquis broad sweep)")
    all_cands = list(dedup.values())

    with open(CANDS, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["series_id", "cand_year", "source", "access",
                                          "file_id", "title", "size", "ext", "url"],
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(all_cands, key=lambda c: (c["series_id"], c["cand_year"] or 0)))
    print(f"\nwrote {len(all_cands)} candidate files -> {CANDS}")

    by_series = {}
    for c in all_cands:
        by_series.setdefault(c["series_id"], []).append(c)

    def pick(sid, year):
        cands = [c for c in by_series.get(sid, [])
                 if c["cand_year"] is not None and abs(c["cand_year"] - year) <= 1]
        n_lg = sum(1 for c in cands if c["source"] == "libgen")
        n_iao = sum(1 for c in cands if c["source"] == "archive.org" and c["access"] == "open")
        n_iar = sum(1 for c in cands if c["source"] == "archive.org" and c["access"] == "restricted")
        # priority: exact-year first, then libgen > ia-open > ia-restricted
        order = {"libgen": 0, "ia_open": 1, "ia_restricted": 2}
        def key(c):
            tier = "libgen" if c["source"] == "libgen" else (
                "ia_open" if c["access"] == "open" else "ia_restricted")
            return (abs(c["cand_year"] - year), order[tier])
        best = min(cands, key=key) if cands else None
        if not cands:
            avail = "none"
        elif n_lg:
            avail = "libgen"
        elif n_iao:
            avail = "ia_open"
        else:
            avail = "ia_restricted"
        return avail, best, n_lg, n_iao, n_iar

    rows = list(csv.DictReader(open(MANIFEST, encoding="utf-8")))
    extra = ["availability", "n_libgen", "n_ia_open", "n_ia_restricted"]
    for r in rows:
        avail, best, n_lg, n_iao, n_iar = pick(r["series_id"], int(r["year"]))
        r["availability"] = avail
        r["n_libgen"], r["n_ia_open"], r["n_ia_restricted"] = n_lg, n_iao, n_iar
        if best:
            r["source_used"] = best["source"]
            r["file_id"] = best["file_id"]
    fields = list(rows[0].keys())
    for e in extra:
        if e not in fields:
            fields.insert(fields.index("acquired"), e)
    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    exp = [r for r in rows if r["expected_edition"] == "yes"]
    def cnt(rs, a):
        return sum(1 for r in rs if r["availability"] == a)
    print("\n=== acquisition coverage (expected editions only) ===")
    print(f"{'id':7} {'exp':>4} {'libgen':>6} {'ia_open':>7} {'ia_rest':>7} {'none':>5}  name")
    from build_target_manifest import NAMES
    for sid in TARGETS:
        rs = [r for r in exp if r["series_id"] == sid]
        print(f"{sid:7} {len(rs):4} {cnt(rs,'libgen'):6} {cnt(rs,'ia_open'):7} "
              f"{cnt(rs,'ia_restricted'):7} {cnt(rs,'none'):5}  {NAMES[sid]}")
    print(f"\nTOTAL expected={len(exp)}  obtainable(libgen+ia_open)="
          f"{cnt(exp,'libgen')+cnt(exp,'ia_open')}  "
          f"restricted={cnt(exp,'ia_restricted')}  none={cnt(exp,'none')}")


if __name__ == "__main__":
    main()
