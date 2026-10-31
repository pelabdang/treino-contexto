# Regras do time

Produto: app de análise de treinos com contexto (corrida, natação, ciclismo).
Plano completo: docs/produto/plano-mvp-execucao.md

## Como trabalhamos
- Toda tarefa é uma issue no GitHub. Ninguém trabalha sem issue.
- Uma issue = uma branch = um PR. Branch: <agente>/<numero>-<descricao>.
- Tarefas pequenas: até 1 dia de trabalho, com "critério de pronto".
- Nenhum código entra sem teste. Rode os testes (`pytest` no backend, `npm test` no app) antes de abrir o PR.
- Só o Theo (tech lead) faz merge, e só com o check `testes` verde.
- Mudança no modelo de dados: só com aprovação do Theo, registrada em docs/decisoes/.
- Nunca faça commit de dados pessoais. A pasta dados-teste/ fica fora do git.
- Nunca use force push, nunca apague branches de outros, nunca mexa em .github/ sem o Theo.
- Ao terminar uma tarefa: PR aberto com "Closes #N", label em-revisao e aviso ao Theo.
- Documentação: siga a seção "Documentação" (padrão Obsidian + Graphify). O Theo só faz merge com CI verde e "docs ok" da Nina.

## Stack
- App: React Native com Expo (TypeScript, Expo Router), rodando em iOS, Android e web. Pasta apps/mobile/.
- Backend: Python 3.12, uv, FastAPI, pytest. Pastas services/api/ e services/worker/.
- Banco: PostgreSQL via Docker Compose (infra/docker-compose.yml). Migrações com Alembic.
- Contrato: OpenAPI do FastAPI gera o cliente TypeScript em packages/api-client/.
- Tudo roda local com `docker compose up` e `npx expo start`. Produção futura: DigitalOcean.
- IA do produto: sempre por uma camada trocável (LiteLLM / interface OpenAI). Provedor e modelo vêm do .env
  (LLM_PROVIDER, LLM_MODEL). Padrão: Groq. Nunca chamar um provedor direto no código.
- Nada de serviços pagos ou contas novas sem "PRECISA DO ANGELO".

## Roteiro
- O roteiro de metas fica em docs/produto/roadmap.md e é mantido pelo Paulo.
- Só se trabalha em issues da meta atual.

## Documentação
- Antes de procurar arquivos, leia graphify-out/GRAPH_REPORT.md. Se graphify-out/ não existir (fica fora do git),
  rode `/graphify . --update` primeiro. Para relações entre partes do
  código use /graphify query "<tema>" ou /graphify explain "<item>".
- Toda mudança de comportamento atualiza a nota do módulo ou da métrica em docs/.
- Métrica nova = nota nova em docs/metricas/ usando o template.
- Decisão que afeta mais de um módulo = ADR em docs/decisoes/.
- A Nina comenta "docs ok" no PR. O Theo só faz merge com CI verde e "docs ok".
- Nunca edite docs/_grafo/ nem graphify-out/: são gerados.
