

def test_health(client):
    data = client.get('/api/v1/health').json()
    assert data['status'] == 'ok' and data['fictional_data'] is True


def test_home_and_static(client):
    assert client.get('/').status_code == 200
    assert 'Civitas AI' in client.get('/').text
    assert client.get('/assets/app.js').status_code == 200
    assert client.get('/assets/style.css').status_code == 200


def test_services_and_detail(client):
    r = client.get('/api/v1/services')
    assert r.status_code == 200 and r.json()['total'] == 10
    assert client.get('/api/v1/services/AUR-005').json()['category'] == 'Infraestrutura'
    assert client.get('/api/v1/services/not-there').status_code == 404
    assert client.get('/api/v1/services?q=creche').json()['total'] == 1


def test_chat_grounded(client):
    data = client.post('/api/v1/chat', json={'message': 'O poste de iluminação está apagado'}).json()
    assert data['sources'][0]['id'] == 'AUR-005'
    assert 'AUR-005' in data['answer']
    assert len(data['trace']) == 4
    assert data['mode'] == 'demo'


def test_chat_no_evidence(client):
    data = client.post('/api/v1/chat', json={'message': 'Como visitar as luas de Júpiter?'}).json()
    assert not data['sources']
    assert 'Não encontrei' in data['answer']


def test_limits_and_validation(client):
    assert client.post('/api/v1/chat', json={'message':'x'}).status_code == 422
    assert client.post('/api/v1/chat', json={'message':'x' * 1001}).status_code == 422
    assert client.post('/api/v1/chat', json={'message':'Olá', 'history':[{'role':'system','content':'hack'}]}).status_code == 422
    assert client.get('/api/v1/services?q=' + 'x'*151).status_code == 422
    for _ in range(27):
        assert client.post('/api/v1/chat', json={'message':'consultar creche'}).status_code == 200
    assert client.post('/api/v1/chat', json={'message':'consultar creche'}).status_code == 429


def test_ingest_requires_token(client):
    payload = {'id':'USR-EXAMPLE', 'title':'Serviço de demonstração novo', 'category':'Atenção',
               'summary':'Nova documentação fictícia para treinamento de RAG.'}
    assert client.post('/api/v1/documents', json=payload).status_code == 401
    r = client.post('/api/v1/documents', headers={'Authorization':'Bearer secret-test-token'}, json=payload)
    assert r.status_code == 201, r.text
    assert client.get('/api/v1/services/USR-EXAMPLE').status_code == 200
    assert client.post('/api/v1/documents', headers={'Authorization':'Bearer secret-test-token'}, json=payload).status_code == 409
    assert client.get('/api/v1/services').json()['total'] == 11


def test_headers_and_metrics(client):
    r = client.get('/api/v1/overview')
    assert 'frame-ancestors' in r.headers['content-security-policy']
    assert r.headers['x-content-type-options'] == 'nosniff'
    client.post('/api/v1/chat', json={'message':'Consultar IPTU'})
    x = client.get('/api/v1/metrics').json()
    assert x['queries'] == 1
    assert 'civitas_queries 1' in client.get('/metrics').text


def test_ingest_off_by_default(tmp_path):
    from fastapi.testclient import TestClient

    from app.config import Settings
    from app.main import create_app
    x = TestClient(create_app(Settings(admin_token='', mode='demo', storage_path=tmp_path/'x.json')))
    assert x.post('/api/v1/documents', json={}).status_code == 403
