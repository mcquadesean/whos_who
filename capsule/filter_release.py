"""Prepare HTRC release CSVs: from the segmented per-person CSVs, drop any long
paratext block (front/back-matter that slipped past the entry-signal gate) so only
factual person listings ship out for release review. Keeps the full data in
--in-dir untouched; writes a filtered copy to --out-dir.

Run INSIDE the capsule (secure mode) after segment_all.sh, before releaseresults.

Usage:
    python filter_release.py --max-words 350
Then inspect the "longest DROPPED" preview to confirm they are all paratext, and the
"longest KEPT" to confirm the cap isn't clipping real prolific bios; adjust --max-words.
"""
import argparse
import csv
import glob
import os

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(x, **k):
        return x


def word_count(text):
    return len(text.split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", default="/media/secure_volume/parsed")
    ap.add_argument("--out-dir", default="/media/secure_volume/release")
    ap.add_argument("--max-words", type=int, default=350,
                    help="drop any entry whose raw_entry exceeds this many words")
    ap.add_argument("--show", type=int, default=30)
    a = ap.parse_args()

    csv.field_size_limit(10 ** 7)
    os.makedirs(a.out_dir, exist_ok=True)
    files = sorted(glob.glob(os.path.join(a.in_dir, "*.csv")))

    g_in = g_out = 0
    dropped = []
    longest_kept = (0, "", "")
    for fp in tqdm(files, desc="files"):
        name = os.path.basename(fp)
        with open(fp, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fields = reader.fieldnames
        kept = []
        for row in rows:
            n = word_count(row.get("raw_entry", ""))
            if n > a.max_words:
                dropped.append((n, name, row.get("raw_entry", "")[:140]))
            else:
                kept.append(row)
                if n > longest_kept[0]:
                    longest_kept = (n, name, row.get("raw_entry", "")[:140])
        with open(os.path.join(a.out_dir, name), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(kept)
        print(f"{name}: {len(rows)} -> {len(kept)} (dropped {len(rows)-len(kept)})")
        g_in += len(rows)
        g_out += len(kept)

    print(f"\nTOTAL: {g_in} -> {g_out} (dropped {g_in-g_out}) at max_words={a.max_words}")
    print(f"longest KEPT: {longest_kept[0]}w [{longest_kept[1]}] {longest_kept[2]!r}")
    print(f"\n--- {a.show} longest DROPPED (verify these are all paratext) ---")
    for n, name, prev in sorted(dropped, reverse=True)[:a.show]:
        print(f"  {n}w [{name}] {prev!r}")


if __name__ == "__main__":
    main()
