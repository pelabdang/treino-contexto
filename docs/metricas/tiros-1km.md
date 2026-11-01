---
tipo: metrica
status: em-uso
dono: caio
atualizado: 2026-10-31
links: [[modulos/grafico-tiros]], [[produto/meta-1-como-reproduzir]], [[produto/roadmap]], [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0002-segmento-intensidade-e-versao]], [[glossario]]
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

## Agregação por sessão (issue #12)
Um ponto por atividade com `eh_intervalado` verdadeiro; série ordenada por data (empate: id da atividade).
Rodagem leve e natação não entram.

- **Pace da sessão (s/km)** = soma das durações dos tiros / soma das distâncias dos tiros x 1000. É a média
  ponderada pela distância, não a média simples dos paces.
- **FC da sessão (bpm)** = soma(FC x duração) / soma(duração), média ponderada pela duração. Tiros sem FC ficam
  fora (inclusive do peso); se nenhum tem FC, `None`.
- Também saem `n_tiros`, `data` (data local do início) e `atividade_id`.
- `versao`: versão da regra de detecção (`tiros_1km@1`), vinda da detecção e levada até o ponto da série
  (`SessaoTiros.versao`, `PontoSessao.versao`). É o valor a gravar em `segmento.versao_deteccao` ([[decisoes/0002-segmento-intensidade-e-versao]]).
  Mudou regra ou constante: sobe `VERSAO`.
- Arredondamento só na apresentação, 1 casa decimal (`para_apresentacao`); o cálculo usa o valor cheio.

Exemplo à mão: tiros 1000 m/240 s/160 bpm, 1000 m/236 s/165 bpm, 990 m/238 s sem FC:
pace = 714 / 2990 x 1000 = 238,8 s/km; FC = (160x240 + 165x236) / 476 = 162,5 bpm.

### Formato do pace em `m:ss` (issue #39)
`formatar_pace(s_km)` arredonda ao segundo **com meio para cima** (piso de `s_km + 0,5`) e só depois separa
minutos e segundos; por isso nunca sai "3:60". Não usa `round()` do Python (arredonda para o par). É a regra única
do eixo do gráfico, do CSV e do JSON ([[modulos/grafico-tiros]]).

| Pace (s/km) | `m:ss` |
|---|---|
| 238,8 | 3:59 |
| 239,5 | 4:00 |
| 238,49 | 3:58 |
| 250,83 | 4:11 |
| 237,0 | 3:57 |
| 59,5 | 1:00 |

### Valores esperados das fixtures (oráculo, issue #30)
Calculados à mão a partir de `tests/fixtures/garmin/gerar_fixtures.py`; o teste
`services/api/tests/metricas/test_oraculo_fixtures.py` os guarda em `ESPERADO` para a #14 e a #18 reutilizarem.

| Atividade | Tiros | Pace (s/km) | FC (bpm) | Conta |
|---|---|---|---|---|
| 1000000001 (6 x 1 km) | 6 | 250,83 (4:10,8) | 170,30 | 1505 s / 6000 m; 256309 / 1505 |
| 1000000002 (5 x 1 km) | 5 | 237,0 (3:57,0) | 171,77 | 1185 s / 5000 m; 203546 / 1185 |

Ficam fora da série: 1000000003 (corrida leve, sem tiros), 1000000004 (natação) e 1000000005 (sem FIT).

## Dados de entrada
Por volta: `ordem`, `distancia_m`, `duracao_s`, `fc_media` (opcional) e `intensidade` (opcional; campo
`segmento.intensidade` proposto na ADR da issue #9). Mais a modalidade da atividade.

## Referência
Regra própria do projeto; não há artigo. A mediana como referência de ritmo-base é a escolha robusta
usual: poucos tiros rápidos não a puxam.

## Código e teste
- Código: `services/api/app/metricas/tiros_1km.py` (`detectar_tiros`, `agregar_sessao`, `serie_por_sessao`)
- Testes: `services/api/tests/metricas/test_agregacao_sessao.py` (exemplo acima) e
  `services/api/tests/metricas/test_tiros_1km.py` (valor esperado calculado à mão em cada caso, ex.:
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
- **Esteira fica fora da série** (decisão do Angelo, #51): a detecção classifica uma esteira como qualquer corrida,
  mas `serie_tiros_1km`/`sessoes_tiros_1km` descartam `subtipo = "esteira"`. A atividade segue guardada.
