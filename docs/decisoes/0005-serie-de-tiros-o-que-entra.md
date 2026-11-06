---
tipo: decisao
status: em-uso
dono: theo
atualizado: 2026-11-06
links: [[metricas/tiros-1km]], [[modulos/api]], [[modulos/worker]], [[modulos/grafico-tiros]], [[decisoes/0002-segmento-intensidade-e-versao]], [[produto/metas/meta-1-tiros-1km]], [[produto/roadmap]]
---
# ADR: 0005 Série de tiros: o que entra e como a regra muda

> Numeração: a 0004 fica reservada ao contrato da tela da Meta 2, decidido no PR dela.

## Contexto
Com as fixtures, a regra dos tiros de 1 km (`tiros_1km@1`) passava em todos os testes. Com a exportação real (#19),
a série trouxe sessões que não eram tiros de 1 km (casos descritos de forma genérica em #48, #53 e #58) e
atividades de esteira (#51). A regra mudou em quatro versões (#48, #53, #58) e a esteira saiu da série (#51).
Essas decisões valem para a métrica ([[metricas/tiros-1km]]), para o serviço da série, para a API (JSON e PNG) e para
o comando que grava o gráfico e o CSV ([[modulos/worker]], [[modulos/grafico-tiros]]). Por isso viram ADR.

## Decisão
1. **Esteira fica fora da série** (decisão do Angelo, #51). A atividade continua guardada e classificada; só não entra
   na série, no JSON, no PNG nem no CSV. A regra fica num lugar só (`SUBTIPOS_FORA_DA_SERIE`, no serviço da série).
2. **A regra é geral.** Nenhuma versão usa dia da semana, nome de treino ou qualquer critério específico de um atleta.
   Os limites são constantes nomeadas, iguais para todos os atletas.
3. **O que não tem critério geral vira limitação documentada**, com aprovação do Theo, em vez de exceção no código.
   A lista fica em [[metricas/tiros-1km]], seção "Limitações e quando não usar".
4. **Toda mudança de detecção sobe a versão** (`VERSAO`, gravada em `versao_deteccao`, ADR 0002) e exige reclassificar
   as atividades já gravadas: reimportar a exportação ou rodar `classificar_atividades` para o atleta. Como a API avisa
   que há segmentos com versão antiga fica na ADR 0004 (Meta 2).
5. **Validação com dado real fica fora do repositório.** O gabarito do atleta e os números ficam só no relatório
   privado em `entregas/meta-1/` (fora do git) e em mensagem ao Theo. Issues, PRs, testes e notas usam só exemplos
   sintéticos, com a conta à mão.

6. **Regra de entrada na `tiros_1km@5`** (#168, ADR 0008, item 8): a série passa a ser uma visão dos esforços, em vez
   de olhar voltas. Mudam o mínimo (**2 tiros por sessão**, Angelo 04/11), o treino misto (os tiros de 1 km do bloco
   principal **contam**, sem a regra do volume) e a unidade (bloco `esforco` da faixa `d1000`). Seguem: esteira fora
   (item 1), regra geral (item 2), ritmo parecido de 20%, bloco contínuo de 15% e ritmo habitual de 10%. Um esforço de
   1500 m não é tiro de 1 km. O contrato da API não muda.

## Alternativas consideradas
- **Esteira no mesmo gráfico, marcada pelo `subtipo`:** era o padrão até a conferência; o Angelo decidiu tirar (#51).
- **Regras por atleta (ou pelo dia da semana em que ele costuma fazer tiros):** acertariam o caso de um atleta e
  errariam o de outros; ficam proibidas.
- **Ajustar a regra até não sobrar nenhum caso duvidoso:** levaria a limites calibrados para uma amostra só. Preferimos
  regra geral mais limitação escrita.
- **Testes com recortes do dado real:** mais realistas, mas o repositório é público. Ficam só os sintéticos.

## Consequências
- A regra foi validada com **um atleta**. Os limites podem precisar de ajuste com mais atletas; a nota da métrica diz isso.
- Cada nova versão pede a reclassificação dos dados já gravados, e a documentação da métrica diz como fazer.
- Métricas novas seguem o mesmo caminho: regra geral, versão gravada, conferência com o atleta fora do git e
  limitações escritas.

## Data e quem decidiu
2026-11-03. Esteira fora da série: Angelo (#51). Regra geral, limitações e validação fora do repositório: Theo (#53,
#58). Registro do Paulo no fechamento da Meta 1 (#60). Aprovação do Theo no PR deste ADR.
