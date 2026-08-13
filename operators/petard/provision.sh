#!/usr/bin/env bash
# petard setup: provision the frontier-independent local model.
#
# sysop runs this while the frontier IS up, so petard can answer when it is DOWN.
# The model is a small CPU sentence-transformer used only to SELECT among the
# capability cards (it never writes a command). It reuses system torch if present
# so the download stays small (~100MB), which matters on a full disk. Idempotent.
#
# Usage: provision.sh [runtime_dir] [model_name]
#   runtime_dir  where the local model venv lives   (default: ~/.local/share/petard)
#   model_name   sentence-transformer to pull       (default: all-MiniLM-L6-v2)
#
# After it runs, answer with:
#   "$runtime_dir/venv/bin/python" translate.py cards.json "<operator's words>"
set -euo pipefail
RUNTIME="${1:-$HOME/.local/share/petard}"
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
print("petard model ready:", sys.argv[1])
PY
echo "petard runtime python: $RUNTIME/venv/bin/python"
