"""Metadados públicos, segurança de release e readiness da demo."""
from __future__ import annotations

import json

from app.config import ROOT


def test_readiness_does_not_misrepresent_llm_validation(client):
    res = client.get('/api/v1/readiness')
    assert res.status_code == 200
    payload = res.json()
    assert payload['ready_for_local_demo'] is True
    assert payload['document_count'] == 10
    assert payload['external_llm_tested'] is False
    assert payload['mode'] == 'demo'


def test_openapi_and_version(client):
    schema = client.get('/openapi.json').json()
    assert schema['info']['version'] == '1.3.1'
    assert '/api/v1/chat' in schema['paths']
    assert '/api/v1/readiness' in schema['paths']
    assert client.get('/api/v1/overview').json()['version'] == '1.3.1'


def test_release_has_no_real_personal_data_in_seed():
    seed = json.loads((ROOT / 'app/knowledge/services.json').read_text(encoding='utf-8'))
    assert len(seed) == 10
    assert len({doc['id'] for doc in seed}) == 10
    assert all(doc['id'].startswith('AUR-') for doc in seed)


def test_no_admin_token_or_model_key_returned_by_health(client):
    response = client.get('/api/v1/health').text
    assert 'secret-test-token' not in response
    assert 'admin_token' not in response
    assert 'api_key' not in response
