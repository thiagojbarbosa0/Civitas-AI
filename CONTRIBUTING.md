# Contribuindo para Civitas AI

1. Crie uma branch com nome descritivo; não inclua segredos, dados reais, PDFs de cidadãos ou pesos de modelos.
2. Instale as dependências de desenvolvimento: `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`.
3. Execute `bash scripts/verify.sh` e confirme testes, cobertura e dataset LoRA.
4. Documente novos endpoints na OpenAPI e adicione testes positivos, negativos e de acesso.
5. PRs devem explicar: problema, solução, testes executados e limites conhecidos.

As alterações devem manter a cidade Aurora fictícia e distinguir claramente inferência real, demo determinística e recursos experimentais.
