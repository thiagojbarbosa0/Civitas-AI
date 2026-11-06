# Roteiro de demonstração — 3 a 4 minutos

**Problema:** atendimento fragmentado em múltiplos serviços, dificuldade em localizar procedimentos e falta de transparência da resposta.

**Solução:** o Civitas AI organiza documentos, recupera evidências, orienta por um pipeline de agentes e expõe cada fonte em painel auditável.

## Demonstração

1. **Dashboard (30s):** mostrar os quatro agentes, base fictícia, consultas e métricas. Reforçar que o ambiente não representa prefeitura real.
2. **Assistente (60s):** perguntar "Como solicitar reparo de iluminação pública?". Apontar os documentos `AUR-005`, a trilha e o tipo de resposta. Em modo `llm`, mostrar LangChain real e tools conforme modelo escolhido.
3. **Conhecimento (30s):** navegar na base, abrir documentos e explicar diferença entre *retrieval* e geração.
4. **Avaliação (45s):** executar golden set. Explicar que Hit@1 não mede alucinação; há testes de API e segurança.
5. **DevOps (30s):** mostrar `/api/docs`, `/metrics`, GitHub Actions, Docker e exemplo de integração Ollama.
6. **Visão futura (30s):** autenticação e RLS, RAG com chunks/pgvector, observabilidade distribuída, avaliação de resposta por evidência e atualização de fontes oficiais.

## Para entrevista

**O que é multiagente aqui?** Separação funcional dos estágios de roteamento, recuperação, resposta e auditoria. No modo demo os estágios são determinísticos; no modo llm somente o especialista usa um LLM com ferramentas. Não são quatro modelos autônomos deliberando entre si.

**Por que não fine-tuning em vez de RAG?** RAG melhora atualização e inspeção de fontes; fine-tuning ajusta comportamento de um modelo, não garante que fatos estejam atualizados.

**Por que dados fictícios?** Não atribuir procedimentos inventados a órgãos públicos; preservar credibilidade e segurança da demonstração.

**Quanto custa?** Modo demo: nenhuma API LLM. Ollama local: sem custo de API, mas exige hardware e energia. OpenAI/Mistral: custos dependem de uso/modelo e tabela vigente.
