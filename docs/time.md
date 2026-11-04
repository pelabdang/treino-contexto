---
tipo: guia
status: em-uso
dono: nina
atualizado: 2026-11-04
links: [[00-inicio]], [[produto/roadmap]], [[glossario]], [[modulos]], [[design/guia-visual]]
---
# Time e papéis

Quem faz o quê no repositório. As regras de trabalho estão em `AGENTS.md`; este mapa liga cada pessoa (ou agente) às
pastas e notas que ela mantém. Cada agente tem um arquivo em `.claude/agents/`.

| quem | papel | dono de | notas relacionadas |
|---|---|---|---|
| Angelo | dono do produto; decide o que está em "PRECISA DO ANGELO" | decisões de produto | [[produto/roadmap]], [[diario/2026-11-04]] |
| Theo | tech lead; revisa o código e faz o merge com CI verde e `docs-ok` | arquitetura, ADRs | [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0008-deteccao-de-esforcos]] |
| Paulo | planejador; mantém o roteiro de metas e as issues | `docs/produto/roadmap.md` e `docs/produto/metas/` | [[produto/roadmap]] |
| Duda | dados e backend: ingestão Garmin/FIT, banco, clima e API | `services/api/` (menos `app/metricas/` e `app/explicacao/`) e `services/worker/` | [[modulos/ingestao-garmin]], [[modulos/api]], [[modulos/banco]], [[modulos/worker]], [[modulos/clima]] |
| Caio | ciência do esporte: métricas, linha de base e motor de explicação | `services/api/app/metricas/` e `app/explicacao/`, com os testes | [[metricas/tiros-1km]], [[metricas/esforcos]], [[metricas/esforcos-oraculo]] |
| Rafa | app em React Native com Expo (iOS, Android e web) | `apps/mobile/` | [[modulos/mobile]], [[modulos/api-client]] |
| Lia | design de produto e UX; dá o "design-ok" como aval | `docs/design/` | [[design/guia-visual]], [[design/tokens]] |
| Bia | QA: critério de pronto e testes de ponta a ponta | `tests/e2e/` | [[produto/meta-2-como-rodar]] |
| Nina | documentação; revisa todo PR e aplica o `docs-ok` | `docs/` (menos `docs/_grafo/`) | [[00-inicio]], [[glossario]] |

## Regras que ligam o time
- Uma issue = uma branch = um PR, com a branch no formato `<agente>/<número>-<descrição>`.
- Merge só do Theo, com os checks `testes` e `docs` verdes. O `docs-ok` é da Nina; commit novo no PR remove o label.
- PR escrito pela própria Nina recebe o `docs-ok` do Theo.
- O "design-ok" da Lia é um aval a mais nos PRs de tela. Não é requisito de merge e não substitui o `docs-ok`.
- Repositório público: só dado sintético. Dado real fica em `entregas/` e `dados-teste/`, fora do git.
- Nada de serviço pago ou conta nova sem "PRECISA DO ANGELO".
