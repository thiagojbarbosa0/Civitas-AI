# Demo de 5 minutos para uma entrevista técnica

**Posicionamento:** o Civitas AI é um laboratório GovTech **fictício** para mostrar arquitetura, avaliação, segurança e integração opcional com LLMs. Não é produto usado por prefeitura.

1. **0:00–0:40 — problema:** mostrar o dashboard com procedimentos da cidade fictícia Aurora; destacar o risco de chatbot dar orientações sem evidências.
2. **0:40–1:40 — RAG:** perguntar sobre o reparo de iluminação pública. Apontar o ID recuperado `AUR-005`, documentos e rastreabilidade da decisão.
3. **1:40–2:15 — segurança:** perguntar como renovar passaporte ou solicitar IPVA. Mostrar recusa do modelo demo quando não há fonte relacionada.
4. **2:15–3:00 — arquitetura:** explicar os quatro estágios. Roteamento determinístico, recuperação BM25/híbrida, geração template ou via LangChain, auditoria de fontes. A única etapa que chama LLM (quando habilitado) é o especialista.
5. **3:00–4:00 — engenharia:** mostrar FastAPI/OpenAPI, testes, rate limiting, ingestão com token, Docker e GitHub Actions.
6. **4:00–5:00 — evidências e limitações:** executar avaliação sintética. Explicar por que Hit@1 de 100% sobre 15 casos **não** é precisão do chatbot, e por que citação válida não certifica factualidade.

## Perguntas difíceis que você deve saber responder

**"Isso realmente usa IA?"** No modo demo não usa geração LLM: é uma simulação determinística com recuperação real. O modo `llm` integra LangChain com OpenAI/Mistral/Ollama, mas para alegar funcionamento real é necessário executá-lo com um provedor configurado.

**"São quatro agentes autônomos?"** Não. Há quatro etapas especializadas de um pipeline; a arquitetura permite expansão, mas não confundo funções com múltiplos agentes de inferência independentes.

**"Por que BM25?"** É barato, reproduzível e exige pouca infraestrutura para um corpus pequeno. Busca semântica é opcional e exigiria benchmark maior antes de decidir pesos.

**"Por que os testes deram 100%?"** São 15 perguntas positivas e oito negativas artificiais, construídas sobre dez documentos simulados. O objetivo é detectar regressões de recuperação, não demonstrar generalização.

**"E se um documento disser para ignorar as regras?"** O prompt separa evidências de instruções e as ferramentas ficam restritas. Há também fallback quando citações são inválidas. Ainda faltam avaliações rigorosas de injeção de prompt, verificação semântica e aprovação humana; não está pronto para dados sensíveis.

**"Como você evoluiria?"** Adicionaria chunking, indexação vetorial real, reranking, observabilidade distribuída, autenticação robusta e avaliação com dados independentes, antes de cloud pública.
