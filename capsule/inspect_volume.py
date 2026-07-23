"""Calibration helper: dump the first N segmented entry-blocks from a downloaded
volume so we can eyeball whether parse_whoswho's name-header detection is catching
real entries (and not header noise) BEFORE running the full extraction.

Usage (inside capsule, after dl.sh):
    python inspect_volume.py <volume_dir> [--n 15]
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import parse_whoswho as pw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("volume_dir")
    ap.add_argument("--n", type=int, default=15)
    a = ap.parse_args()
    paths = pw.page_files(a.volume_dir)
    print(f"{len(paths)} page files under {a.volume_dir}")
    lines = []
    for p in paths:
        lines.extend(p.read_text(errors="replace").splitlines())
    blocks = list(pw.iter_record_blocks(lines))
    print(f"segmented {len(blocks)} entry-blocks; showing first {a.n}:\n")
    for b in blocks[:a.n]:
        sur, giv, mid, suf = pw.split_name(b[0])
        print(f"[{sur} | {giv} {mid} {suf}]")
        print("  " + pw.join_block(b)[:400])
        print()


if __name__ == "__main__":
    main()
