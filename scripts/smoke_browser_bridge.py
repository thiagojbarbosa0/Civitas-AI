"""Teste real do DOM no Chromium, com transporte HTTP substituído por ponte ASGI.

Útil em ambientes que impedem navegação HTTP local. Não substitui o smoke
HTTP real nem o teste E2E que usa rede do navegador.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import ROOT, Settings
from app.main import create_app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--screenshots', default='', help='Pasta opcional para duas capturas')
    args = parser.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit('Instale Playwright: pip install playwright && python -m playwright install chromium') from exc

    html = (ROOT / 'frontend/index.html').read_text(encoding='utf-8')
    # Arquivos são carregados explicitamente para não disparar HTTP bloqueado.
    html = re.sub(r'<script[^>]*src="/assets/app\.js"[^>]*></script>', '', html)
    html = re.sub(r'<link[^>]*href="/assets/style\.css"[^>]*>', '', html)

    with tempfile.TemporaryDirectory(prefix='civitas-ui-asgi-') as tmp:
        app = create_app(Settings(mode='demo', storage_path=Path(tmp) / 'uploads.json'))
        with TestClient(app) as api, sync_playwright() as playwright:
            exe = os.environ.get('CIVITAS_CHROMIUM', '').strip()
            if not exe:
                default_cache = Path.home() / '.cache' / 'ms-playwright'
                if not list(default_cache.glob('chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell')):
                    exe = shutil.which('chromium') or shutil.which('chromium-browser') or ''
            browser = playwright.chromium.launch(headless=True, executable_path=exe or None,
                                                  args=['--no-sandbox'] if exe else [])
            try:
                page = browser.new_page(viewport={'width': 1366, 'height': 900}, locale='pt-BR')
                failures: list[str] = []
                page.on('pageerror', lambda err: failures.append(str(err)))

                def bridge(url: str, options: dict) -> dict:
                    response = api.request(options.get('method', 'GET'), url,
                                           headers=options.get('headers') or {},
                                           content=options.get('body') or None)
                    return {'status': response.status_code, 'payload': response.json()}

                page.expose_function('civitasAsgiBridge', bridge)
                page.set_content(html, wait_until='domcontentloaded')
                page.add_style_tag(content=(ROOT / 'frontend/style.css').read_text(encoding='utf-8'))
                page.evaluate('''() => {
                  window.fetch = async (url, options = {}) => {
                    const response = await window.civitasAsgiBridge(String(url), {
                      method: options.method || 'GET', body: options.body || '', headers: options.headers || {}
                    });
                    return { ok: response.status >= 200 && response.status < 300,
                      status: response.status, json: async () => response.payload };
                  };
                }''')
                page.add_script_tag(content=(ROOT / 'frontend/app.js').read_text(encoding='utf-8'))
                page.wait_for_function("document.querySelector('#stat-docs')?.textContent === '10'", timeout=12000)
                assert page.locator('#top-status').inner_text() == 'API online'
                print('PASS BROWSER ASGI: painel e métricas')
                if args.screenshots:
                    path = Path(args.screenshots)
                    path.mkdir(parents=True, exist_ok=True)
                    page.evaluate('document.activeElement?.blur()')
                    page.screenshot(path=str(path / 'dashboard.png'), full_page=True)

                page.locator('[data-page="assistant"]').click()
                page.locator('#chat-input').fill('Qual o prazo de reparo de iluminação pública?')
                page.locator('#send-chat').click()
                page.locator('.message.assistant').last.wait_for(timeout=12000)
                assert '[AUR-005]' in page.locator('.message.assistant').last.inner_text()
                assert page.locator('.message.assistant strong').count() >= 1
                assert page.locator('#source-list .source-card').count() >= 1
                page.wait_for_function("document.querySelector('#top-status')?.textContent === 'API online'")
                print('PASS BROWSER ASGI: resposta, formatação segura e fonte')
                if args.screenshots:
                    page.evaluate('document.activeElement?.blur()')
                    page.screenshot(path=str(path / 'assistant.png'), full_page=True)

                page.locator('#clear-chat').click()
                assert page.locator('.message').count() == 0
                assert page.locator('#chat-prompts .prompt-chip').count() > 0
                print('PASS BROWSER ASGI: limpar e reinicializar sugestões')

                page.locator('[data-page="knowledge"]').click()
                page.locator('#search-services').fill('creche')
                page.wait_for_function("document.querySelector('#knowledge-count')?.textContent === '1 documento disponível'", timeout=10000)
                print('PASS BROWSER ASGI: pesquisa no catálogo')

                page.locator('[data-page="evaluation"]').click()
                page.locator('#run-eval').click()
                page.wait_for_function("document.querySelector('#eval-state')?.textContent === 'CONCLUÍDO'", timeout=12000)
                assert page.locator('#eval-top1').inner_text() == '100%'
                assert page.locator('#eval-abstention').inner_text() == '100%'
                assert not failures, failures
                print('PASS BROWSER ASGI: avaliações e nenhuma exceção JavaScript')
                print('BROWSER ASGI BRIDGE: 5 verificações aprovadas (sem rede no navegador)')
            finally:
                browser.close()


if __name__ == '__main__':
    main()
