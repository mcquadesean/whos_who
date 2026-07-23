# Who's Who — HathiTrust Capsule Runbook

Extract structured biographical records from the 337 HathiTrust volumes (11 Marquis
series) before HathiTrust access ends **September 30, 2026**.

**Architecture (mirrors the approved S&P path):** the capsule only *segments* the
in-copyright OCR into per-person `raw_entry` blocks. HTRC already ruled the `raw_entry`
column is "wholly factual data, non-consumptive," so we **release the segmented CSVs** and
run the heavy 121-field LLM extraction on **KLC GPUs** — not on the capsule's slow CPU.

```
  CAPSULE (secure):  htrc download -> segment -> filter_release -> releaseresults
  HTRC review        (approves the raw_entry CSVs, ~48h)
  KLC (GPU):         download release -> vLLM + extract_whoswho_llm.py -> JSONL
```

## ⚠️ Capsule gotchas (from the S&P runs — read first)
- **To change modes, SHUT DOWN and RESTART from the portal — never the mode-switch
  button** (it bricked the capsule into an ERROR state that needed an HTRC admin reset).
  Verify the portal shows the expected mode before acting. `/media/secure_volume` persists.
- **`git pull` / model downloads need MAINTENANCE mode** (secure has no internet).
- **Paste is disabled in secure-mode VNC** — hand-type; keep commands short; no heredocs/`sed`.
- **In-capsule Python is `/opt/anaconda/bin/python`** (bare `python` is absent).
- HTRC release is a terminal tool, not a portal button: `releaseresults add <tar>` then
  `releaseresults done`.

---

## Phase A — Maintenance mode: get the kit
```
git clone https://github.com/mcquadesean/whos_who.git   # or: cd whos_who && git pull
cd whos_who/capsule
pip install tqdm
```

## Phase B — Secure mode: download + segment
```
./dl.sh                       # 337 vols -> /media/secure_volume/vols
```
Calibrate on ONE volume before the full run:
```
/opt/anaconda/bin/python inspect_volume.py /media/secure_volume/vols/<a-vol-dir> --n 20
```
Check the kept/dropped counts and that headers are real entries. If off, tweak
`NAME_HEADER_RE` in `parse_whoswho.py` (pull the fix from GitHub in maintenance mode).
Then segment everything:
```
PY=/opt/anaconda/bin/python ./segment_all.sh    # -> /media/secure_volume/parsed
```

## Phase C — Secure mode: filter + release
```
/opt/anaconda/bin/python filter_release.py --max-words 350
```
Inspect the "longest DROPPED" (should all be paratext) and "longest KEPT" (should be real
prolific bios, not clipped); adjust `--max-words` if needed. Then bundle + submit:
```
cd /media/secure_volume && tar czf ~/whoswho_raw.tar.gz -C release .
releaseresults add ~/whoswho_raw.tar.gz
releaseresults done
```
HTRC reviews (~48h); approval email → download link.

## Phase D — KLC (GPU): extract
Stage the approved CSVs, set up the env once, then run the extractor over them:
```
mkdir -p /gpfs/kellogg/proj/mke060/shared_sm/whos_who/data/processed/released_csv
#   (extract the downloaded tarball into released_csv/)
bash ~/mcquade_projects/whos_who/jobs/setup_vllm_env.sh        # one-time
sbatch ~/mcquade_projects/whos_who/jobs/run_extract.sh         # serves vLLM + extracts all
```
Output: `data/processed/llm_out/*.jsonl` (nested records + `raw_entry`), resumable.
Downstream: filter `is_person_entry`, then dedupe people across editions.

---

**Priority:** the 1930s–1980s in-copyright run exists *only* in HathiTrust and disappears
Sept 30 — get those series (regionals, Finance & Industry) downloaded + segmented + released
first, so they clear review before the deadline. KLC extraction has no deadline.
