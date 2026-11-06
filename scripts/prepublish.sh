#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
printf '\n=== CIVITAS AI: PRÉ-PUBLICAÇÃO ===\n'
bash scripts/verify.sh
PYTHON="${PYTHON:-python3}"
[[ ! -x .venv/bin/python ]] || PYTHON=.venv/bin/python
"$PYTHON" -m scripts.smoke_http
"$PYTHON" scripts/audit_release.py
printf '\nVERIFICAÇÃO LOCAL OK. Ainda é necessário verificar interface em navegador, Docker, LLM e CI em máquina com esses recursos.\n'
