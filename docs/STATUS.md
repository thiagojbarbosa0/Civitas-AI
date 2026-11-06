# Estado de validação — Civitas AI v1.3.1

**Último ensaio local:** 3 de novembro de 2026 (Python 3.13.5). Base sintética e isolada, sem credenciais externas. Detalhes em `docs/TEST_REPORT.md`.

| Componente | Estado atual | Evidência / ressalva |
| --- | --- | --- |
| API REST FastAPI | **Testado** | 40 testes pytest e 11 verificações HTTP reais com Uvicorn |
| UI | **Parcialmente testado** | Chromium validou dashboard/chat/busca/avaliação com ponte ASGI local; navegação HTTP direta bloqueada; E2E real previsto na CI |
| RAG lexical BM25 | **Testado em dataset sintético** | 15 positivas: Hit@1 e Hit@3 = 100%; 8 negativas: 100% de abstenção |
| Rate limiter, schemas e ingestão | **Testado** | 401/403/409/413/422/429, atomicidade, permissões 0600 e concorrência |
| LLM e tool calling | **Testado com simulação** | Ferramentas autorizadas, limite, IDs de cada tool call e fallback de citações; provedores reais pendentes |
| LangChain / OpenAI / Mistral / Ollama | **Código implementado; não exercitado com provedores** | Depende de credenciais, modelos e rede |
| Embeddings multilíngues | **Implementado, não exercitado** | Requer biblioteca e modelo externo |
| LoRA fine-tuning | **Dataset validado** | Oito exemplos, apenas dry-run, nenhum treino real |
| Métricas | **Testado** | JSON, Prometheus textual, avaliação não altera métricas de conversas |
| Docker / Compose | **Arquivos prontos; build local não executado** | Daemon Docker indisponível; configuração de build verificada por leitura |
| GitHub Actions | **Workflow escrito, execução remota pendente** | Jobs: testes, build Docker, navegador E2E |
| Prepublish / GitHub CLI | **Scripts escritos; verificações locais testadas** | Auditoria heurística; publicação real depende de autenticação e confirmação |
| Cloud Run | **Somente guia de deploy** | Infraestrutura, custos e permissões não testados |

**Veredito:** pronto para teste no Fedora e publicação como portfólio, **não** pronto para uso governamental real ou para afirmar robustez/precisão de modelos em produção.
