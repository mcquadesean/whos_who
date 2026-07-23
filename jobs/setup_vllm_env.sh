#!/bin/bash
# One-time setup of the vLLM serving env on KLC (login node). For the post-release
# extraction pass that runs on GPU over the released raw_entry CSVs.
set -e
CONDA_SH="${CONDA_SH:-/software/miniconda3/4.12.0/etc/profile.d/conda.sh}"
source "$CONDA_SH"
conda create -y -n ww_vllm python=3.10
conda activate ww_vllm
pip install --upgrade pip
pip install vllm tqdm
echo "env ww_vllm ready. activate with: conda activate ww_vllm"
