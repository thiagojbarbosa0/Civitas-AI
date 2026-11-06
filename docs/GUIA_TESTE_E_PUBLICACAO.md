# Testar e publicar o Civitas AI v1.3.1 — Fedora

Este projeto é um **protótipo de portfólio com dados inteiramente fictícios**, não um atendimento governamental. Os comandos abaixo não requerem credenciais pagas para o modo demo.

## 1. Preparar e verificar

Após extrair o ZIP, abra o terminal dentro da pasta `Civitas-AI`:

```bash
bash scripts/fedora.sh --check
```

O comando cria `.venv` se necessário, instala bibliotecas, testa o backend, verifica cobertura, valida o dataset LoRA (dry-run), verifica sintaxe JavaScript se houver Node, checa HTTP com Uvicorn e audita os arquivos de release. O processo retorna ao terminal sem iniciar um servidor permanente. **Resultado esperado:** 40 testes passando, cobertura de aproximadamente 90%, 11 verificações HTTP e auditoria concluída. Versões futuras podem mudar esses números.

O Ruff é obrigatório e não é ignorado na publicação. Se o script falhar, **não publique** antes de ler o erro e corrigir. A verificação local não substitui teste de integração de serviços externos.

## 2. Experimentar na interface

```bash
bash scripts/fedora.sh
```

Abra `http://127.0.0.1:8000` no navegador. Faça estes passos:

1. **Visão geral:** verifique 10 documentos e o status API online.
2. **Assistente:** pergunte `Qual o prazo de reparo de iluminação pública?` e verifique fonte `AUR-005` e as quatro etapas do pipeline.
3. **Fora do escopo:** pergunte `Como renovar meu passaporte?` e confirme a abstenção.
4. **Base de conhecimento:** pesquise `creche`, abra um serviço e verifique seus detalhes.
5. **Avaliações:** execute e confira Hit@1, Hit@3 e taxa de abstenção, com aviso de corpus sintético.
6. **Swagger:** abra `http://127.0.0.1:8000/api/docs` e `/api/v1/readiness`.
7. **Navegação:** teste em janela estreita ou pelo celular na mesma rede **apenas se configurar conscientemente** o acesso local. O padrão não abre a API para a rede.

Pare o servidor com `Ctrl+C`. Um clique não deve criar protocolo real, executar pagamentos nem acessar órgãos públicos.

### Automação opcional do navegador

```bash
. .venv/bin/activate
python -m pip install 'playwright>=1.55,<2'
python -m playwright install chromium
python -m scripts.smoke_browser --screenshot artifacts/browser-smoke.png
```

Se o navegador tiver a navegação HTTP bloqueada por política local, use o teste alternativo de interface com ponte ASGI (valida DOM, API e interações sem rede no Chromium):

```bash
python -m scripts.smoke_browser_bridge
```

Esse teste alternativo **não substitui** a navegação HTTP E2E; é uma verificação complementar.

Esse passo **não é parte do check local padrão**, pois precisa baixar um navegador. O CI do GitHub tentará rodá-lo. O teste visita o dashboard, faz perguntas, limpa o chat, busca serviços e avalia a recuperação. Se o ambiente bloquear acesso local ao Chromium, documente o motivo e execute manualmente.

## 3. Docker (opcional, mas recomendado antes da entrevista)

O Docker Engine ou Podman com suporte a Compose precisa estar instalado e iniciado:

```bash
cp -n .env.example .env
# Se utiliza Docker Compose v2:
docker compose up --build -d
docker compose ps
curl -fsS http://127.0.0.1:8000/api/v1/health
docker compose logs --tail=30
docker compose down
```

**Atenção:** o serviço Docker usa a porta `8000`, portanto pare o Uvicorn iniciado na etapa anterior. Docker não é requisito para rodar o modo demo pelo script Fedora.

## 4. Modelos reais (opcionais)

No modo demo a resposta é **determinística**; não há geração por um LLM. Para demonstrar LangChain e inferência real, siga o `README.md` para instalar `requirements-llm.txt`, configurar Ollama ou API compatível e definir `CIVITAS_MODE=llm`. Confirme pelo `/api/v1/health` que está em modo `llm` e faça uma pergunta documentada. O endpoint `readiness` **não** comprova que o provedor externo funciona. Não exponha uma API pública e não publique chaves em `.env` ou no Git.

## 5. Publicar no GitHub (somente após a revisão)

```bash
sudo dnf install -y git gh python3 python3-pip unzip
# Executar da pasta Civitas-AI extraída:
bash scripts/publicar_fedora.sh
```

O script testa, verifica a lista de arquivos preparados para publicação, procura tipos conhecidos de segredos e exige que você digite `PUBLICAR` antes de criar um **novo repositório público** chamado `Civitas-AI`. Ele recusa pastas que já apontam para um remote `origin`. A auditoria de segredos é heurística: confira visualmente a lista e nunca inclua documentos privados.

Depois da publicação, abra a aba **Actions** no GitHub e verifique **tests**, **docker-build** e **browser-smoke**. CI verde é evidência adicional, mas não comprova qualidade de um LLM real. O script não faz deploy público nem conecta a uma prefeitura.

## Critério de aprovação antes de mostrar a recrutadores

- `bash scripts/fedora.sh --check` passa.
- Dashboard, chat, evidências e avaliação funcionam no navegador Fedora.
- Nenhuma chave, `data/`, peso de modelo ou `.env` entrou no commit.
- O README descreve que roteador, pesquisador e auditoria são estágios especializados; **não são todos agentes LLM autônomos**.
- O GitHub Actions está verde **ou** eventuais falhas estão resolvidas/documentadas.
- Para afirmar que há GPT/Mistral/Llama rodando, faça e registre um teste real com o provedor escolhido.

**Conclusão:** adequado para testar e publicar como **protótipo de portfólio**, não como software de produção.  
