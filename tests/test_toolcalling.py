"""Exercita o fluxo de tool calling com cliente LLM falso (sem acesso à rede)."""
from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from typing import ClassVar

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@dataclass
class FakeMessage:
    content: str = ''
    tool_calls: list | None = None
    tool_call_id: str = ''


class FakeTool:
    def __init__(self, func):
        self.func, self.name = func, func.__name__

    def invoke(self, args):
        return self.func(**args)


class FakeChatOpenAI:
    instances: ClassVar[list] = []

    def __init__(self, **kwargs):
        assert kwargs['temperature'] <= 0.2
        self.messages = []
        self.calls = 0
        self.__class__.instances.append(self)

    def bind_tools(self, tools):
        assert {t.name for t in tools} == {'consultar_servico', 'calcular_dias_uteis'}
        return self

    def invoke(self, messages):
        self.messages = messages.copy()
        self.calls += 1
        if self.calls == 1:
            return FakeMessage(tool_calls=[
                {'id': 'call-1', 'name': 'consultar_servico', 'args': {'codigo': 'AUR-002'}},
                {'id': 'call-2', 'name': 'consultar_servico', 'args': {'codigo': 'AUR-999'}},
                {'id': 'call-3', 'name': 'calcular_dias_uteis', 'args': {'dias': 2}},
            ])
        return FakeMessage(content='Alvará de Aurora: documento de referência [AUR-002].', tool_calls=[])


def test_tool_calling_allowlist_and_context(monkeypatch, tmp_path):
    fake_core = types.ModuleType('langchain_core')
    fake_messages = types.ModuleType('langchain_core.messages')
    fake_tools = types.ModuleType('langchain_core.tools')
    fake_openai = types.ModuleType('langchain_openai')
    fake_messages.SystemMessage = FakeMessage
    fake_messages.HumanMessage = FakeMessage
    fake_messages.AIMessage = FakeMessage
    fake_messages.ToolMessage = FakeMessage
    fake_tools.tool = FakeTool
    fake_openai.ChatOpenAI = FakeChatOpenAI
    monkeypatch.setitem(sys.modules, 'langchain_core', fake_core)
    monkeypatch.setitem(sys.modules, 'langchain_core.messages', fake_messages)
    monkeypatch.setitem(sys.modules, 'langchain_core.tools', fake_tools)
    monkeypatch.setitem(sys.modules, 'langchain_openai', fake_openai)

    c = TestClient(create_app(Settings(mode='llm', provider='ollama', storage_path=tmp_path/'uploads.json')))
    data = c.post('/api/v1/chat', json={'message': 'Como conseguir alvará?'}).json()
    assert data['answer'].endswith('[AUR-002].')
    assert data['mode'] == 'llm'
    assert len(data['tools_used']) == 3
    sent = FakeChatOpenAI.instances[-1].messages
    tool_results = [x.content for x in sent if getattr(x, 'tool_call_id', '')]
    assert any('Consulta fora das evidências recuperadas' in x for x in tool_results)
    assert any('Data ilustrativa' in x for x in tool_results)
    assert any('AUR-002' in x for x in tool_results)


def test_tool_call_overflow_always_returns_matching_tool_messages(monkeypatch, tmp_path):
    """A próxima chamada ao provedor falharia se sobrassem IDs sem resposta."""
    import sys
    import types

    fake_messages = types.ModuleType('langchain_core.messages')
    fake_tools = types.ModuleType('langchain_core.tools')
    fake_openai = types.ModuleType('langchain_openai')
    fake_messages.SystemMessage = FakeMessage
    fake_messages.HumanMessage = FakeMessage
    fake_messages.AIMessage = FakeMessage
    fake_messages.ToolMessage = FakeMessage
    fake_tools.tool = FakeTool

    class OverflowChat(FakeChatOpenAI):
        def invoke(self, messages):
            self.messages = messages.copy()
            self.calls += 1
            if self.calls == 1:
                return FakeMessage(tool_calls=[
                    {'id': f'tool-{i}', 'name': 'consultar_servico', 'args': {'codigo': 'AUR-002'}}
                    for i in range(5)
                ])
            ids = [m.tool_call_id for m in messages if m.tool_call_id]
            assert ids == [f'tool-{i}' for i in range(5)]
            assert 'Limite de execução' in messages[-1].content
            return FakeMessage(content='Referência para o alvará [AUR-002].', tool_calls=[])

    fake_openai.ChatOpenAI = OverflowChat
    monkeypatch.setitem(sys.modules, 'langchain_core', types.ModuleType('langchain_core'))
    monkeypatch.setitem(sys.modules, 'langchain_core.messages', fake_messages)
    monkeypatch.setitem(sys.modules, 'langchain_core.tools', fake_tools)
    monkeypatch.setitem(sys.modules, 'langchain_openai', fake_openai)

    c = TestClient(create_app(Settings(mode='llm', provider='ollama', storage_path=tmp_path / 'z.json')))
    result = c.post('/api/v1/chat', json={'message': 'Preciso do alvará para comércio'}).json()
    assert result['answer'].endswith('[AUR-002].')
    assert result['tools_used'] == ['consultar_servico'] * 3


def test_excessive_tool_requests_fail_safe(monkeypatch, tmp_path):
    import sys
    import types
    fake_messages = types.ModuleType('langchain_core.messages')
    fake_messages.SystemMessage = FakeMessage
    fake_messages.HumanMessage = FakeMessage
    fake_messages.AIMessage = FakeMessage
    fake_messages.ToolMessage = FakeMessage
    fake_tools = types.ModuleType('langchain_core.tools')
    fake_tools.tool = FakeTool
    fake_openai = types.ModuleType('langchain_openai')

    class RunawayChat(FakeChatOpenAI):
        def invoke(self, messages):
            self.calls += 1
            return FakeMessage(tool_calls=[
                {'id': f'req-{i}', 'name': 'consultar_servico', 'args': {'codigo': 'AUR-002'}}
                for i in range(21)
            ])

    fake_openai.ChatOpenAI = RunawayChat
    monkeypatch.setitem(sys.modules, 'langchain_core', types.ModuleType('langchain_core'))
    monkeypatch.setitem(sys.modules, 'langchain_core.messages', fake_messages)
    monkeypatch.setitem(sys.modules, 'langchain_core.tools', fake_tools)
    monkeypatch.setitem(sys.modules, 'langchain_openai', fake_openai)
    c = TestClient(create_app(Settings(mode='llm', provider='ollama', storage_path=tmp_path / 'z.json')))
    result = c.post('/api/v1/chat', json={'message': 'Preciso do alvará para comércio'}).json()
    assert result['tools_used'] == []
    assert 'determinística' in result['answer']
    assert '[AUR-002]' in result['answer']
