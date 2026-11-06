"""E2E de navegador: opcional, requer Playwright e Chromium instalados."""
from __future__ import annotations

import argparse
import os
import shutil
import socket
import tempfile
import threading
from pathlib import Path

import uvicorn
from app.config import Settings
from app.main import create_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--screenshot', default='', help='Caminho opcional para captura da UI')
    args = parser.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit('Instale: python -m pip install playwright && python -m playwright install chromium') from exc

    with tempfile.TemporaryDirectory(prefix='civitas-browser-') as td:
        app = create_app(Settings(mode='demo', storage_path=Path(td) / 'uploads.json'))
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        sock.listen(128)
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port,
                                               log_level='error', access_log=False))
        thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
        thread.start()
        try:
            with sync_playwright() as p:
                # Respeita navegador Playwright instalado; Fedora pode usar Chromium do sistema.
                exe = os.environ.get('CIVITAS_CHROMIUM', '').strip()
                if not exe:
                    standard = Path.home() / '.cache' / 'ms-playwright'
                    if not standard.exists() or not list(standard.glob('chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell')):
                        exe = shutil.which('chromium') or shutil.which('chromium-browser') or ''
                browser = p.chromium.launch(headless=True, executable_path=exe or None, args=['--no-sandbox'] if exe else [])
                try:
                    page = browser.new_page(viewport={'width': 1366, 'height': 900}, locale='pt-BR')
                    failures = []
                    page.on('pageerror', lambda error: failures.append(str(error)))
                    page.goto(f'http://127.0.0.1:{port}/', wait_until='domcontentloaded', timeout=15000)
                    page.wait_for_function("document.querySelector('#stat-docs')?.textContent === '10'", timeout=10000)
                    assert page.title().startswith('Civitas AI')
                    print('PASS UI: home e dashboard')

                    page.locator('[data-page="assistant"]').click()
                    page.locator('#chat-input').fill('Qual o prazo de reparo de iluminação pública?')
                    page.locator('#send-chat').click()
                    page.locator('.message.assistant').last.wait_for(timeout=15000)
                    assert '[AUR-005]' in page.locator('.message.assistant').last.inner_text()
                    assert page.locator('.message.assistant strong').count() >= 1
                    page.wait_for_function("document.querySelector('#top-status')?.textContent === 'API online'")
                    assert page.locator('#source-list .source-card').count() > 0
                    print('PASS UI: chat com evidência recuperada')

                    page.locator('#clear-chat').click()
                    assert page.locator('.message').count() == 0
                    print('PASS UI: limpar conversa')

                    page.locator('[data-page="knowledge"]').click()
                    page.locator('#search-services').fill('creche')
                    page.wait_for_function("document.querySelector('#knowledge-count')?.textContent === '1 documento disponível'", timeout=10000)
                    print('PASS UI: busca no catálogo')

                    page.locator('[data-page="evaluation"]').click()
                    page.locator('#run-eval').click()
                    page.wait_for_function("document.querySelector('#eval-state')?.textContent === 'CONCLUÍDO'", timeout=15000)
                    assert page.locator('#eval-top1').inner_text() == '100%'
                    assert page.locator('#eval-abstention').inner_text() == '100%'
                    print('PASS UI: avaliação de RAG e abstenção')
                    assert not failures, failures
                    print('PASS UI: sem erros JavaScript detectados')
                    if args.screenshot:
                        target = Path(args.screenshot)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(target), full_page=True)
                        print(f'Captura: {target}')
                    print('BROWSER E2E: 5 verificações aprovadas')
                finally:
                    browser.close()
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            sock.close()
            assert not thread.is_alive(), 'Servidor não encerrou'


if __name__ == '__main__':
    main()
