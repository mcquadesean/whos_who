import csv
import os

PROC = "/gpfs/kellogg/proj/mke060/shared_sm/whos_who/data/processed"
HT = os.path.join(PROC, "marquis_observed_volumes.csv")
MANIFEST = os.path.join(PROC, "whos_who_target_manifest.csv")
PD = {"pd", "pdus"}

TARGET_SERIES = ["WWA", "WWE", "WWW", "WWSSW", "WWMW", "WWAW", "WWAL",
                 "WWFB", "WWCI", "WWFI", "WWFBU"]
NAMES = {
    "WWA": "Who's Who in America", "WWE": "Who's Who in the East",
    "WWW": "Who's Who in the West", "WWSSW": "Who's Who in the South and Southwest",
    "WWMW": "Who's Who in the Midwest", "WWAW": "Who's Who of American Women",
    "WWAL": "Who's Who in American Law",
    "WWFB": "Who's Who in Finance (Banking & Insurance)",
    "WWCI": "Who's Who in Commerce and Industry",
    "WWFI": "Who's Who in Finance and Industry",
    "WWFBU": "Who's Who in Finance and Business",
}


def main():
    # (series, year) -> best HT rights (pd preferred), and htid
    ht = {}
    ht_counts = {s: {"pd": 0, "ic": 0} for s in TARGET_SERIES}
    for r in csv.DictReader(open(HT, encoding="utf-8")):
        sid = r["series_id"]
        if sid not in TARGET_SERIES or not r["year"]:
            continue
        y = int(r["year"])
        is_pd = r["rights"] in PD
        ht_counts[sid]["pd" if is_pd else "ic"] += 1
        key = (sid, y)
        prev = ht.get(key)
        if prev is None or (is_pd and prev[0] != "pd"):
            ht[key] = ("pd" if is_pd else "ic", r["htid"])

    def ht_for(sid, year):
        best = None
        for dy in (0, -1, 1):
            v = ht.get((sid, year + dy))
            if v:
                if v[0] == "pd":
                    return v
                best = best or v
        return best

    rows = list(csv.DictReader(open(MANIFEST, encoding="utf-8")))
    fields = list(rows[0].keys())
    for c in ("ht_rights", "ht_htid"):
        if c not in fields:
            fields.insert(fields.index("acquired"), c)
    for r in rows:
        v = ht_for(r["series_id"], int(r["year"]))
        r["ht_rights"] = v[0] if v else "none"
        r["ht_htid"] = v[1] if v else ""
    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    exp = [r for r in rows if r["expected_edition"] == "yes"]

    def free_get(r):  # obtainable without the capsule
        return r["availability"] in ("libgen", "ia_open") or r["ht_rights"] == "pd"

    def any_get(r):   # obtainable including capsule / borrowing
        return free_get(r) or r["availability"] == "ia_restricted" or r["ht_rights"] == "ic"

    print("HathiTrust holdings for the 11 target series (all volumes):")
    print(f"{'id':7} {'HT_pd':>6} {'HT_ic':>6} {'HT_all':>7}  name")
    tot_pd = tot_ic = 0
    for s in TARGET_SERIES:
        pd_, ic_ = ht_counts[s]["pd"], ht_counts[s]["ic"]
        tot_pd += pd_
        tot_ic += ic_
        print(f"{s:7} {pd_:6} {ic_:6} {pd_+ic_:7}  {NAMES[s]}")
    print(f"{'TOTAL':7} {tot_pd:6} {tot_ic:6} {tot_pd+tot_ic:7}")

    print("\nTarget book-year coverage (expected editions = 411):")
    print(f"{'id':7} {'exp':>4} {'HTpd':>5} {'HTic':>5} {'free':>5} {'any':>4} {'gap':>4}  name")
    for s in TARGET_SERIES:
        rs = [r for r in exp if r["series_id"] == s]
        htpd = sum(1 for r in rs if r["ht_rights"] == "pd")
        htic = sum(1 for r in rs if r["ht_rights"] == "ic")
        fr = sum(1 for r in rs if free_get(r))
        an = sum(1 for r in rs if any_get(r))
        gap = len(rs) - an
        print(f"{s:7} {len(rs):4} {htpd:5} {htic:5} {fr:5} {an:4} {gap:4}  {NAMES[s]}")
    fr = sum(1 for r in exp if free_get(r))
    an = sum(1 for r in exp if any_get(r))
    htpd = sum(1 for r in exp if r["ht_rights"] == "pd")
    htic = sum(1 for r in exp if r["ht_rights"] == "ic")
    print(f"\nOF 411 EXPECTED EDITIONS:")
    print(f"  HathiTrust has:              {htpd+htic}   (pd={htpd}, in-copyright={htic})")
    print(f"  freely obtainable (no capsule): {fr}   [libgen + open-IA + HT-public-domain]")
    print(f"  obtainable incl. capsule/borrow: {an}")
    print(f"  still nowhere found:            {411 - an}")


if __name__ == "__main__":
    main()
