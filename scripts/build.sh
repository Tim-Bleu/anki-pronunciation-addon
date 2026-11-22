#!/usr/bin/env bash
# Build dist/pronunciation_tts.ankiaddon (install via Anki: Tools → Add-ons → Install from file)
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p dist
out="dist/pronunciation_tts.ankiaddon"
rm -f "$out"
(cd pronunciation_tts && zip -q -r "../$out" . -x "__pycache__/*" "*/__pycache__/*" "*.pyc" "meta.json")
echo "Built $out"
