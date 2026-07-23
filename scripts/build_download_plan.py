import csv
import os
from collections import Counter

PROC = "/gpfs/kellogg/proj/mke060/shared_sm/whos_who/data/processed"
MANIFEST = os.path.join(PROC, "whos_who_target_manifest.csv")
PLAN = os.path.join(PROC, "whos_who_download_plan.csv")
HT_WORKSET = os.path.join(PROC, "htrc_workset_whoswho.txt")
LIBGEN_LIST = os.path.join(PROC, "worklist_libgen.csv")
IA_OPEN_LIST = os.path.join(PROC, "worklist_ia_open.csv")

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


def assign(r):
    """Deadline-aware: use free non-HT sources when possible (they don't expire);
    reserve HathiTrust (ends Sept 2026) for editions only it can provide."""
    avail = r.get("availability", "none")
    ht = r.get("ht_rights", "none")
    if avail == "libgen":
        return "2_free", "libgen", r.get("file_id", ""), \
            "https://libgen.li/ads.php?md5=" + r.get("file_id", "")
    if avail == "ia_open":
        return "2_free", "ia_open", r.get("file_id", ""), \
            "https://archive.org/details/" + r.get("file_id", "")
    if ht in ("pd", "ic"):
        tag = "1_urgent_ht" if ht == "ic" else "1_urgent_ht_pd"
        return tag, "ht_capsule", r.get("ht_htid", ""), \
            "https://babel.hathitrust.org/cgi/pt?id=" + r.get("ht_htid", "")
    if avail == "ia_restricted":
        return "3_ia_borrow", "ia_borrow", r.get("file_id", ""), \
            "https://archive.org/details/" + r.get("file_id", "")
    return "4_missing", "none", "", ""


def main():
    rows = list(csv.DictReader(open(MANIFEST, encoding="utf-8")))
    exp = [r for r in rows if r["expected_edition"] == "yes"]

    plan = []
    for r in exp:
        tier, src, tid, url = assign(r)
        plan.append({
            "uid": r["uid"], "book_year_id": r["book_year_id"],
            "series_id": r["series_id"], "series_name": NAMES.get(r["series_id"], ""),
            "year": r["year"], "tier": tier, "primary_source": src,
            "target_id": tid, "url": url,
            "also_libgen": r.get("n_libgen", "0"),
            "also_ia_open": r.get("n_ia_open", "0"),
            "also_ia_restricted": r.get("n_ia_restricted", "0"),
            "ht_rights": r.get("ht_rights", "none"),
        })

    with open(PLAN, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(plan[0].keys()))
        w.writeheader()
        w.writerows(plan)

    # HT capsule workset: unique htids for every HT-covered target edition
    ht_ids = []
    seen = set()
    for r in exp:
        h = r.get("ht_htid", "")
        if h and h not in seen:
            seen.add(h)
            ht_ids.append(h)
    with open(HT_WORKSET, "w", encoding="utf-8") as f:
        f.write("\n".join(ht_ids) + ("\n" if ht_ids else ""))

    # urgent-only htids (editions where HT is the chosen primary source)
    urgent_ids = sorted({p["target_id"] for p in plan
                         if p["tier"].startswith("1_urgent_ht") and p["target_id"]})

    def dump(path, rows_, cols):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows_)

    dump(LIBGEN_LIST, [p for p in plan if p["primary_source"] == "libgen"],
         ["book_year_id", "series_id", "year", "target_id", "url"])
    dump(IA_OPEN_LIST, [p for p in plan if p["primary_source"] == "ia_open"],
         ["book_year_id", "series_id", "year", "target_id", "url"])

    tiers = Counter(p["tier"] for p in plan)
    print(f"download plan -> {PLAN}  ({len(plan)} expected editions)\n")
    order = ["1_urgent_ht", "1_urgent_ht_pd", "2_free", "3_ia_borrow", "4_missing"]
    labels = {
        "1_urgent_ht": "HT capsule, in-copyright  (URGENT - HT-only, ends Sept)",
        "1_urgent_ht_pd": "HT capsule, public-domain (URGENT - HT-only)",
        "2_free": "Free now (libgen / open Internet Archive)",
        "3_ia_borrow": "IA borrow-only (1-at-a-time, DRM)",
        "4_missing": "Not found anywhere yet",
    }
    for t in order:
        print(f"  {t:16} {tiers.get(t,0):4}  {labels[t]}")
    urgent = tiers.get("1_urgent_ht", 0) + tiers.get("1_urgent_ht_pd", 0)
    print(f"\n  >>> URGENT before Sept 2026: {urgent} editions from HT capsule")
    print(f"      workset written: {HT_WORKSET} "
          f"({len(ht_ids)} htids all HT-covered; {len(urgent_ids)} are HT-only/urgent)")

    print(f"\n{'id':7} {'urgent':>6} {'free':>5} {'borrow':>6} {'miss':>5}  name")
    for sid in NAMES:
        rs = [p for p in plan if p["series_id"] == sid]
        u = sum(1 for p in rs if p["tier"].startswith("1_urgent"))
        fr = sum(1 for p in rs if p["tier"] == "2_free")
        b = sum(1 for p in rs if p["tier"] == "3_ia_borrow")
        m = sum(1 for p in rs if p["tier"] == "4_missing")
        print(f"{sid:7} {u:6} {fr:5} {b:6} {m:5}  {NAMES[sid]}")


if __name__ == "__main__":
    main()
