import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scrape_libgen_universe as slu

UA = slu.UA
OUT = "/gpfs/kellogg/proj/mke060/shared_sm/whos_who/data/processed/target_series_coverage.csv"

TARGETS = {
    "whos_who_in_america": [
        "who's who in america",
    ],
    "finance_and_industry": [
        "who's who in finance and industry",
        "who's who in finance and business",
        "who's who in commerce and industry",
        "who's who in finance and banking",
        "who's who in finance, banking",
        "who's who in finance",
    ],
}


def decade(year):
    m = re.search(r"\b(1[89]\d\d|20[0-2]\d)\b", str(year or ""))
    return (int(m.group(1)) // 10 * 10) if m else 0


def libgen_hits(phrase, max_pages=8, sleep=0.7):
    rows = []
    empty = 0
    for page in range(1, max_pages + 1):
        try:
            html = slu.fetch('"%s"' % phrase, page)
        except Exception as e:
            print(f"    libgen '{phrase}' p{page}: {e}", file=sys.stderr)
            time.sleep(sleep * 2)
            continue
        got = slu.parse_rows(html)
        got = [r for r in got if slu.WHOSWHO_RE.search(r["title"])]
        if not got:
            empty += 1
            if empty >= 2:
                break
        else:
            empty = 0
            rows.extend(got)
        time.sleep(sleep)
    return rows


def ia_hits(phrase, max_rows=500):
    q = 'title:("%s") AND mediatype:texts' % phrase
    params = [("q", q), ("rows", str(max_rows)), ("output", "json")]
    for f in ("identifier", "year", "title", "access-restricted-item", "collection"):
        params.append(("fl[]", f))
    url = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode("utf-8", "replace"))
    return d["response"]["docs"]


def main():
    out_rows = []
    for series, variants in TARGETS.items():
        print(f"\n=== {series} ===")
        for phrase in variants:
            lg = libgen_hits(phrase)
            for r in lg:
                out_rows.append({
                    "series": series, "variant": phrase, "source": "libgen",
                    "id": r["md5"], "title": r["title"], "year": r["year"],
                    "decade": decade(r["year"]), "extension": r["extension"],
                    "size": r["size"], "open_download": "yes",
                })
            try:
                ia = ia_hits(phrase)
            except Exception as e:
                print(f"    IA '{phrase}': {e}", file=sys.stderr)
                ia = []
            for r in ia:
                restricted = str(r.get("access-restricted-item", "")).lower() == "true"
                out_rows.append({
                    "series": series, "variant": phrase, "source": "archive.org",
                    "id": r.get("identifier", ""),
                    "title": (r.get("title") or "")[:200],
                    "year": (str(r.get("year") or "")),
                    "decade": decade(r.get("year")), "extension": "",
                    "size": "", "open_download": "no" if restricted else "yes",
                })
            print(f"  '{phrase}': libgen={len(lg)}  IA={len(ia) if isinstance(ia,list) else 0}")

    seen = set()
    dedup = []
    for r in out_rows:
        k = (r["source"], r["id"])
        if r["id"] and k not in seen:
            seen.add(k)
            dedup.append(r)

    fields = ["series", "variant", "source", "id", "title", "year", "decade",
              "extension", "size", "open_download"]
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(dedup)
    print(f"\nwrote {len(dedup)} rows -> {OUT}")

    from collections import Counter
    for series in TARGETS:
        rows = [r for r in dedup if r["series"] == series]
        print(f"\n## {series}: {len(rows)} editions")
        by = {}
        for r in rows:
            d = r["decade"]
            by.setdefault(d, {"open": 0, "gated": 0})
            by[d]["open" if r["open_download"] == "yes" else "gated"] += 1
        for d in sorted(by):
            lbl = d if d else "unknown"
            print(f"   {lbl}: {by[d]['open']:3d} open  {by[d]['gated']:3d} gated")


if __name__ == "__main__":
    main()
