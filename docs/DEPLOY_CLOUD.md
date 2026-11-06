# Deploy em nuvem — Google Cloud Run (roteiro, não executado)

A API e a SPA funcionam no mesmo contêiner. O `Dockerfile` escuta `0.0.0.0:8000` e usa usuário não-root. O deploy abaixo é **opcional** e pode gerar custos em infraestrutura, tráfego e build.

## Pré-requisitos

- Conta e projeto Google Cloud com billing habilitado, `gcloud` instalado e autenticação configurada.
- APIs Cloud Run e Cloud Build habilitadas, permissões IAM necessárias.
- Definir política de acesso (a demo não tem autenticação para o chat).

## Deploy de validação com acesso restrito

```bash
# Dentro da pasta do repositório
gcloud config set project SEU_PROJETO

gcloud run deploy civitas-ai \
  --source . \
  --region southamerica-east1 \
  --port 8000 \
  --no-allow-unauthenticated \
  --set-env-vars CIVITAS_MODE=demo,CIVITAS_EMBEDDINGS=bm25
```

`--source` utiliza o `Dockerfile` presente; o deploy de origem é suportado pela documentação oficial do Cloud Run. Para serviço publicamente acessível, a opção é `--allow-unauthenticated`, **mas não recomendamos torná-lo público** antes de implantar autenticação, quotas, monitoramento e revisão de segurança.

**Restrições importantes:**

- O volume `data/` do compose **não** é aplicado no Cloud Run. O filesystem da instância é efêmero; para ingestão persistente é necessário storage externo. A opção padrão recomendada para cloud demo é deixar `CIVITAS_ADMIN_TOKEN` vazio e desabilitar escrita.
- Métricas, limites e contadores em memória variam por instância e reinício, não são globais.
- O modo `llm` pode usar uma API remota com Secret Manager; jamais codificar a chave no Dockerfile ou no comando de deploy. O Ollama local do Fedora não é acessível a partir de Cloud Run sem arquitetura e rede específicas.
- O limite gratuito, preços e disponibilidade regional podem mudar. Verifique tabela atual do GCP antes de implantar.

Documentação: https://docs.cloud.google.com/run/docs/deploying-source-code
