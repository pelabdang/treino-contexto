---
tipo: glossario
status: em-uso
dono: nina
atualizado: 2026-10-31
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
- **Tiro (1 km)**: volta de corrida de 950 a 1050 m com intensidade `active` ou `interval`; sem intensidade, a que é pelo menos 8% mais rápida que a mediana da atividade. Ver [[metricas/tiros-1km]].
- **Recuperação**: volta que não é tiro entre o primeiro e o último tiro. Ver [[metricas/tiros-1km]].
- **Treino intervalado (detecção)**: corrida com 3 ou mais tiros de 1 km. Vira sugestão de tipo `intervalado`, nunca sobrescreve o professor. Ver [[modulos/api]].
- **Pace médio ponderado**: pace da sessão = soma das durações dos tiros / soma das distâncias x 1000 (ponderado pela distância, não a média simples). A FC da sessão pondera pela duração. Ver [[metricas/tiros-1km]].
- **Oráculo (das fixtures)**: valores de pace e FC por sessão calculados à mão, usados como referência nos testes. Ver [[metricas/tiros-1km]].
