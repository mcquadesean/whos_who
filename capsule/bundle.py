"""Split the release set into sub-1GB tarball parts for HTRC (single release file cap
is 1 GB). Packs the per-volume CSVs into balanced bins by size, tars+gzips each. Add each
part to the release spool, then `releaseresults done` once (reviewed together).

Run: bash bundle.sh
"""
import glob
import os
import subprocess

REL = "/media/secure_volume/release"
OUTDIR = "/media/secure_volume"          # more space than home
CAP = 1_700_000_000                       # 1.7 GB uncompressed/bin -> comfortably <1GB gz

files = [(os.path.basename(p), os.path.getsize(p)) for p in glob.glob(REL + "/*.csv")]
files.sort(key=lambda x: -x[1])
total = sum(s for _, s in files)
print("release: {} files, {:.1f} GB uncompressed".format(len(files), total / 1e9))

bins, sizes = [], []
for name, sz in files:
    for i in range(len(bins)):
        if sizes[i] + sz <= CAP:
            bins[i].append(name)
            sizes[i] += sz
            break
    else:
        bins.append([name])
        sizes.append(sz)

for old in glob.glob(os.path.expanduser("~/whoswho_raw*.tar.gz")) + \
           glob.glob(OUTDIR + "/whoswho_raw*.tar.gz"):
    os.remove(old)

print("packing into %d parts:" % len(bins))
parts = []
for i, names in enumerate(bins, 1):
    listf = "/tmp/bin%d.txt" % i
    with open(listf, "w") as f:
        f.write("\n".join(names) + "\n")
    out = "%s/whoswho_raw_%d.tar.gz" % (OUTDIR, i)
    subprocess.check_call(["tar", "czf", out, "-C", REL, "-T", listf])
    mb = os.path.getsize(out) / 1e6
    parts.append((out, mb))
    flag = "  <-- OVER 1GB!" if mb > 1000 else ""
    print("  part %d: %3d files -> %s  %.0f MB%s" % (i, len(names), out, mb, flag))

print("\nnow run (secure mode):")
for out, _ in parts:
    print("  releaseresults add %s" % out)
print("  releaseresults done")
