#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if ! command -v gh >/dev/null 2>&1; then
  echo 'Instale o GitHub CLI: sudo dnf install gh' >&2
  exit 1
fi
if ! command -v git >/dev/null 2>&1; then
  echo 'Instale Git: sudo dnf install git' >&2
  exit 1
fi
if ! gh auth status >/dev/null 2>&1; then
  echo 'Primeiro autentique: gh auth login' >&2
  exit 1
fi
# Faz a publicação APENAS na conta solicitada, nunca no usuário errado.
EXPECTED_LOGIN='thiagojbarbosa0'
CURRENT_LOGIN="$(gh api user --jq '.login')" || {
  echo 'Não foi possível confirmar a conta GitHub; abortando.' >&2
  exit 1
}
if [[ "$CURRENT_LOGIN" != "$EXPECTED_LOGIN" ]]; then
  echo "Conta conectada: $CURRENT_LOGIN. Esperada: $EXPECTED_LOGIN. Publicação cancelada." >&2
  exit 1
fi
echo "GitHub autenticado: $CURRENT_LOGIN"
# Não publicar acidentalmente dentro do repositório de outro projeto.
if [[ -d .git ]] && [[ "$(git rev-parse --show-toplevel)" != "$(pwd -P)" ]]; then
  echo 'Pasta contém outro repositório Git; publicação interrompida.' >&2
  exit 1
fi
if [[ -d .git ]] && git remote get-url origin >/dev/null 2>&1; then
  echo 'Já existe remote origin. Revise o repositório; nenhuma publicação automática será feita.' >&2
  exit 1
fi
if gh repo view "${EXPECTED_LOGIN}/Civitas-AI" >/dev/null 2>&1; then
  echo 'Um repositório Civitas-AI já existe nesta conta. Nenhuma alteração será feita nele.' >&2
  exit 1
fi
bash scripts/prepublish.sh
if [[ ! -d .git ]]; then git init -b main; fi
# Não requer git config global e usa e-mail noreply do GitHub, se necessário.
if ! git config user.name >/dev/null 2>&1; then
  git config user.name "$EXPECTED_LOGIN"
fi
if ! git config user.email >/dev/null 2>&1; then
  GH_ID="$(gh api user --jq '.id')"
  [[ "$GH_ID" =~ ^[0-9]+$ ]] || { echo 'ID GitHub inválido; abortando.' >&2; exit 1; }
  git config user.email "${GH_ID}+${EXPECTED_LOGIN}@users.noreply.github.com"
fi
git add -A
PYTHON="${PYTHON:-python3}"
[[ ! -x .venv/bin/python ]] || PYTHON=.venv/bin/python
"$PYTHON" scripts/audit_release.py --git-index
printf '\nARQUIVOS QUE SERÃO PUBLICADOS:\n'
git ls-files | sed -n '1,120p'
printf '\nVocê confirma que NÃO incluiu segredos, dados reais ou credenciais?\n'
read -r -p 'Para criar o repositório PÚBLICO, digite PUBLICAR: ' answer
if [[ "$answer" != 'PUBLICAR' ]]; then echo 'Cancelado, sem publicar.'; exit 0; fi
if ! git diff --cached --quiet || ! git rev-parse --verify HEAD >/dev/null 2>&1; then
  git commit -m 'feat: Civitas AI GovTech RAG portfolio v1.3.1'
fi
gh auth setup-git
gh repo create "${EXPECTED_LOGIN}/Civitas-AI" --public --source=. --remote=origin --push
printf '\nGitHub CLI concluiu o comando; confira a CI e as configurações do novo repositório.\n'
printf 'Repositório: https://github.com/%s/Civitas-AI\n' "$EXPECTED_LOGIN"
