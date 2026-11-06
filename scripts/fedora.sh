#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo '=== CIVITAS AI • Setup Fedora / Linux ==='
if ! command -v python3 >/dev/null; then
  echo 'Python 3 não encontrado. Instale com sudo dnf install python3 python3-pip' >&2
  exit 1
fi
python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    sys.exit('Este projeto requer Python 3.10 ou superior')
print('Python', sys.version.split()[0], 'detectado')
PY
if [[ ! -d .venv ]]; then
  python3 -m venv .venv || { echo 'Falha no venv. Verifique instalação do Python.' >&2; exit 1; }
fi
.venv/bin/python -m pip install -r requirements-dev.txt
if [[ ! -f .env ]]; then cp .env.example .env; fi
if [[ $# -gt 1 ]] || [[ $# -gt 0 && "$1" != '--check' && "$1" != '--prepare' ]]; then
  echo 'Uso: bash scripts/fedora.sh [--check|--prepare]' >&2
  exit 2
fi
if [[ "${1:-}" == '--prepare' ]]; then
  printf '\n[CIVITAS] Ambiente configurado. A auditoria será executada uma única vez antes da publicação.\n'
  exit 0
fi
if [[ "${1:-}" == '--check' ]]; then
  bash scripts/prepublish.sh
  exit 0
fi
.venv/bin/python -m pytest -q
printf '\nInterface: http://127.0.0.1:8000\nSwagger: http://127.0.0.1:8000/api/docs\nPressione Ctrl+C para sair.\n\n'
exec .venv/bin/python -m uvicorn app.main:app --env-file .env --host 127.0.0.1 --port 8000
