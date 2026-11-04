---
tipo: glossario
status: em-uso
dono: nina
atualizado: 2026-11-04
---
# Glossário

- **A1, A2, A3**: zonas de intensidade aeróbia usadas na natação (A2 = aeróbio médio).
- **ATL** (carga aguda): média da carga dos últimos ~7 dias. Representa a fadiga.
- **CTL** (carga crônica): média da carga dos últimos ~42 dias. Representa o condicionamento.
- **TSB** (forma): CTL − ATL.
- **TSS / rTSS / hrTSS**: pontuação de carga de um treino por potência, pace ou FC.
- **NP** (potência normalizada): potência média ajustada às variações do esforço no ciclismo.
- **FTP**: maior potência sustentável por cerca de 1 hora.
- **PSE**: percepção subjetiva de esforço, de 0 a 10.
- **HRV**: variabilidade da frequência cardíaca.
- **Desacoplamento (Pa:HR)**: queda da relação potência (ou pace) / FC ao longo de um treino longo.
- **GAP**: pace ajustado pela inclinação do terreno.
- **SWOLF**: tempo + braçadas num comprimento de piscina (eficiência na natação).
- **Linha de base**: o normal do próprio atleta para uma métrica e um tipo de treino.
- **Tipo de treino**: leve, moderado, longo, intervalado, fartlek (definido pelo professor).
- **Intensidade da volta**: campo `intensity` do lap no FIT (`active`, `rest`, `warmup`, `cooldown`, `recovery`, `interval`, `other`). Guardada em `segmento.intensidade`. Ver [[decisoes/0002-segmento-intensidade-e-versao]].
- **Versão da detecção**: identificador `<regra>@<n>` (ex.: `tiros_1km@1`) da regra que classificou o segmento. Guardada em `segmento.versao_deteccao`. Ver [[decisoes/0002-segmento-intensidade-e-versao]].
- **Fuso da atividade (`fuso_min`)**: deslocamento do fuso em minutos (`startTimeLocal` - `startTimeGmt`, ex.: `-180`). Ver [[decisoes/0003-fuso-da-atividade]].
- **Data local da sessão**: data de `inicio + fuso_min`; sem `fuso_min`, usa `America/Sao_Paulo`. É o eixo X da série de tiros. Ver [[decisoes/0003-fuso-da-atividade]].
- **Tiro (1 km)**: volta de corrida de 950 a 1050 m com intensidade `active` ou `interval`; sem intensidade, a que é pelo menos 8% mais rápida que a mediana da atividade. Desde a `@4`, não vale o km mais de 20% mais lento que a mediana dos tiros (ritmo parecido) nem o km forte colado a outro km de corrida quase tão rápido (bloco contínuo, progressivo ou fartlek). Ver [[metricas/tiros-1km]].
- **Recuperação**: volta que não é tiro entre o primeiro e o último tiro. Ver [[metricas/tiros-1km]].
- **Treino intervalado (detecção)**: corrida com 3 ou mais tiros de 1 km. Vira sugestão de tipo `intervalado`, nunca sobrescreve o professor. Ver [[modulos/api]].
- **Pace médio ponderado**: pace da sessão = soma das durações dos tiros / soma das distâncias x 1000 (ponderado pela distância, não a média simples). A FC da sessão pondera pela duração. Ver [[metricas/tiros-1km]].
- **Oráculo (das fixtures)**: valores de pace e FC por sessão calculados à mão, usados como referência nos testes. Ver [[metricas/tiros-1km]].
- **Estado do clima**: `ok` (valores), `indoor` (esteira, piscina, virtual: sem clima), `sem_posicao` (ao ar livre sem coordenada válida), `pendente` (ainda não buscado, dentro dos 7 dias, ou sem sucesso) e `falha` (HTTP 400, resposta fora do esperado ou 5 rodadas sem sucesso). `indoor` e `sem_posicao` são calculados, sem linha na tabela. Ver [[modulos/clima]] e [[decisoes/0007-clima-da-atividade]].
- **Posição de início (arredondada)**: latitude e longitude do começo da atividade, com 2 casas (~1 km), sem trajeto. É o único dado de lugar que o produto guarda. Ver [[decisoes/0007-clima-da-atividade]] e [[modulos/ingestao-garmin]].
- **`entrada` (do clima)**: SHA-256 de início, duração e posição. Se muda, o clima é buscado de novo; se é igual e o estado é `ok`, a atividade não é consultada outra vez. Ver [[modulos/clima]].
- **Rodada (do clima)**: uma execução de `worker.preencher_clima`. `pendente` conta 1 por rodada e vira `falha` na quinta. Não confundir com as repetições dentro de uma consulta (1 chamada mais até 3). Ver [[produto/meta-4-como-rodar]].
- **Bloco (de atividade)**: uma ou mais voltas consecutivas juntadas por ritmo parecido e sem pausa, com distância, duração, pace e FC próprios. Ver [[decisoes/0008-deteccao-de-esforcos]].
- **Esforço**: bloco de intensidade alta em relação ao ritmo habitual (corrida) ou à velocidade habitual (ciclismo). As outras categorias de bloco são recuperação, aquecimento, desaquecimento e leve. Ver [[decisoes/0008-deteccao-de-esforcos]].
- **Faixa (de esforço)**: nome do esforço pela distância (corrida, ex.: `d400`) ou pela duração (ciclismo, ex.: `t4`), com tolerância. Fora de qualquer faixa, o esforço fica sem nome. Ver [[decisoes/0008-deteccao-de-esforcos]].
- **Treino-chave contínuo**: sequência de esforços sem recuperação que soma pelo menos 20 min, sem outra estrutura de repetição. Ver [[decisoes/0008-deteccao-de-esforcos]].
