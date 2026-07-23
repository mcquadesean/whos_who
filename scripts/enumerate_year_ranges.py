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
from scan_hathitrust_marquis import norm, classify  # noqa: E402

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124 Safari/537.36")
PROC = "/gpfs/kellogg/proj/mke060/shared_sm/whos_who/data/processed"
LIBGEN_UNIVERSE = os.path.join(PROC, "whos_who_universe.csv")
OUT_EVID = os.path.join(PROC, "series_year_evidence.csv")

YMIN, YMAX = 1890, 2027

# series_id -> (display name, [search variants])
SERIES = {
    "WWA":   ("Who's Who in America", ["who's who in america"]),
    "WWWA":  ("Who Was Who in America", ["who was who in america"]),
    "IWWB":  ("Index to Who's Who Books", ["index to who's who books", "index to who's who"]),
    "WWE":   ("Who's Who in the East", ["who's who in the east"]),
    "WWW":   ("Who's Who in the West", ["who's who in the west"]),
    "WWSSW": ("Who's Who in the South and Southwest", ["who's who in the south and southwest", "who's who in the south"]),
    "WWMW":  ("Who's Who in the Midwest", ["who's who in the midwest"]),
    "WWAW":  ("Who's Who of American Women", ["who's who of american women", "who's who in american women"]),
    "WWFB":  ("Who's Who in Finance (Banking & Insurance)", ["who's who in finance and banking", "who's who in finance, banking and insurance", "who's who in finance"]),
    "WWCI":  ("Who's Who in Commerce and Industry", ["who's who in commerce and industry"]),
    "WWFI":  ("Who's Who in Finance and Industry", ["who's who in finance and industry"]),
    "WWFBU": ("Who's Who in Finance and Business", ["who's who in finance and business"]),
    "WWAL":  ("Who's Who in American Law", ["who's who in american law"]),
    "WWSE":  ("Who's Who in Science and Engineering", ["who's who in science and engineering"]),
    "WWMH":  ("Who's Who in Medicine and Healthcare", ["who's who in medicine and healthcare", "who's who in medicine and health care"]),
    "WWAE":  ("Who's Who in American Education", ["who's who in american education"]),
    "WWENT": ("Who's Who in Entertainment", ["who's who in entertainment"]),
    "WWR":   ("Who's Who in Religion", ["who's who in religion"]),
    "WWART": ("Who's Who in American Art", ["who's who in american art"]),
    "WWADV": ("Who's Who in Advertising", ["who's who in advertising"]),
    "WWTECH":("Who's Who in Technology", ["who's who in technology"]),
}


def yrs_in(s):
    return [int(y) for y in re.findall(r"\b(1[89]\d\d|20[0-2]\d)\b", str(s or ""))
            if YMIN <= int(y) <= YMAX]


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def openlibrary(variant):
    url = "https://openlibrary.org/search.json?" + urllib.parse.urlencode({
        "title": variant, "fields": "title,publish_year", "limit": "200"})
    d = get_json(url)
    out = []
    nv = norm(variant)
    for doc in d.get("docs", []):
        if nv not in norm(doc.get("title", "")):
            continue
        for y in doc.get("publish_year", []):
            if YMIN <= int(y) <= YMAX:
                out.append((int(y), doc.get("title", "")[:120]))
    return out


def archive_org(variant):
    q = 'title:("%s") AND mediatype:texts' % variant
    url = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(
        [("q", q), ("rows", "500"), ("output", "json"),
         ("fl[]", "identifier"), ("fl[]", "year"), ("fl[]", "title")])
    d = get_json(url)
    out = []
    nv = norm(variant)
    for doc in d["response"]["docs"]:
        if nv not in norm(doc.get("title", "")):
            continue
        for y in yrs_in(doc.get("year")):
            out.append((y, doc.get("identifier", "")))
    return out


def libgen_from_universe():
    by = {}
    if not os.path.exists(LIBGEN_UNIVERSE):
        return by
    for r in csv.DictReader(open(LIBGEN_UNIVERSE, encoding="utf-8")):
        sid, _ = classify(r["title"])
        if not sid:
            continue
        for y in yrs_in(r["year"]):
            by.setdefault(sid, []).append((y, r["md5"]))
    return by


def main():
    lg = libgen_from_universe()
    evid = []
    summary = {}
    for sid, (name, variants) in SERIES.items():
        years = {"openlibrary": [], "archive.org": [], "libgen": []}
        for v in variants:
            for fn, src in ((openlibrary, "openlibrary"), (archive_org, "archive.org")):
                try:
                    for y, ref in fn(v):
                        years[src].append(y)
                        evid.append({"series_id": sid, "series_name": name,
                                     "source": src, "year": y, "ref": ref, "variant": v})
                except Exception as e:
                    print(f"  {sid} {src} '{v}': {e}", file=sys.stderr)
                time.sleep(0.3)
        for y, ref in lg.get(sid, []):
            years["libgen"].append(y)
            evid.append({"series_id": sid, "series_name": name, "source": "libgen",
                         "year": y, "ref": ref, "variant": ""})
        summary[sid] = (name, years)

    with open(OUT_EVID, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["series_id", "series_name", "source",
                                          "year", "ref", "variant"])
        w.writeheader()
        w.writerows(evid)

    def rng(v):
        return f"{min(v)}-{max(v)}" if v else "—"
    print(f"\n{'id':7} {'OpenLibrary':13} {'Archive.org':13} {'Libgen':11} {'COMBINED':13}  name")
    for sid, (name, years) in SERIES_ordered(summary):
        allc = years["openlibrary"] + years["archive.org"] + years["libgen"]
        print(f"{sid:7} {rng(years['openlibrary']):13} {rng(years['archive.org']):13} "
              f"{rng(years['libgen']):11} {rng(allc):13}  {name}")
    print(f"\nevidence rows: {len(evid)} -> {OUT_EVID}")


def SERIES_ordered(summary):
    for sid in SERIES:
        if sid in summary:
            yield sid, summary[sid]


if __name__ == "__main__":
    main()
