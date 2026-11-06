# Segurança e divulgação responsável

**Não conecte este protótipo a dados pessoais reais ou a sistemas oficiais.** O projeto usa documentos municipais inteiramente fictícios. A execução padrão é local (`127.0.0.1`) e não tem autenticação de cidadãos.

Para reportar uma vulnerabilidade, abra uma **private vulnerability report** no menu *Security* do repositório GitHub depois de publicado, se disponível. Não divulgue credenciais, dados pessoais ou provas de conceito perigosas em issues públicas.

O modo LLM permite prompt injection em documentos e respostas potencialmente alucinadas. O verificador de citações é apenas **sintático**, não um verificador de verdade. O rate limiting funciona somente dentro de um processo, e o limite HTTP por `Content-Length` não substitui um limite de corpo em um gateway de produção.

Antes de expor publicamente: reverse proxy/WAF, autenticação OIDC, RBAC, limites de tráfego distribuídos, controle de payload em streaming, auditoria de acessos, vetores de injeção, isolamento de tenants, secrets em vault e monitoramento.

Consulte `docs/SEGURANCA.md` para o modelo de ameaças e limitações.
