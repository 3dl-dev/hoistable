#!/usr/bin/env bash
# arlo setup: provision the frontier-independent local model.
#
# Run this while the frontier IS up, so arlo can answer when the lights are out.
# The model runs on an independent path (local CPU, no frontier network).
#
# Rung 0 (retrieval) uses a small CPU sentence-transformer to SELECT among the
# capability cards; it never writes a command, so a weak model is fine. It reuses
# system torch if present so the download stays small (~100MB). Idempotent.
#
# Rungs 1+ (slot-fill and up) want a small instruct/coder model (a gguf served by
# llama.cpp) instead of an embedder, a different model class. That provisioning
# lands with those rungs; until then arlo's binder runs deterministically with no
# model (see arlo/binder.py), and slot-fill is honest about what it could not bind.
#
# Usage: provision.sh [runtime_dir] [model_name]
#   runtime_dir  where the local model venv lives   (default: ~/.local/share/arlo)
#   model_name   sentence-transformer to pull       (default: all-MiniLM-L6-v2)
#
# After it runs, answer with:
#   "$runtime_dir/venv/bin/python" -m arlo.translate cards.json "<your words>"
set -euo pipefail
RUNTIME="${1:-$HOME/.local/share/arlo}"
MODEL="${2:-all-MiniLM-L6-v2}"
mkdir -p "$RUNTIME"
if [ ! -x "$RUNTIME/venv/bin/python" ]; then
  python3 -m venv --system-site-packages "$RUNTIME/venv"
fi
"$RUNTIME/venv/bin/pip" install -q --disable-pip-version-check sentence-transformers
"$RUNTIME/venv/bin/python" - "$MODEL" <<'PY'
import sys
from sentence_transformers import SentenceTransformer
SentenceTransformer(sys.argv[1])
print("arlo model ready:", sys.argv[1])
PY
echo "arlo runtime python: $RUNTIME/venv/bin/python"
