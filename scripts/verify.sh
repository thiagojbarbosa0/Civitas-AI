#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
PYTHON="${PYTHON:-python3}"
if [[ -x .venv/bin/python ]]; then PYTHON=".venv/bin/python"; fi
printf '\n[CIVITAS] Python: %s\n' "$($PYTHON --version)"
"$PYTHON" -m compileall -q app tests training
"$PYTHON" -m pytest -q --cov=app --cov-report=term --cov-fail-under=85
"$PYTHON" training/finetune_lora.py --dry-run
if command -v node >/dev/null 2>&1; then
  node --check frontend/app.js
  echo '[CIVITAS] JavaScript: sintaxe válida'
else
  echo '[CIVITAS] Node.js ausente: teste de sintaxe JS ignorado (opcional).'
fi
# O lint é obrigatório na etapa de publicação; não declarar aprovação sem Ruff.
"$PYTHON" -m ruff check app tests
printf '\n[CIVITAS] Verificação local concluída. Integrações externas não estão cobertas.\n'
