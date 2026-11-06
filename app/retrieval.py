"""Indexação lexical BM25 e recuperação híbrida com embeddings opcionais."""
from __future__ import annotations

import json
import math
import os
import re
import tempfile
import threading
import unicodedata
from collections import Counter
from pathlib import Path


QUERY_FILLERS = {'quanto', 'custa', 'custo', 'valor', 'preco', 'prazo', 'dias', 'documentos', 'necessarios', 'necessario', 'obter', 'faco', 'reclamar', 'servico', 'servicos', 'requisitos', 'procedimento', 'procedimentos', 'saber', 'vai'}

STOPWORDS = {
    'a', 'o', 'as', 'os', 'um', 'uma', 'uns', 'umas', 'ao', 'aos', 'da', 'do', 'das', 'dos',
    'de', 'e', 'em', 'no', 'na', 'nos', 'nas', 'por', 'para', 'pra', 'com', 'sem', 'que',
    'qual', 'quais', 'como', 'quando', 'onde', 'sobre', 'preciso', 'precisa', 'fazer',
    'quero', 'gostaria', 'pode', 'posso', 'pelo', 'pela', 'minha', 'meu', 'seu', 'sua',
    'este', 'esta', 'isso', 'voce', 'voces', 'eu', 'me', 'ter', 'tem', 'ha', 'ate', 'ou',
    'sera', 'ser', 'mais', 'menos', 'se', 'ja', 'esse', 'essa', 'algo', 'solicitar',
    'pedido', 'informacoes', 'informacao',
}

def tokenize(s: str) -> list[str]:
    raw = unicodedata.normalize('NFKD', s.lower())
    clean = ''.join(c for c in raw if not unicodedata.combining(c))
    return [w for w in re.findall(r'[a-z0-9]+', clean) if w not in STOPWORDS and len(w) >= 2]


class KnowledgeBase:
    """Índice em memória, persistência local de demonstração (processo único)."""

    MAX_UPLOADS = 100
    def __init__(self, seed: Path, uploads: Path, embedding_mode='bm25', embedding_model=''):
        self.seed, self.uploads = seed, uploads
        self.mode, self.embedding_model = embedding_mode, embedding_model
        self._lock = threading.RLock()
        self._encoder = None
        self._vectors = None
        self.reload()

    def reload(self):
        with self._lock:
            data = json.loads(self.seed.read_text(encoding='utf-8'))
            if self.uploads.exists():
                extras = json.loads(self.uploads.read_text(encoding='utf-8'))
                if isinstance(extras, list):
                    data.extend(extras)
            if len({d['id'] for d in data}) != len(data):
                raise ValueError('Documentos com IDs duplicados')
            self.docs = data
            self.tokens = [tokenize(self.document_text(d)) for d in data]
            self.counts = [Counter(t) for t in self.tokens]
            self.avgdl = sum(map(len, self.tokens)) / max(1, len(data))
            df = Counter()
            for doc in self.counts:
                df.update(doc.keys())
            self.idf = {w: math.log(1 + (len(data) - n + .5) / (n + .5)) for w, n in df.items()}
            self._vectors = None

    @staticmethod
    def document_text(d):
        return ' '.join([d.get('title', ''), d.get('category', ''), d.get('summary', ''),
                         ' '.join(d.get('tags', [])), ' '.join(d.get('requirements', [])),
                         ' '.join(d.get('steps', [])), d.get('deadline', ''),
                         d.get('fee', ''), d.get('channel', ''), d.get('notes', '')])

    def _bm25(self, query):
        words = set(tokenize(query))
        scores = []
        for counts, tokens in zip(self.counts, self.tokens):
            score = 0.0
            for w in words:
                f = counts.get(w, 0)
                if f:
                    score += self.idf.get(w, 0) * f * 2.2 / (f + 1.2 * (.25 + .75 * len(tokens) / max(1, self.avgdl)))
            scores.append(score)
        return scores

    def _semantic(self, query):
        if self._encoder is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as e:
                raise RuntimeError('Instale requirements-embeddings.txt para retrieval híbrido') from e
            self._encoder = SentenceTransformer(self.embedding_model)
        if self._vectors is None:
            self._vectors = self._encoder.encode([self.document_text(d) for d in self.docs], normalize_embeddings=True)
        q = self._encoder.encode([query], normalize_embeddings=True)[0]
        return [float(v @ q) for v in self._vectors]

    def search(self, query: str, limit: int = 4):
        with self._lock:
            if not query.strip():
                return []
            query_terms = set(tokenize(query)) - QUERY_FILLERS
            if not query_terms:
                return []
            lexical = self._bm25(query)
            best = max(lexical, default=0)
            sem = self._semantic(query) if self.mode == 'hybrid' else None
            result = []
            for i, doc in enumerate(self.docs):
                # Abstém quando um resultado compartilha somente palavras genéricas.
                # Heurística conservadora; não é classificador de domínio treinado.
                overlap = len(query_terms.intersection(self.counts[i]))
                if sem is None and overlap / len(query_terms) < .5:
                    continue
                norm = lexical[i] / best if best > 0 else 0
                if sem is None:
                    score = norm
                else:
                    score = .55 * norm + .45 * max(0, sem[i])
                # OOD lexical sem confiança: semantic-only só se similaridade alta
                if (lexical[i] == 0 and (sem is None or sem[i] < .55)) or score < .12:
                    continue
                result.append({'id': doc['id'], 'title': doc['title'], 'category': doc['category'],
                               'summary': doc['summary'], 'score': round(score, 3), 'document': doc})
            result.sort(key=lambda d: (-d['score'], d['id']))
            return result[:max(1, min(limit, 10))]

    def get(self, doc_id: str):
        with self._lock:
            return next((d for d in self.docs if d['id'] == doc_id), None)

    def list(self, q: str = ''):
        with self._lock:
            return [{'id': d['id'], 'title': d['title'], 'category': d['category'], 'summary': d['summary']}
                    for d in self.docs if not q or any(t in tokenize(self.document_text(d)) for t in tokenize(q))]

    def ingest(self, doc: dict):
        """Adiciona documento estruturado. Autenticação é feita na camada HTTP."""
        with self._lock:
            if self.get(doc['id']):
                raise ValueError('ID já existe')
            previous = json.loads(self.uploads.read_text(encoding='utf-8')) if self.uploads.exists() else []
            if not isinstance(previous, list):
                raise TypeError('Base de uploads inválida: esperada uma lista')
            if len(previous) >= self.MAX_UPLOADS:
                raise ValueError('Limite de 100 documentos locais atingido')
            previous.append(doc)
            self.uploads.parent.mkdir(parents=True, exist_ok=True)
            # Arquivo temporário exclusivo: sem janela de leitura parcialmente escrita;
            # permissões 0600 para não expor conteúdo enviado pelo administrador.
            tmp_name = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', prefix='.civitas-',
                                                 suffix='.tmp', dir=self.uploads.parent, delete=False) as tmp:
                    tmp_name = tmp.name
                    os.chmod(tmp_name, 0o600)
                    json.dump(previous, tmp, ensure_ascii=False, indent=2)
                    tmp.flush()
                    os.fsync(tmp.fileno())
                os.replace(tmp_name, self.uploads)
            finally:
                if tmp_name and os.path.exists(tmp_name):
                    os.unlink(tmp_name)
            self.reload()
