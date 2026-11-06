from datetime import date

from app.agents import workdays
from app.retrieval import tokenize


def test_golden_retrieval(client):
    data = client.post('/api/v1/evaluate').json()
    assert data['n'] >= 12
    assert data['hit_at_3'] >= 0.90, data['cases']
    assert data['hit_at_1'] >= 0.80, data['cases']


def test_normalization():
    assert tokenize('Árvore e PÔDA') == ['arvore', 'poda']


def test_workdays():
    assert workdays(date(2026,10,30), 1) == date(2026,11,2)
    assert workdays(date(2026,10,30), 0) == date(2026,10,30)
