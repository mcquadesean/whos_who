#!/bin/bash
#SBATCH --job-name=ww_extract
#SBATCH --partition=gengpu
#SBATCH --gres=gpu:a100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=24:00:00
#SBATCH --output=/gpfs/home/hfa9391/mcquade_projects/whos_who/jobs/logs/extract_%j.out
#SBATCH --error=/gpfs/home/hfa9391/mcquade_projects/whos_who/jobs/logs/extract_%j.err

# Serve an instruct model with vLLM on the allocated GPU, then run the full-schema
# Who's Who extractor over every RELEASED raw_entry CSV. Resumable per volume
# (re-submit to continue). Runs on KLC — the raw_entry CSVs must already have cleared
# HTRC release review and been staged in $IN_DIR.
set -euo pipefail

PROJ=/gpfs/home/hfa9391/mcquade_projects/whos_who
DATA=/gpfs/kellogg/proj/mke060/shared_sm/whos_who/data/processed
IN_DIR="${IN_DIR:-$DATA/released_csv}"
OUT_DIR="${OUT_DIR:-$DATA/llm_out}"
MODEL="${MODEL:-Qwen/Qwen2.5-14B-Instruct}"
PORT="${PORT:-8000}"
SERVER="http://localhost:${PORT}"
mkdir -p "$OUT_DIR"

CONDA_SH="${CONDA_SH:-/software/miniconda3/4.12.0/etc/profile.d/conda.sh}"
source "$CONDA_SH"
conda activate ww_vllm

echo "serving $MODEL on :$PORT"
python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" --served-model-name "$MODEL" --port "$PORT" \
    --gpu-memory-utilization 0.92 --max-model-len 8192 --disable-log-requests \
    > "$PROJ/jobs/logs/vllm_${SLURM_JOB_ID}.log" 2>&1 &
VLLM_PID=$!
trap 'kill $VLLM_PID 2>/dev/null || true' EXIT

echo "waiting for vLLM..."
for i in $(seq 1 120); do
    curl -sf "$SERVER/v1/models" >/dev/null 2>&1 && { echo "up after ${i}0s"; break; }
    kill -0 $VLLM_PID 2>/dev/null || { echo "vLLM died; see jobs/logs/vllm_${SLURM_JOB_ID}.log"; exit 1; }
    sleep 10
done
curl -sf "$SERVER/v1/models" >/dev/null 2>&1 || { echo "vLLM not ready"; exit 1; }

n=0
for csv in "$IN_DIR"/*.csv; do
    [ -e "$csv" ] || continue
    base=$(basename "$csv" .csv)
    echo "=== $base ==="
    python "$PROJ/capsule/extract_whoswho_llm.py" \
        --in "$csv" --out "$OUT_DIR/${base}.jsonl" --server "$SERVER" --model "$MODEL"
    n=$((n+1))
done
echo "extraction complete: $n volume(s) -> $OUT_DIR"
