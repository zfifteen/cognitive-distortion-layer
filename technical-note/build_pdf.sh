#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p export

python3 generate_figures.py

pandoc technical_note.md \
  --citeproc \
  --pdf-engine=xelatex \
  --output export/cdl-technical-note.pdf
