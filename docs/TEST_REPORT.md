# Relatório de validação — Civitas AI v1.3.1

**Ensaio local:** 3 de novembro de 2026. **Ambiente:** Python 3.13.5, Uvicorn local, sem credenciais de LLM, sem daemon Docker, navegador Chromium com navegação local bloqueada pela política do ambiente.

## Testes efetivamente executados

| Teste | Resultado |
| --- | --- |
| Pytest | **40/40 aprovados** |
| Cobertura backend (`app/`) | **90,08%** (51 linhas não exercitadas de 514; mínimo configurado: 85%) |
| Recuperação (15 perguntas positivas) | **Hit@1 100%; Hit@3 100%** sobre 10 serviços fictícios |
| Fora do escopo (8 negativas) | **Abstenção 100%** na base sintética |
| Tool calling | **Simulado**, incluindo 5 chamadas na mesma resposta e limite de 3 executadas por rodada |
| Teste HTTP end-to-end (não navegador) | **11 verificações aprovadas**, incluindo chat, avaliação, métricas e ingestão bloqueada |
| Fine-tuning | `--dry-run` validou 8 exemplos, sem treinamento de pesos |
| Teste Chromium DOM com ponte ASGI | **5 verificações aprovadas:** dashboard, chat, limpar, pesquisa e avaliação; não é HTTP direto |
| Teste de corpo em chunks | **2 testes aprovados:** corpo excessivo retorna HTTP 413 e corpo pequeno é aceito |
| Auditoria do Git index | **Aprovada:** token falso inserido somente no stage foi bloqueado mesmo após corrigir o arquivo no disco |
| Sintaxe JavaScript | `node --check frontend/app.js` aprovado |
| Sintaxe Python | `python -m compileall` aprovado |
| Auditoria de release | Scanner de segredos reconhecíveis, assets e golden set aprovado; não substitui revisão manual |

## Não verificado localmente

- Navegação HTTP direta no Chromium: retornou `net::ERR_BLOCKED_BY_ADMINISTRATOR` ao abrir `http://127.0.0.1`. **A interface foi renderizada e testada no Chromium via ponte ASGI**, mas o teste E2E HTTP direto ainda precisa rodar em um ambiente sem essa restrição. Scripts: `smoke_browser_bridge.py` (executado) e `smoke_browser.py` (pendente).
- Execução de modelos externos reais (GPT, Llama, Mistral), embeddings multilíngues, treinamento LoRA e integração LangChain com provedores.
- Build Docker, Docker Compose, execução da GitHub Actions após publicação e deploy Cloud Run.
- Ruff: a execução no Fedora detectou 14 apontamentos na v1.3.0, corrigidos nesta versão. O Ruff não está disponível no ambiente desta revisão; é necessário confirmar `ruff check app tests` no Fedora antes de publicar. Sintaxe, testes e checagens próprias foram executados.

## Limitações técnicas

Esses indicadores são testes de regressão sobre dez documentos e não fornecem estimativas de qualidade em produção. A citação permitida não comprova a veracidade de cada frase. O rate limiter é em memória por processo; não protege múltiplas réplicas. Persistência de ingestão é JSON local. O projeto não oferece autenticação de usuários, tenant isolation, observabilidade distribuída ou dados governamentais oficiais.

## Reexecutar

```bash
bash scripts/fedora.sh --check
# ou, num ambiente já instalado:
bash scripts/prepublish.sh
```

Confira também `docs/GUIA_TESTE_E_PUBLICACAO.md` para navegador, Docker, provedor de IA e publicação.
