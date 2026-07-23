import csv
import os
from collections import defaultdict

PROC = "/gpfs/kellogg/proj/mke060/shared_sm/whos_who/data/processed"
EVID = os.path.join(PROC, "series_year_evidence.csv")
OUT = os.path.join(PROC, "whos_who_target_manifest.csv")

# Adjudicated ranges: triangulated observed range, cleaned with domain knowledge.
# fields: start, end, cadence, confidence, publisher, note
# cadence: annual | biennial | irregular
# Final target set: 11 Marquis series (shared biographical entry format).
RANGES = {
    "WWA":   (1899, 2026, "mixed",     "high",   "Marquis", "biennial 1899-1993, annual 1994+"),
    "WWE":   (1943, 2013, "biennial",  "high",   "Marquis", "regional; discontinued ~2013"),
    "WWW":   (1949, 2013, "biennial",  "high",   "Marquis", "regional"),
    "WWSSW": (1947, 2014, "biennial",  "high",   "Marquis", "regional"),
    "WWMW":  (1949, 2014, "biennial",  "high",   "Marquis", "regional"),
    "WWAW":  (1958, 2022, "biennial",  "high",   "Marquis", ""),
    "WWAL":  (1977, 2022, "biennial",  "high",   "Marquis", ""),
    "WWFB":  (1911, 1935, "irregular", "low",    "Marquis", "early Finance/Banking&Insurance; sparse, verify"),
    "WWCI":  (1936, 1965, "biennial",  "high",   "Marquis", "Commerce & Industry"),
    "WWFI":  (1972, 2002, "biennial",  "high",   "Marquis", "Finance & Industry; continuous numbering w/ WWCI"),
    "WWFBU": (2007, 2026, "biennial",  "medium", "Marquis", "Finance & Business"),
}

NAMES = {
    "WWA": "Who's Who in America", "WWWA": "Who Was Who in America",
    "IWWB": "Index to Who's Who Books", "WWE": "Who's Who in the East",
    "WWW": "Who's Who in the West", "WWSSW": "Who's Who in the South and Southwest",
    "WWMW": "Who's Who in the Midwest", "WWAW": "Who's Who of American Women",
    "WWFB": "Who's Who in Finance (Banking & Insurance)",
    "WWCI": "Who's Who in Commerce and Industry",
    "WWFI": "Who's Who in Finance and Industry",
    "WWFBU": "Who's Who in Finance and Business",
    "WWAL": "Who's Who in American Law",
    "WWSE": "Who's Who in Science and Engineering",
    "WWMH": "Who's Who in Medicine and Healthcare",
    "WWAE": "Who's Who in American Education", "WWENT": "Who's Who in Entertainment",
    "WWR": "Who's Who in Religion", "WWART": "Who's Who in American Art",
    "WWADV": "Who's Who in Advertising", "WWTECH": "Who's Who in Technology",
}


def load_evidence():
    obs = defaultdict(set)          # sid -> set(year)
    src = defaultdict(lambda: defaultdict(set))  # sid -> year -> set(source)
    if os.path.exists(EVID):
        for r in csv.DictReader(open(EVID, encoding="utf-8")):
            try:
                y = int(r["year"])
            except (ValueError, KeyError):
                continue
            obs[r["series_id"]].add(y)
            src[r["series_id"]][y].add(r["source"])
    return obs, src


def dominant_parity(years):
    odd = sum(1 for y in years if y % 2)
    even = sum(1 for y in years if not y % 2)
    return 1 if odd >= even else 0


def main():
    obs, src = load_evidence()
    rows = []
    uid = 0
    for sid, (start, end, cadence, conf, pub, note) in RANGES.items():
        years = sorted(y for y in obs.get(sid, set()) if start <= y <= end)
        par = dominant_parity(years) if years else None
        for year in range(start, end + 1):
            uid += 1
            observed = year in obs.get(sid, set())
            if cadence == "annual":
                expected = "yes"
            elif cadence == "biennial":
                expected = "yes" if (par is None or year % 2 == par or observed) else "off-year"
            elif cadence == "mixed":  # WWA: biennial pre-1994 then annual
                if year >= 1994:
                    expected = "yes"
                else:
                    expected = "yes" if (par is None or year % 2 == par or observed) else "off-year"
            else:  # irregular
                expected = "yes" if observed else "unknown"
            srcs = ";".join(sorted(src.get(sid, {}).get(year, [])))
            rows.append({
                "uid": uid,
                "book_year_id": f"{sid}-{year}",
                "series_id": sid,
                "series_name": NAMES[sid],
                "year": year,
                "cadence": cadence,
                "expected_edition": expected,
                "observed_in_sources": "yes" if observed else "no",
                "evidence_sources": srcs,
                "series_start": start,
                "series_end": end,
                "range_confidence": conf,
                "publisher": pub,
                "note": note,
                "acquired": "",
                "source_used": "",
                "file_id": "",
            })

    fields = ["uid", "book_year_id", "series_id", "series_name", "year", "cadence",
              "expected_edition", "observed_in_sources", "evidence_sources",
              "series_start", "series_end", "range_confidence", "publisher", "note",
              "acquired", "source_used", "file_id"]
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    n_exp = sum(1 for r in rows if r["expected_edition"] == "yes")
    n_obs = sum(1 for r in rows if r["observed_in_sources"] == "yes")
    print(f"wrote {len(rows)} book-year rows -> {OUT}")
    print(f"  expected editions: {n_exp}   |   already seen in >=1 source: {n_obs}")
    print(f"\n{'id':7} {'range':11} {'yrs':>4} {'exp':>4} {'obs':>4} {'conf':7} name")
    for sid, (start, end, cad, conf, pub, note) in RANGES.items():
        sr = [r for r in rows if r["series_id"] == sid]
        e = sum(1 for r in sr if r["expected_edition"] == "yes")
        o = sum(1 for r in sr if r["observed_in_sources"] == "yes")
        print(f"{sid:7} {str(start)+'-'+str(end):11} {len(sr):4} {e:4} {o:4} {conf:7} {NAMES[sid]}")


if __name__ == "__main__":
    main()
