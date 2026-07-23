# Who's Who — HathiTrust Capsule Runbook

Extract structured biographical records from the 337 HathiTrust volumes (11 Marquis
series) **inside the HTRC Data Capsule**, before HathiTrust access ends **September 2026**.

Because the volumes are in-copyright, OCR text cannot leave the capsule — segmentation
**and** LLM extraction both run inside it; only the derived JSONL is exported (via HTRC
export review).

Files in this directory:
- `ids.txt` — 337 htids (all HT volumes across the 11 series)
- `whos_who_ht_manifest.csv` — htid, series_id, year, rights, title
- `dl.sh` — download volumes → `/media/secure_volume/vols`
- `parse_whoswho.py` — page → per-person entry segmenter
- `inspect_volume.py` — calibration: dump sample entries from one volume
- `segment_all.sh` — segment every volume → `/media/secure_volume/parsed`
- `extract_whoswho_llm.py` — full-schema LLM field extractor
- `extract_all.sh` — run extractor over every segmented CSV → `/media/secure_volume/llm_out`

---

## Phase A — Maintenance mode (internet on)

1. Clone the kit into the capsule:
   ```
   git clone https://github.com/mcquadesean/whos_who.git
   cd whos_who/capsule
   ```
2. Python deps: `pip install tqdm`  (segmenter needs only stdlib + tqdm).
3. Stand up a **local model server** for extraction (CPU, quantized — the capsule has no
   GPU). Reuse the in-capsule GGUF/llama.cpp setup from the S&P work:
   ```
   # e.g. llama.cpp server exposing an OpenAI-compatible endpoint on :8000
   ./server -m <model>.gguf --port 8000 -c 4096
   ```
   The heavier schema wants a capable instruct model; confirm quality on the calibration
   sample (Phase C) before the full run. Download the model weights now (needs internet).

## Phase B — Secure mode: download

4. Switch the capsule to **secure mode** and download the corpus:
   ```
   ./dl.sh
   ```
   Downloads all 337 volumes into `/media/secure_volume/vols`.

## Phase C — Calibrate (one volume)

5. Point `inspect_volume.py` at one downloaded volume and eyeball the segmentation:
   ```
   python inspect_volume.py /media/secure_volume/vols/<enc-htid-dir> --n 20
   ```
   If name-headers are being missed or noise is captured, tweak `NAME_HEADER_RE` /
   `RUNNING_HEADER_RE` in `parse_whoswho.py`. Then extract a few entries as a spot-check:
   ```
   python parse_whoswho.py <vol_dir> --htid <h> --series <S> --year <Y> --out /tmp/one.csv
   python extract_whoswho_llm.py --in /tmp/one.csv --out /tmp/one.jsonl --limit 10
   ```
   Inspect `/tmp/one.jsonl` — adjust the model or add few-shot examples to the prompt if
   fields are being missed. **Do not run the full set until this looks right.**

## Phase D — Full run

6. Segment everything, then extract:
   ```
   ./segment_all.sh
   SERVER=http://localhost:8000 MODEL=<name> ./extract_all.sh
   ```
   Both are resumable — re-run to continue after interruption.

## Phase E — Export

7. Output is `/media/secure_volume/llm_out/*.jsonl` (one file per volume, nested records +
   `raw_entry`). Request HTRC **export review** for the derived JSONL. Once out, land it in
   `/gpfs/kellogg/proj/mke060/shared_sm/whos_who/data/processed/` and dedupe people across
   editions downstream.

---

**Priority:** the ~1930s–1980s in-copyright run exists *only* here and disappears in
September — front-load those series (regionals, Finance & Industry) if capsule time is tight.
