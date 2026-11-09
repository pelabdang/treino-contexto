---
tipo: glossario
status: em-uso
dono: nina
atualizado: 2026-11-09
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
- **Tiro (1 km)**: volta de corrida de 950 a 1050 m com intensidade `active` ou `interval`; sem intensidade, a que é pelo menos 8% mais rápida que a mediana da atividade. Desde a `@4`, não vale o km mais de 20% mais lento que a mediana dos tiros (ritmo parecido) nem o km forte colado a outro km de corrida quase tão rápido (bloco contínuo, progressivo ou fartlek). Desde a `@5` o tiro é um esforço de faixa `d1000` ([[metricas/esforcos]]); a série é uma visão dos esforços. Ver [[metricas/tiros-1km]].
- **Recuperação**: volta que não é tiro entre o primeiro e o último tiro. Ver [[metricas/tiros-1km]].
- **Treino intervalado (detecção)**: corrida com 2 ou mais tiros de 1 km (desde a `tiros_1km@5`). Vira sugestão de tipo `intervalado`, nunca sobrescreve o professor. Ver [[modulos/api]].
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
- **Treino de transição (brick)**: treino em uma modalidade logo seguida de outra, gravado pelo relógio como atividades separadas. As atividades não se juntam: cada uma ganha um rótulo sim/não, sugerido pela regra `transicao@1` e corrigível pelo atleta. Ver [[decisoes/0009-treino-de-transicao]] e [[metricas/transicao]].
- **Rótulo de transição**: linha em `rotulo_transicao` com `origem` `sugerido` (da regra) ou `atleta` (correção, que a regra nunca toca). Sem linha vale "não". Ver [[decisoes/0009-treino-de-transicao]] e [[modulos/banco]].
- **Grupo de transição**: sequência de atividades rotuladas, cada uma começando até 30 min depois do fim da anterior. Calculado na leitura, nunca guardado; o `grupo_id` muda quando uma correção parte ou junta o grupo. Só se comparam grupos da mesma forma (ex.: `ciclismo>corrida`). Ver [[decisoes/0009-treino-de-transicao]] e [[modulos/api]].
- **Intervalo estimado**: tempo entre o fim de uma parte e o início da seguinte, com o fim estimado por `inicio + duracao_s` (tempo em movimento). Pode sair maior que o real e não ranqueia nada. Ver [[decisoes/0009-treino-de-transicao]].
- **Multiesporte (pai e troca)**: treino em que o relógio grava uma atividade que agrupa as partes (`subtipo = multiesporte_pai`) e atividades de troca entre elas (`troca`), ambas com `modalidade = outra`. Ficam fora da regra de transição e, na Meta 6, fora da carga. Ver [[modulos/ingestao-garmin]].
- **Semana-padrão**: plano semanal do atleta: para cada dia da semana (ISO, 1 = segunda) e modalidade, o tipo de treino esperado. Tem vigência (`vigente_desde`) e `definido_por` (`atleta` ou `professor`, rótulo declarado, sem login). Tabelas `semana_padrao` e `semana_padrao_item`. Ver [[decisoes/0011-linha-de-base-e-semana-padrao]] e [[modulos/banco]].
- **Vigência (da semana-padrão)**: período em que uma semana-padrão vale. Para uma atividade, vale a de maior `vigente_desde` menor ou igual à data local; nunca a seguinte. Ver [[decisoes/0011-linha-de-base-e-semana-padrao]].
- **Encaixe (na semana-padrão)**: ligar uma atividade ao item do plano do seu dia e modalidade. O item vale para uma atividade só: a de maior duração. Ver [[metricas/tipo-treino]].
- **Origem do tipo (`tipo_origem`)**: de onde veio o tipo de treino: `professor`, `trainingpeaks` (confirmados, não mudam), `semana_padrao` (plano) ou `sugestao` (regra de reserva). Ver [[metricas/tipo-treino]].
- **Regra de reserva**: regra que sugere o tipo da corrida quando o plano não dá um: 2 ou mais tiros = `intervalado`; sem esforço e 75 min ou mais = `longo`; sem esforço e 20 min ou mais = `leve`. `moderado` e `fartlek` nunca saem dela. Ver [[metricas/tipo-treino]].
- **Divergência (de tipo)**: o formato do treino contradiz o plano (`sem_esforco` ou `tem_tiros`). O tipo do plano fica, o dado é gravado em `tipo_divergencia` e o treino não entra na linha de base. Ver [[metricas/tipo-treino]].
- **Janela da linha de base**: os 56 dias (8 semanas) anteriores à sessão, no mesmo atleta, modalidade e tipo. Exige pelo menos 8 valores; com menos, o estado é `aprendendo`. Ver [[metricas/linha-base]].
- **Desvio robusto**: medida de quanto os treinos variam em torno da mediana: `max(1,4826 x MAD, 2% da mediana)`. Não se deixa levar por um treino fora do comum. Ver [[metricas/linha-base]].
- **MAD**: desvio absoluto mediano: a mediana de `|x - mediana|`. Base do desvio robusto. Ver [[metricas/linha-base]].
- **Escore z (robusto)**: `(valor - mediana) / desvio robusto`. Com `|z| >= 2,5` a sessão fica `fora` do normal; senão, `dentro`. Compara com o histórico, não diz se o treino foi bom ou ruim. Ver [[metricas/linha-base]].
- **Estado da linha de base**: `dentro`, `fora`, `aprendendo` (poucos treinos), `sem_valor` (a sessão não tem a métrica) ou sem linha de base, com motivo (`multiesporte`, `sem_tipo`, `divergente`, `transicao`, `modalidade_sem_metricas`). Ver [[metricas/linha-base]].
