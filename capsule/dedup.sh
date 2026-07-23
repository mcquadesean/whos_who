#!/bin/bash
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"
/opt/anaconda/bin/python dedup.py
