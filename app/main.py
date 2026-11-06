"""HTTP API, UI, rate-limiting e segurança básica do protótipo."""
from __future__ import annotations

import hmac
import json
import time
from collections import OrderedDict, deque
from threading import Lock

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.requests import ClientDisconnect

from app.agents import AgentPipeline
from app.config import ROOT, Settings
from app.metrics import Metrics
from app.retrieval import KnowledgeBase


class Message(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: str
    content: str = Field(min_length=1, max_length=1000)

    @field_validator('role')
    @classmethod
    def check_role(cls, role):
        if role not in ('user', 'assistant'):
            raise ValueError('Papel não permitido')
        return role


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    message: str = Field(min_length=2, max_length=1000)
    history: list[Message] = Field(default_factory=list, max_length=6)


class DocumentInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str = Field(pattern=r'^USR-[A-Z0-9-]{3,20}$')
    title: str = Field(min_length=5, max_length=120)
    category: str = Field(min_length=3, max_length=60)
    summary: str = Field(min_length=20, max_length=1500)
    tags: list[str] = Field(default_factory=list, max_length=12)
    requirements: list[str] = Field(default_factory=list, max_length=20)
    steps: list[str] = Field(default_factory=list, max_length=20)
    deadline: str = Field(default='Não informado', max_length=160)
    fee: str = Field(default='Não informado', max_length=160)
    channel: str = Field(default='Não informado', max_length=160)
    notes: str = Field(default='Documento enviado pelo administrador; validar antes de uso.', max_length=400)

    @field_validator('title', 'category', 'summary')
    @classmethod
    def require_content(cls, value):
        if not value.strip():
            raise ValueError('Campo não pode conter apenas espaços')
        return value.strip()

    @field_validator('tags', 'requirements', 'steps')
    @classmethod
    def limit_items(cls, values):
        if any(not 2 <= len(x) <= 250 for x in values):
            raise ValueError('Cada elemento deve conter entre 2 e 250 caracteres')
        return values


class RateLimit:
    def __init__(self, max_requests=30, window=60):
        self.max_requests, self.window = max_requests, window
        self.data = OrderedDict()
        self.max_clients = 4096
        self.lock = Lock()

    def check(self, key: str):
        now = time.monotonic()
        with self.lock:
            q = self.data.pop(key, deque())
            while q and now - q[0] >= self.window:
                q.popleft()
            if len(q) >= self.max_requests:
                self.data[key] = q
                raise HTTPException(429, 'Limite temporário de requisições excedido',
                                    headers={'Retry-After': str(self.window)})
            q.append(now)
            self.data[key] = q
            # Impede crescimento ilimitado diante de muitos IPs diferentes.
            while len(self.data) > self.max_clients:
                self.data.popitem(last=False)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.validate()
    app = FastAPI(title='Civitas AI', description='Plataforma GovTech multiagente (cidade fictícia de Aurora)',
                  version='1.3.1', docs_url='/api/docs', redoc_url=None)
    kb = KnowledgeBase(ROOT / 'app' / 'knowledge' / 'services.json', settings.storage_path,
                       settings.embeddings, settings.embedding_model)
    metrics = Metrics()
    engine = AgentPipeline(kb, settings, metrics)
    rate = RateLimit()
    app.state.kb, app.state.engine, app.state.metrics = kb, engine, metrics

    @app.middleware('http')
    async def security_headers(request: Request, call_next):
        blocked = None
        if request.method in ('POST', 'PUT', 'PATCH') and request.url.path.startswith('/api/v1/'):
            # Content-Length sozinho não protege corpos enviados por chunked transfer.
            # O máximo pequeno permite validar o corpo sem fazer streaming no endpoint.
            size = request.headers.get('content-length')
            if size is not None:
                try:
                    content_length = int(size)
                    if content_length < 0:
                        raise ValueError('negative')
                except ValueError:
                    blocked = JSONResponse({'detail': 'Content-Length inválido'}, status_code=400)
                else:
                    if content_length > 20_000:
                        blocked = JSONResponse({'detail': 'Payload muito grande'}, status_code=413)
            if blocked is None:
                payload = bytearray()
                try:
                    async for chunk in request.stream():
                        if len(payload) + len(chunk) > 20_000:
                            blocked = JSONResponse({'detail': 'Payload muito grande'}, status_code=413)
                            break
                        payload.extend(chunk)
                    if blocked is None:
                        # Starlette reaproveita esse corpo para o parser Pydantic.
                        request._body = bytes(payload)
                except ClientDisconnect:
                    blocked = JSONResponse({'detail': 'Envio interrompido'}, status_code=400)
        response = blocked if blocked is not None else await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Frame-Options'] = 'DENY'
        csp = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        # O Swagger padrão do FastAPI usa JS/CSS externos; só essa rota libera o CDN.
        if request.url.path == '/api/docs':
            csp = csp.replace("script-src 'self'", "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net").replace(
                "style-src 'self'", "style-src 'self' https://cdn.jsdelivr.net").replace(
                "img-src 'self' data:", "img-src 'self' data: https://fastapi.tiangolo.com")
        response.headers['Content-Security-Policy'] = csp
        response.headers['Cache-Control'] = 'no-store' if request.url.path.startswith('/api/') else 'public, max-age=60'
        return response

    def throttle(request: Request):
        rate.check(request.client.host if request.client else 'unknown')

    def require_admin(authorization: str | None = Header(default=None)):
        # Sem configuração explícita, endpoint de escrita permanece desligado.
        if not settings.admin_token:
            raise HTTPException(403, 'Ingestão desabilitada. Configure CIVITAS_ADMIN_TOKEN.')
        expected = 'Bearer ' + settings.admin_token
        if not hmac.compare_digest(authorization or '', expected):
            raise HTTPException(401, 'Token de administrador inválido', headers={'WWW-Authenticate': 'Bearer'})

    @app.get('/api/v1/health', tags=['Sistema'])
    def health():
        return {'status': 'ok', 'mode': settings.mode, 'provider': settings.provider,
                'model': settings.model if settings.mode == 'llm' else 'regras determinísticas',
                'retrieval': settings.embeddings, 'fictional_data': True}

    @app.get('/api/v1/readiness', tags=['Sistema'])
    def readiness():
        # Não faz requisição para modelo externo. Uma chave configurada não garante disponibilidade do provedor.
        retrieval_ok = bool(kb.docs)
        llm_configured = (settings.mode != 'llm' or
                          (settings.provider == 'ollama' or bool(settings.llm_params()['api_key'])))
        return {'ready_for_local_demo': retrieval_ok, 'document_count': len(kb.docs),
                'mode': settings.mode, 'llm_configured': llm_configured,
                'external_llm_tested': False,
                'scope': 'Verificação local; não testa rede, Docker, nuvem ou credenciais externas.'}

    @app.get('/api/v1/overview', tags=['Sistema'])
    def overview():
        return {'product': 'Civitas AI', 'version': '1.3.1', 'city': 'Aurora (fictícia)',
                'services': len(kb.docs), 'categories': len({d['category'] for d in kb.docs}),
                'metrics': metrics.snapshot(), 'mode': settings.mode, 'provider': settings.provider,
                'model': settings.model if settings.mode == 'llm' else 'Demo local',
                'retrieval': settings.embeddings, 'ingestion_enabled': bool(settings.admin_token),
                'examples': ['Como pedir poda de árvore na rua?', 'Quais documentos preciso para matrícula na creche?',
                             'Quanto custa solicitar um alvará?', 'Qual o prazo de reparo de iluminação pública?']}

    @app.get('/api/v1/services', tags=['Base de conhecimento'])
    def services(q: str = ''):
        if len(q) > 150:
            raise HTTPException(422, 'Consulta muito longa')
        items = kb.list(q)
        return {'items': items, 'total': len(items)}

    @app.get('/api/v1/services/{doc_id}', tags=['Base de conhecimento'])
    def service(doc_id: str):
        doc = kb.get(doc_id)
        if not doc:
            raise HTTPException(404, 'Serviço não encontrado')
        return doc

    @app.post('/api/v1/documents', status_code=201, tags=['Base de conhecimento'], dependencies=[Depends(throttle)])
    def ingest(doc: DocumentInput, _: None = Depends(require_admin)):
        if len(json.dumps(doc.model_dump(), ensure_ascii=False).encode('utf-8')) > 12000:
            raise HTTPException(413, 'Documento muito grande')
        try:
            kb.ingest(doc.model_dump())
        except ValueError as e:
            raise HTTPException(409, str(e)) from e
        return {'id': doc.id, 'status': 'indexed'}

    @app.post('/api/v1/chat', tags=['Agentes'], dependencies=[Depends(throttle)])
    def chat(body: ChatRequest):
        try:
            return engine.answer(body.message.strip(), [m.model_dump() for m in body.history])
        except (ValueError, RuntimeError) as e:
            # Não expor mensagens de erro de provedores que possam conter segredos.
            raise HTTPException(503, 'Modo de inferência indisponível. Verifique a configuração do servidor.') from e
        except Exception as e:
            # Não devolver stack, prompt, credenciais nem dados de modelos ao cliente.
            raise HTTPException(502, 'Modelo indisponível ou resposta incompatível; consulte logs do servidor') from e

    @app.post('/api/v1/evaluate', tags=['Avaliação'], dependencies=[Depends(throttle)])
    def evaluate():
        dataset = json.loads((ROOT / 'evals' / 'golden.json').read_text(encoding='utf-8'))
        cases = []
        for test in dataset:
            result = engine.answer(test['question'], force_demo=True, record_metrics=False)
            ids = [s['id'] for s in result['sources']]
            hit = test['expected_id'] in ids[:3]
            top1 = bool(ids and ids[0] == test['expected_id'])
            cases.append({'question': test['question'], 'expected_id': test['expected_id'],
                          'retrieved': ids, 'hit_at_3': hit, 'hit_at_1': top1})
        negatives = json.loads((ROOT / 'evals' / 'out_of_scope.json').read_text(encoding='utf-8'))
        negative_cases = []
        for test in negatives:
            result = engine.answer(test['question'], force_demo=True, record_metrics=False)
            negative_cases.append({'question': test['question'], 'abstained': not result['sources'],
                                   'retrieved': [s['id'] for s in result['sources']]})
        n, negative_n = len(cases), len(negative_cases)
        return {'n': n, 'hit_at_3': round(sum(x['hit_at_3'] for x in cases)/n, 3),
                'hit_at_1': round(sum(x['hit_at_1'] for x in cases)/n, 3),
                'negative_n': negative_n,
                'abstention_rate': round(sum(x['abstained'] for x in negative_cases)/negative_n, 3),
                'negative_cases': negative_cases, 'cases': cases,
                'scope': 'Mede recuperação e abstenção lexical em dados sintéticos; não factualidade da geração.'}

    @app.get('/api/v1/metrics', tags=['Observabilidade'])
    def metric_json():
        return metrics.snapshot()

    @app.get('/metrics', response_class=PlainTextResponse, tags=['Observabilidade'])
    def metric_prometheus():
        return PlainTextResponse(metrics.prometheus(), media_type='text/plain; version=0.0.4; charset=utf-8')

    @app.get('/', include_in_schema=False)
    def homepage():
        return FileResponse(ROOT / 'frontend' / 'index.html')

    app.mount('/assets', StaticFiles(directory=ROOT / 'frontend'), name='assets')
    return app


app = create_app()
