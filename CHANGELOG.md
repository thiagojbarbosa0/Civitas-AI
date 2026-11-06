## Pacote final de publicação — 2026-11-04
- Corrigido instalador para evitar executar duas vezes a verificação completa antes do upload.
- A análise estática com Ruff tornou-se obrigatória na verificação e na publicação.
- Empacotamento final com comandos Fedora atualizados; recursos externos continuam condicionados a validação no ambiente do usuário.

## 1.3.1 — 2026-11-03

- Ruff de desenvolvimento fixado em 0.17.3 e CI cobrindo Python 3.14; corrigidos os 14 apontamentos do Ruff 0.17.3 relatados na execução real do Fedora.
- Imports organizados em módulos, testes e integração opcional com LangChain.
- Tratamento de erro de ferramenta limitado a parâmetros inválidos (sem engolir falhas inesperadas).
- Melhorados os testes de rate limiting: conferem `HTTPException` 429, não uma exceção qualquer.
- Mantida semântica do corpus BM25; exceção por formato inválido de uploads agora é `TypeError`.
- Reexecutados testes, HTTP smoke, validação da base LoRA, sintaxe JS e auditoria do índice Git.
- **Pendência:** Ruff 0.17.3 deve ser executado no Fedora; não foi possível instalar esta ferramenta no ambiente de revisão.

## 1.3.0 — 2026-11-03

- Segurança: bloqueio efetivo de payloads acima de 20 KB mesmo em transferências chunked.
- Testes: 40 testes pytest, novos cenários de corpo em chunks e browser com API por ponte local.
- Frontend: corrigido erro de atualização após enviar/limpar mensagens; negrito seguro sem HTML não confiável.
- Publicação: conta GitHub verificada (`thiagojbarbosa0`), autor de commit sem configuração global e auditoria dos bytes preparados no Git index.
- Portfólio: capturas reais da UI, instruções de publicação Fedora e documentação de limites.
- **Não testado aqui:** navegação direta HTTP no Chromium, Docker, modelo LLM externo, LoRA real ou CI remota.

# Changelog

## 1.2.0 — 2026-11-03

- Corrigido contrato OpenAI de tool calling: retorno correspondente a cada chamada requisitada, mesmo quando ultrapassa o limite de execução.
- Teto de execução de ferramentas por interação e teste de regressão para chamadas excedentes.
- Endpoint `/api/v1/readiness` explicita que disponibilidade de provedor LLM **não** é verificada.
- Testes de pré-publicação, smoke HTTP real e auditoria de arquivos a publicar.
- Guia de estreia no Fedora e checklist para GitHub com limitações explícitas.
- Atualização da versão visual e da documentação.

# Histórico de versões

## 1.1.0 — revisão para portfólio

- Recuperação lexical com regra conservadora de cobertura de termos e abstenção em perguntas fora do domínio.
- Avaliação de 15 consultas positivas e 8 negativas, sem contaminar métricas de uso.
- Testes com LLM simulado cobrindo tool calling e guarda sintática de citações; `consultar_servico` fica restrita aos IDs recuperados.
- Rate limiter com memória limitada e proteção adicional na ingestão; escrita atômica e permissões 0600 no armazenamento local.
- Schemas mais restritivos, validação de token administrativo, erros de inferência sanitizados.
- CSP ajustada para Swagger UI; melhorias de acessibilidade, cancelamento de consulta e busca com debounce.
- Pipeline CI com matriz Python, cobertura, Ruff, validação LoRA em dry-run e build Docker.
- Documentação de segurança, contribuição e limitações de validação.

## 1.0.0 — base inicial

- FastAPI, interface SaaS, corpus fictício, BM25, demo e integrações opcionais com provedores LLM.
