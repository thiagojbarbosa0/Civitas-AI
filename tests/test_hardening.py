"""Regressões: segurança, qualidade da recuperação e isolamento de métricas."""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.agents import AgentPipeline
from app.config import ROOT, Settings
from app.main import RateLimit, create_app
from app.retrieval import KnowledgeBase


def make_client(tmp_path: Path, *, mode='demo'):
    app = create_app(Settings(mode=mode, provider='ollama', embeddings='bm25',
                              storage_path=tmp_path / 'uploads.json', admin_token='secure-test-token-12345'))
    return TestClient(app)


def test_eval_does_not_inflate_chat_metrics(client):
    assert client.post('/api/v1/evaluate').status_code == 200
    assert client.get('/api/v1/metrics').json()['queries'] == 0
    assert client.post('/api/v1/chat', json={'message': 'Informações sobre creche'}).status_code == 200
    assert client.get('/api/v1/metrics').json()['queries'] == 1


@pytest.mark.parametrize('query', [
    'Quero comprar um telescópio para observar Júpiter',
    'Como tirar passaporte brasileiro?',
    'Me diga o valor do IPVA do meu carro',
    'Como cancelar matrícula na universidade?',
    'Como preparar um bolo de chocolate?',
    'Me mostre meu CPF e senha',
])
def test_out_of_scope_refuses_unrelated_documents(client, query):
    data = client.post('/api/v1/chat', json={'message': query}).json()
    assert data['sources'] == [], (query, data['sources'])
    assert 'Não encontrei' in data['answer']


@pytest.mark.parametrize('query,expected', [
    ('Quanto custa obter alvará para comércio?', 'AUR-002'),
    ('Como faço para reclamar sobre um serviço na ouvidoria?', 'AUR-008'),
    ('Preciso saber quando vai reparar a iluminação pública', 'AUR-005'),
    ('Quais documentos são necessários para matrícula na creche?', 'AUR-004'),
])
def test_relevant_questions_are_still_found(client, query, expected):
    data = client.post('/api/v1/chat', json={'message': query}).json()
    assert data['sources'] and data['sources'][0]['id'] == expected


def test_intent_router_preserves_important_words():
    assert AgentPipeline.route('Quando abre a creche?') == 'orientacao_de_prazo'
    assert AgentPipeline.route('Precisa levar documentos?') == 'documentacao'
    assert AgentPipeline.route('Quanto custa a taxa?') == 'custos'


def test_llm_without_valid_citation_returns_grounded_fallback(tmp_path, monkeypatch):
    from app.agents import AgentPipeline
    def ungrounded(self, query, hits, history):
        return 'Invente uma taxa de R$ 999 [AUR-999]', []
    monkeypatch.setattr(AgentPipeline, '_llm_answer', ungrounded)
    c = make_client(tmp_path, mode='llm')
    result = c.post('/api/v1/chat', json={'message': 'Como conseguir alvará?'}).json()
    assert 'Validador de citações' in [step['agent'] for step in result['trace']]
    assert 'AUR-999' not in result['answer']
    assert 'AUR-002' in result['answer']


def test_valid_llm_citations_are_preserved(tmp_path, monkeypatch):
    from app.agents import AgentPipeline
    monkeypatch.setattr(AgentPipeline, '_llm_answer', lambda self, q, h, hist: ('Consulte [AUR-002].', ['consultar_servico']))
    c = make_client(tmp_path, mode='llm')
    answer = c.post('/api/v1/chat', json={'message': 'Como conseguir alvará?'}).json()
    assert answer['answer'] == 'Consulte [AUR-002].'
    assert answer['tools_used'] == ['consultar_servico']


def test_schema_rejects_unknown_fields_and_blank_titles(client):
    assert client.post('/api/v1/chat', json={'message': 'Oi', 'admin': True}).status_code == 422
    data = {'id': 'USR-TESTE', 'title': '     ', 'summary': 'Resumo com vinte ou mais caracteres.',
            'category': 'Testes'}
    assert client.post('/api/v1/documents', json=data, headers={'Authorization': 'Bearer secret-test-token'}).status_code == 422


def test_payload_limit_and_docs_security_policy(client):
    response = client.post('/api/v1/chat', content=b'x' * 20001)
    assert response.status_code == 413
    docs = client.get('/api/docs')
    assert docs.status_code == 200
    assert 'cdn.jsdelivr.net' in docs.headers['content-security-policy']
    page = client.get('/')
    assert 'cdn.jsdelivr.net' not in page.headers['content-security-policy']


def test_rate_limiter_bounded_memory():
    rate = RateLimit(max_requests=1)
    rate.max_clients = 4
    for i in range(100):
        rate.check(f'ip-{i}')
    assert len(rate.data) <= 4
    with pytest.raises(HTTPException) as exc:
        rate.check('ip-99')
    assert exc.value.status_code == 429


def test_upload_atomic_and_private(tmp_path):
    kb = KnowledgeBase(ROOT / 'app/knowledge/services.json', tmp_path / 'uploads.json')
    docs = [{'id': f'USR-{i:04d}', 'title': f'Documento teste {i}', 'category': 'Teste',
             'summary': 'Descrição demonstrativa e fictícia do documento'} for i in range(8)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(kb.ingest, docs))
    saved = json.loads((tmp_path / 'uploads.json').read_text())
    assert len(saved) == 8
    assert len({d['id'] for d in saved}) == 8
    if os.name == 'posix':
        assert ((tmp_path / 'uploads.json').stat().st_mode & 0o777) == 0o600
    kb.MAX_UPLOADS = 8
    with pytest.raises(ValueError, match='Limite'):
        kb.ingest({'id': 'USR-EXCESSO'})


def test_settings_reloads_env(monkeypatch):
    monkeypatch.setenv('CIVITAS_MODE', 'llm')
    assert Settings().mode == 'llm'
    monkeypatch.setenv('CIVITAS_MODE', 'demo')
    assert Settings().mode == 'demo'
    with pytest.raises(ValueError, match='pelo menos 16'):
        Settings(admin_token='bad').validate()


def test_streamed_request_too_large_rejected(client):
    """Rejeita upload em chunks sem depender do header Content-Length."""
    chunks = iter([b'{"message":"', b'x' * 11_000, b'x' * 10_000, b'"}'])
    response = client.post('/api/v1/chat', content=chunks,
                           headers={'Content-Type': 'application/json', 'Transfer-Encoding': 'chunked'})
    assert response.status_code == 413
    assert response.json()['detail'] == 'Payload muito grande'


def test_streamed_request_small_still_works(client):
    chunks = iter([b'{"message":', b'"Consultar creche"}'])
    response = client.post('/api/v1/chat', content=chunks,
                           headers={'Content-Type': 'application/json', 'Transfer-Encoding': 'chunked'})
    assert response.status_code == 200, response.text
    assert response.json()['sources']
