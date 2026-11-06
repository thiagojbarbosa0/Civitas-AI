# Modelo de ameaças e limites

**Status:** protótipo técnico, não pronto para operar com dados reais de cidadãos.

| Risco | Controle atual | Limitação / ação seguinte |
| --- | --- | --- |
| Prompt injection em textos | Prompt marca documentos como dados não confiáveis, tools allowlisted | LLMs ainda podem obedecer instruções maliciosas; testes adversariais e isolamento por trecho necessários |
| Execução de ações não autorizadas | Tools somente leitura, sem exec/shell/rede e loops limitados | Auditar modelos/providers e validar saída de cada tool |
| Exposição de dados sensíveis | Corpus fictício, sem armazenamento de conversas | Fazer DLP, anonimização de logs, consentimento, política LGPD antes de uso real |
| Ingestão indevida | Token Bearer local exigido, modo escrita desligado sem token | Adicionar autenticação de usuários, RBAC, trilha de auditoria, assinaturas dos documentos |
| Exaustão de recursos | Mensagens até 1000 caracteres, 6 históricos, 30 chamadas/min/IP | Rate limiting distribuído, limite de streaming no reverse proxy, quotas por usuário/modelo e timeout global; limitador atual tem memória limitada |
| XSS no navegador | Texto de LLM desenhado com `textContent`, CSP e nosniff | Revisões CSP e testes em navegador |
| Alucinação | Cobertura mínima lexical, conjunto negativo de avaliação, verificação sintática de IDs de citações e fallback determinístico | **Citações não são verificação factual**; implementar verifier com avaliação humana |
| Credenciais expostas | `.env` no `.gitignore`, tokens exigidos por ambiente | Vault/secret manager, rotação, auditoria Git histórico |
| SSRF | Base URL do LLM configurada apenas via ambiente, nunca por entrada do usuário | Validar DNS/egress e redes internas em produção |
| DoS | Rate limit em memória por IP | Limite não é distribuído, e não cobre todos os endpoints |

## Caminho para produção

1. Segurança de acesso: OIDC, RBAC, isolamento por tenant, HTTPS, bloqueio de origem e gestão de secrets.
2. Confiabilidade: retriever com isolamento de fontes, testes de prompt injection, revisão humana, verificador de citações por afirmação, thresholds calibrados.
3. Dados: fontes oficiais com atualização automática, versionamento e validade, revisão jurídica, LGPD, retenção e direito de exclusão.
4. Monitoramento: auditoria centralizada, tracing distribuído, SLOs, limites de custo e alerta de comportamento anômalo.
5. Plataforma: storage gerenciado, filas, migrações, backups, disaster recovery, infraestrutura com IaC, scanners de segurança.

Referências: https://genai.owasp.org/llm-top-10/ e https://owasp.org/www-project-api-security/ .

### Observações da revisão v1.1

- `Content-Length` é limitado a 20 KB nos endpoints de escrita, porém **requisições com transferência em streaming exigem limite adicional no proxy**. Não há gateway de produção incluído.
- `/api/docs` (Swagger) usa recursos externos de jsDelivr e executa script inline; somente essa rota tem CSP mais permissiva, enquanto o aplicativo mantém CSP restritiva. Para cenário de alta segurança, hospedar todos os ativos localmente e fixar hashes/versões.
- O armazenamento no JSON suporta apenas processo único. Nunca compartilhe um mesmo arquivo entre contêineres concorrentes como banco de dados.
- O modo LLM restringe a ferramenta documental aos IDs recuperados; isso não mitiga inteiramente prompt injection ou acesso por geração alucinada.

### Pré-publicação v1.2 (não equivale a pentest)

A release inclui auditoria heurística de nomes e padrões de credenciais em arquivos preparados, verificação de assets e datasets e smoke HTTP sem conexão externa. O script de GitHub exige confirmação literal e recusa remote `origin` já existente. Nenhum desses mecanismos substitui revisão manual de segredos, varredura de dependências, controle de acesso em nuvem ou avaliação red-team de prompt injection.
