from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path):
    app = create_app(Settings(mode='demo', provider='ollama', embeddings='bm25',
                              storage_path=tmp_path/'upload.json', admin_token='secret-test-token'))
    return TestClient(app)
