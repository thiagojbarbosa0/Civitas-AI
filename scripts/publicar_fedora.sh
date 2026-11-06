#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
printf '\n=== CIVITAS AI v1.3.1 - TESTAR E PUBLICAR EM thiagojbarbosa0 ===\n'
for cmd in python3 git gh; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Falta $cmd. Instale com: sudo dnf install -y python3 python3-pip git gh" >&2
    exit 1
  fi
done
if ! gh auth status >/dev/null 2>&1; then
  echo 'É necessário autenticar no GitHub (janela do navegador).'
  gh auth login --web --git-protocol https
fi
bash scripts/fedora.sh --prepare
bash scripts/publish_github.sh
