"""Configuração carregada por instância, sem credenciais no código-fonte."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True, slots=True)
class Settings:
    # default_factory evita congelar variáveis na importação do módulo.
    mode: str = field(default_factory=lambda: env('CIVITAS_MODE', 'demo').lower())
    provider: str = field(default_factory=lambda: env('CIVITAS_PROVIDER', 'ollama').lower())
    model: str = field(default_factory=lambda: env('CIVITAS_MODEL', 'llama3.2'))
    api_key: str = field(default_factory=lambda: env('CIVITAS_API_KEY', ''))
    base_url: str = field(default_factory=lambda: env('CIVITAS_BASE_URL', ''))
    admin_token: str = field(default_factory=lambda: env('CIVITAS_ADMIN_TOKEN', ''))
    embeddings: str = field(default_factory=lambda: env('CIVITAS_EMBEDDINGS', 'bm25').lower())
    embedding_model: str = field(default_factory=lambda: env('CIVITAS_EMBEDDING_MODEL',
        'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'))
    storage_path: Path = field(default_factory=lambda: Path(env('CIVITAS_STORAGE_PATH', str(ROOT / 'data' / 'uploads.json'))))

    def llm_params(self):
        if self.provider == 'openai':
            return {'api_key': self.api_key or os.getenv('OPENAI_API_KEY', ''),
                    'base_url': self.base_url or 'https://api.openai.com/v1'}
        if self.provider == 'mistral':
            return {'api_key': self.api_key or os.getenv('MISTRAL_API_KEY', ''),
                    'base_url': self.base_url or 'https://api.mistral.ai/v1'}
        if self.provider == 'ollama':
            return {'api_key': self.api_key or 'ollama',
                    'base_url': self.base_url or 'http://localhost:11434/v1'}
        raise ValueError('Provedor inválido: use openai, mistral ou ollama')

    def validate(self):
        if self.mode not in ('demo', 'llm'):
            raise ValueError('CIVITAS_MODE deve ser demo ou llm')
        if self.embeddings not in ('bm25', 'hybrid'):
            raise ValueError('CIVITAS_EMBEDDINGS deve ser bm25 ou hybrid')
        if self.admin_token and len(self.admin_token) < 16:
            raise ValueError('CIVITAS_ADMIN_TOKEN deve ter pelo menos 16 caracteres')
        if self.mode == 'llm':
            if not self.model.strip():
                raise ValueError('CIVITAS_MODEL não pode estar vazio')
            params = self.llm_params()
            if not params['api_key']:
                raise ValueError('Configure CIVITAS_API_KEY (ou chave do provedor) no modo llm')
