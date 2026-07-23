#!/bin/bash
# Cross-volume drop check: bash check.sh
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
/opt/anaconda/bin/python check_sample.py
