"""Métricas agregadas em memória; não armazena conversas ou dados pessoais."""
from collections import Counter
from threading import Lock


class Metrics:
    def __init__(self):
        self.count = Counter()
        self.total_ms = 0.0
        self.lock = Lock()

    def add(self, mode: str, latency_ms: float, had_context: bool, ok: bool):
        with self.lock:
            self.count['queries'] += 1
            self.count['grounded' if had_context else 'unknown'] += 1
            self.count['errors' if not ok else 'success'] += 1
            self.count['mode_' + mode] += 1
            self.total_ms += latency_ms

    def snapshot(self):
        with self.lock:
            n = self.count['queries']
            return {'queries': n, 'grounded': self.count['grounded'], 'unknown': self.count['unknown'],
                    'errors': self.count['errors'], 'average_latency_ms': round(self.total_ms/n, 1) if n else 0}

    def prometheus(self):
        x = self.snapshot()
        return '\n'.join(f'civitas_{k} {v}' for k,v in x.items()) + '\n'
