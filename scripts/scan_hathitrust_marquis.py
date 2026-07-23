import csv
import gzip
import re
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else \
    "/gpfs/kellogg/proj/mke060/shared_sm/whos_who/data/raw/hathi_full.txt.gz"
OUT = "/gpfs/kellogg/proj/mke060/shared_sm/whos_who/data/processed/marquis_observed_volumes.csv"

COLS = ["htid", "access", "rights", "ht_bib_key", "description", "source",
        "source_bib_num", "oclc_num", "isbn", "issn", "lccn", "title", "imprint",
        "rights_reason_code", "rights_timestamp", "us_gov_doc_flag",
        "rights_date_used", "pub_place", "lang", "bib_fmt", "collection_code",
        "content_provider_code", "responsible_entity_code",
        "digitization_agent_code", "access_profile_code", "author"]

# ordered most-specific first; first match wins
SERIES = [
    ("WWFI",   "Who's Who in Finance and Industry",        r"whos who in finance and industry"),
    ("WWFBU",  "Who's Who in Finance and Business",        r"whos who in finance and business"),
    ("WWCI",   "Who's Who in Commerce and Industry",       r"whos who in commerce and industry"),
    ("WWFB",   "Who's Who in Finance (Banking & Insurance)", r"whos who in finance,? ?(and )?bank|whos who in finance,? ?banking|whos who in finance and insurance|whos who in finance(?!\s+and\s+(industry|business))"),
    ("WWWA",   "Who Was Who in America",                   r"who was who in america"),
    ("IWWB",   "Index to Who's Who Books",                 r"index to whos who"),
    ("WWA",    "Who's Who in America",                     r"whos who in america(?!n)"),
    ("WWE",    "Who's Who in the East",                    r"whos who in the east"),
    ("WWW",    "Who's Who in the West",                    r"whos who in the west"),
    ("WWSSW",  "Who's Who in the South and Southwest",     r"whos who in the south"),
    ("WWMW",   "Who's Who in the Midwest",                 r"whos who in the midwest"),
    ("WWAW",   "Who's Who of American Women",              r"whos who of american women|whos who in american women"),
    ("WWAL",   "Who's Who in American Law",                r"whos who in american law"),
    ("WWSE",   "Who's Who in Science and Engineering",     r"whos who in science and engineering"),
    ("WWMH",   "Who's Who in Medicine and Healthcare",     r"whos who in medicine and health"),
    ("WWAE",   "Who's Who in American Education",          r"whos who in american education"),
    ("WWENT",  "Who's Who in Entertainment",               r"whos who in entertainment"),
    ("WWR",    "Who's Who in Religion",                    r"whos who in religion"),
    ("WWART",  "Who's Who in American Art",                r"whos who in american art"),
    ("WWADV",  "Who's Who in Advertising",                 r"whos who in advertising"),
    ("WWTECH", "Who's Who in Technology",                  r"whos who in technology"),
]
SERIES = [(sid, name, re.compile(pat)) for sid, name, pat in SERIES]


def norm(t):
    t = (t or "").lower().replace("'", "").replace("’", "").replace("`", "")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ,]", " ", t)).strip()


def classify(title):
    n = norm(title)
    for sid, name, pat in SERIES:
        if pat.search(n):
            return sid, name
    return None, None


def year_of(imprint, rights_date):
    for src in (imprint, rights_date):
        if not src:
            continue
        yrs = re.findall(r"\b(1[89]\d\d|20[0-2]\d)\b", src)
        if yrs:
            return int(yrs[-1])
    return None


def main():
    n_total = n_match = 0
    rows = []
    op = gzip.open(SRC, "rt", encoding="utf-8", errors="replace")
    for line in op:
        n_total += 1
        p = line.rstrip("\n").split("\t")
        if len(p) < 26:
            continue
        r = dict(zip(COLS, p))
        sid, name = classify(r["title"])
        if not sid:
            continue
        n_match += 1
        yr = year_of(r["imprint"], r["rights_date_used"])
        is_marquis = "marquis" in (r["imprint"] or "").lower() or \
                     "marquis" in (r["author"] or "").lower()
        rows.append({
            "series_id": sid, "series_name": name, "year": yr or "",
            "htid": r["htid"], "rights": r["rights"], "lang": r["lang"],
            "is_marquis": "yes" if is_marquis else "no",
            "title": r["title"], "imprint": r["imprint"],
        })
    op.close()

    fields = ["series_id", "series_name", "year", "htid", "rights", "lang",
              "is_marquis", "title", "imprint"]
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"scanned {n_total:,} HT rows -> {n_match:,} title matches -> {OUT}")

    from collections import defaultdict
    agg = defaultdict(lambda: {"name": "", "years": [], "marq": 0, "n": 0})
    for r in rows:
        a = agg[r["series_id"]]
        a["name"] = r["series_name"]
        a["n"] += 1
        a["marq"] += 1 if r["is_marquis"] == "yes" else 0
        if r["year"]:
            a["years"].append(int(r["year"]))
    print(f"\n{'series':8} {'range(all)':14} {'range(marquis)':16} {'vols':>5} {'marq':>5}  name")
    order = [s[0] for s in SERIES]
    for sid in sorted(agg, key=lambda s: order.index(s) if s in order else 99):
        a = agg[sid]
        ys = sorted(a["years"])
        marq_ys = sorted(int(r["year"]) for r in rows
                         if r["series_id"] == sid and r["is_marquis"] == "yes" and r["year"])
        rng = f"{ys[0]}-{ys[-1]}" if ys else "—"
        mrng = f"{marq_ys[0]}-{marq_ys[-1]}" if marq_ys else "—"
        print(f"{sid:8} {rng:14} {mrng:16} {a['n']:5} {a['marq']:5}  {a['name']}")


if __name__ == "__main__":
    main()
