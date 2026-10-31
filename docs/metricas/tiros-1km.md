---
tipo: metrica
status: rascunho
dono: caio
atualizado: 2026-10-31
links: [[produto/roadmap]], [[decisoes/0001-modelo-de-dados-minimo]], [[glossario]]
---
# Tiros de 1 km

## O que mede
Quais voltas de uma corrida são tiros de 1 km e se a atividade é um treino intervalado. É a base da série
"pace e FC médios dos tiros por sessão" da Meta 1. Cálculo determinístico, em código, sem banco e sem IA.

## Fórmula
Versão do cálculo: `tiros_1km@1`. Constantes em `services/api/app/metricas/tiros_1km.py`.

1. Só `modalidade == "corrida"`. Qualquer outra modalidade devolve 0 tiros e `eh_intervalado = falso`.
2. **Candidata**: volta com distância de **950 a 1050 m**, inclusive (1000 m ± 50 m, tolerância de GPS e de
   auto-lap; ± 5%). Volta de 949 m ou de 1,2 km nunca é tiro.
3. **Com intensidade** (campo `intensidade` da volta, vindo do FIT: `active`, `interval`, `rest`, `recovery`,
   `warmup`, `cooldown`): tiro = candidata com `active` ou `interval`. `rest`, `recovery`, `warmup` e
   `cooldown` nunca são tiro, mesmo com 1 km.
4. **Sem intensidade** (ausente, valor desconhecido, ou sem contraste): tiro = candidata com
   `pace <= mediana(pace de todas as voltas da atividade) x 0,92`, isto é, pelo menos **8% mais rápida**
   que a mediana. Pace da volta (s/km) = duração (s) / distância (m) x 1000.
5. **Sem contraste**: se todas as voltas reconhecidas têm a mesma intensidade (o auto-lap de 1 km de uma
   rodagem leve vem todo como `active`), a intensidade não informa nada e vale a regra do item 4.
6. **Recuperações**: voltas que não são tiro entre o primeiro e o último tiro.
7. `eh_intervalado` = **pelo menos 3 tiros**.

### Por que 8%
Numa rodagem leve com auto-lap, as voltas variam cerca de 3% a 4% em torno da mediana (relevo, vento,
parada em semáforo); 8% fica com folga acima desse ruído. Um tiro de verdade costuma ser 15% a 30% mais
rápido que o ritmo de rodagem, então 8% não perde tiros. O valor é decisão do projeto, não vem de artigo, e
deve ser revisto com dados reais (#19).

## Dados de entrada
Por volta: `ordem`, `distancia_m`, `duracao_s`, `fc_media` (opcional) e `intensidade` (opcional; campo
`segmento.intensidade` proposto na ADR da issue #9). Mais a modalidade da atividade.

## Referência
Regra própria do projeto; não há artigo. A mediana como referência de ritmo-base é a escolha robusta
usual: poucos tiros rápidos não a puxam.

## Código e teste
- Código: `services/api/app/metricas/tiros_1km.py` (`detectar_tiros`)
- Teste: `services/api/tests/metricas/test_tiros_1km.py` (valor esperado calculado à mão em cada caso, ex.:
  6 x 1 km com recuperação de 400 m: 13 voltas, mediana = 360 s/km, limite = 331,2 s/km, tiros a 240 s/km).

## Limitações e quando não usar
- Sem intensidade e com tiros que são a maioria das voltas (ex.: 8 x 1 km com pausa parada, sem volta de
  recuperação), a mediana vira o ritmo do tiro e nenhum tiro é detectado. Com intensidade isso não ocorre.
- Sem intensidade, uma rodagem progressiva com auto-lap de 1 km pode ter 3 ou mais voltas finais pelo menos 8%
  mais rápidas que a mediana. A regra as marca como tiros e a atividade vira `eh_intervalado`. Limitação
  conhecida (apontada pelo Theo). A mitigação fica na #14: cruzar com o tipo da atividade ou exigir
  alternância entre tiro e recuperação.
- Só detecta tiros de 1 km; 400 m, 2 km e outras distâncias ficam fora da Meta 1.
- Voltas de 1 km de uma prova ou de um longo progressivo, com intensidade `active`, podem passar na regra
  de pace se houver mudança de ritmo clara; é o comportamento esperado da regra, não um erro.
- Esteira sem GPS: a distância vem do sensor do aparelho e pode se afastar da faixa de ± 50 m.
