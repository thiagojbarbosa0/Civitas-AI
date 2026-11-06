"""Smoke test HTTP real com Uvicorn local e porta efêmera (sem internet nem credenciais)."""
from __future__ import annotations

import json
import socket
import tempfile
import threading
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import uvicorn

from app.config import Settings
from app.main import create_app


def get_response(base: str, path: str, data: dict | None = None):
    payload = json.dumps(data).encode() if data is not None else None
    request = Request(base + path, data=payload,
                      headers={'Content-Type': 'application/json'} if data is not None else {},
                      method='POST' if data is not None else 'GET')
    try:
        with urlopen(request, timeout=3) as res:
            return res.status, res.read(), res.headers
    except HTTPError as exc:
        return exc.code, exc.read(), exc.headers


def main():
    with tempfile.TemporaryDirectory(prefix='civitas-smoke-') as td:
        app = create_app(Settings(mode='demo', storage_path=Path(td) / 'uploads.json'))
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        sock.listen(128)
        sock.set_inheritable(True)
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port,
                                               log_level='error', access_log=False))
        thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{port}'
        try:
            for _ in range(80):
                try:
                    status, _, _ = get_response(base, '/api/v1/health')
                    if status == 200:
                        break
                except (URLError, OSError):
                    pass
                time.sleep(.05)
            else:
                raise AssertionError('Servidor local não iniciou em 4 segundos')

            checks = [
                ('página inicial', '/', 200),
                ('JS da interface', '/assets/app.js', 200),
                ('CSS da interface', '/assets/style.css', 200),
                ('OpenAPI', '/openapi.json', 200),
                ('readiness', '/api/v1/readiness', 200),
                ('catálogo', '/api/v1/services', 200),
            ]
            for label, path, code in checks:
                status, body, _ = get_response(base, path)
                assert status == code and body, (label, status)
                print(f'PASS HTTP {code}: {label}')

            status, body, _ = get_response(base, '/api/v1/chat', {'message': 'Como solicitar reparo da iluminação pública?'})
            assert status == 200 and b'AUR-005' in body, (status, body[:400])
            print('PASS HTTP 200: pergunta com fonte conhecida')
            status, body, _ = get_response(base, '/api/v1/chat', {'message': 'Como renovar meu passaporte internacional?'})
            assert status == 200 and json.loads(body)['sources'] == [], body[:300]
            print('PASS HTTP 200: abstenção fora do domínio')
            status, body, _ = get_response(base, '/api/v1/evaluate', {})
            result = json.loads(body)
            assert status == 200 and result['n'] == 15 and result['negative_n'] == 8, result
            print('PASS HTTP 200: avaliação')
            status, body, _ = get_response(base, '/api/v1/metrics')
            assert status == 200 and json.loads(body)['queries'] == 2, body[:300]
            print('PASS HTTP 200: avaliação sem contaminar métricas')
            status, body, _ = get_response(base, '/api/v1/documents', {})
            assert status == 403, (status, body[:300])
            print('PASS HTTP 403: endpoint de escrita desabilitado por padrão')
            print('SMOKE HTTP: 11 verificações aprovadas')
        finally:
            server.should_exit = True
            thread.join(timeout=5)
            sock.close()
            assert not thread.is_alive(), 'Servidor não encerrou normalmente'


if __name__ == '__main__':
    main()
