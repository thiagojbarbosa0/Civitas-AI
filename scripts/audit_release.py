"""Verifica artefatos de publicação sem imprimir credenciais. Falha fechado."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_NAMES = {'.env', 'id_rsa', 'id_ed25519', 'credentials.json', 'secrets.json', 'service-account.json'}
PRIVATE_SUFFIXES = {'.pem', '.key', '.p12', '.pfx', '.sqlite', '.db'}
PRIVATE_PARTS = {'.git', '.venv', 'venv', 'data', '__pycache__', '.pytest_cache', '.ruff_cache',
                 'node_modules', 'output', 'htmlcov'}
KEY_PATTERNS = [re.compile(x.encode(), re.IGNORECASE) for x in [
    r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    r'sk-proj-[A-Za-z0-9_-]{18,}',
    r'gh[psu]_[A-Za-z0-9]{30,}',
    r'gho_[A-Za-z0-9]{30,}',
    r'github_pat_[A-Za-z0-9_]{30,}',
    r'AKIA[0-9A-Z]{16}',
]]


def allowed_files():
    for p in ROOT.rglob('*'):
        if not p.is_file() or p.is_symlink():
            continue
        rel = p.relative_to(ROOT)
        if any(v in PRIVATE_PARTS for v in rel.parts) or '__MACOSX' in rel.parts:
            continue
        if any(part.startswith('.') and part not in {'.env.example', '.gitignore', '.dockerignore', '.github'}
               for part in rel.parts):
            continue
        if rel.suffix in {'.pyc', '.log', '.zip'}:
            continue
        yield rel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--git-index', action='store_true', help='Auditar exatamente o conteúdo preparado para commit')
    args = parser.parse_args()
    if args.git_index:
        result = subprocess.run(['git', 'ls-files', '--cached', '-z'], cwd=ROOT,
                                capture_output=True, check=True)
        names = [Path(n.decode()) for n in result.stdout.split(b'\0') if n]
        # Index: avalia os bytes PREPARADOS para commit, não versões alteradas no disco.
        staged = subprocess.run(['git', 'ls-files', '-s', '-z'], cwd=ROOT,
                                capture_output=True, check=True).stdout
        for entry in staged.split(b'\0'):
            if not entry:
                continue
            mode = entry.split(b' ', 1)[0]
            if mode not in {b'100644', b'100755'}:
                raise SystemExit('ERRO: symlink, submódulo ou modo Git inesperado no index')
    else:
        names = sorted(allowed_files())
    if not names:
        raise SystemExit('ERRO: nenhum arquivo identificado para publicação')

    for rel in names:
        if rel.is_absolute() or '..' in rel.parts or (not args.git_index and not (ROOT / rel).is_file()):
            raise SystemExit('ERRO: arquivo inválido no pacote')
        if not args.git_index and (ROOT / rel).is_symlink():
            raise SystemExit(f'ERRO: link simbólico inesperado: {rel}')
        if ((rel.name in PRIVATE_NAMES or
             (rel.name.startswith('.env.') and rel.name != '.env.example') or
             rel.suffix.lower() in PRIVATE_SUFFIXES or
             any(part in PRIVATE_PARTS for part in rel.parts))):
            raise SystemExit(f'ERRO: arquivo privado detectado: {rel}')
        if args.git_index:
            raw = subprocess.run(['git', 'show', f':{rel.as_posix()}'], cwd=ROOT,
                                 capture_output=True, check=True).stdout
        else:
            raw = (ROOT / rel).read_bytes()
        if len(raw) > 5_000_000:
            raise SystemExit(f'ERRO: arquivo grande inesperado: {rel}')
        if any(pattern.search(raw) for pattern in KEY_PATTERNS):
            raise SystemExit(f'ERRO: possível segredo detectado em {rel} (valor não exibido)')

    for required in ['README.md', 'LICENSE', 'Dockerfile', 'docker-compose.yml',
                     'app/main.py', 'app/agents.py', 'frontend/index.html',
                     'frontend/app.js', 'frontend/style.css', '.github/workflows/ci.yml',
                     'scripts/fedora.sh', 'scripts/verify.sh']:
        if Path(required) not in names:
            raise SystemExit(f'ERRO: arquivo essencial ausente: {required}')
    def load(path: str) -> bytes:
        if args.git_index:
            return subprocess.run(['git', 'show', ':' + path], cwd=ROOT,
                                  capture_output=True, check=True).stdout
        return (ROOT / path).read_bytes()

    html = load('frontend/index.html').decode('utf-8')
    for link in ['/assets/app.js', '/assets/style.css', '/assets/favicon.svg']:
        target = Path('frontend') / link.rsplit('/', 1)[-1]
        if link not in html or target not in names:
            raise SystemExit(f'ERRO: asset ausente ou sem referência: {link}')
    golden = json.loads(load('evals/golden.json'))
    seed = json.loads(load('app/knowledge/services.json'))
    known = {x['id'] for x in seed}
    if not all(x['expected_id'] in known for x in golden):
        raise SystemExit('ERRO: avaliação referencia documento inexistente')
    print(f'RELEASE AUDIT OK: {len(names)} arquivos; nenhum segredo reconhecido; assets e dataset consistentes')
    print('AVISO: scanner heurístico; inspeção manual dos arquivos continua necessária.')


if __name__ == '__main__':
    main()
