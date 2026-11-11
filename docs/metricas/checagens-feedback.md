---
tipo: metrica
status: em-uso
dono: caio
atualizado: 2026-11-11
links: [[decisoes/0013-feedback-automatico]], [[metricas/fatos-treino]], [[metricas/fatos-treino-oraculo]], [[produto/roadmap]], [[glossario]]
---
# Checagens do texto do feedback (`checagens_feedback@2`) e lista de linguagem proibida

## O que mede
Se um texto escrito pela camada de LLM pode chegar ao atleta (ADR 0013, item 4). Não é uma métrica de treino: é a **guarda em código** entre o texto e o app. Função pura
`checar_texto(pacote, texto)` em `services/api/app/explicacao/checagens.py`: sem banco, sem rede, sem IA, sem log. Devolve `Resultado(aprovado, motivos)`, com os **códigos** dos motivos
(nunca o texto nem o termo que reprovou, para nada de dado de saúde ir parar em log). **Qualquer reprovação descarta o texto** (decisão 8): ele não é gravado, não chega ao app, e o feedback do
treino fica `sem_feedback` com `motivo = texto_reprovado`; a nova tentativa é a do próximo `worker.gerar_feedback`. Não há texto de reserva escrito por regra.

## Versão `@2` (11/11, #355): o que mudou
A primeira rodada com o provedor de verdade deu textos que passavam nas checagens `@1` mas saíam telegráficos (pedido do Angelo em 11/11). Quatro casos vistos nessa rodada (só com fixtures), avaliados um a um:
- **(a) Linha que é só lista de valores, sem verbo** ("Treino indoor, carga do relógio 20,0 pontos e 150 UA pela PSE."): virou regra, **`forma_sem_verbo`**, por heurística documentada (abaixo).
- **(b) "pois" como palavra de causa**: virou termo da lista `linguagem_causa`, com "já que" e "visto que".
- **(c) "dentro da mediana de X"** quando o estado é `dentro`: virou regra, **`comparacao_mediana`**. Vale para a expressão em qualquer caso (o certo é "perto da mediana" ou "dentro do seu normal"; "dentro da mediana" nunca é certo, nem em `fora`).
- **(d) A mesma conclusão em duas linhas** ("dentro do seu normal" abrindo e fechando): virou regra, **`conclusao_repetida`**, para uma lista fechada de expressões de conclusão.
Todos os 13 textos bons continuam passando e os 72 ruins anteriores continuam com o mesmo motivo (23 foram reescritos com um verbo, para a nova regra não somar um segundo motivo); 10 ruins novos (R73 a R82) cobrem as quatro regras.

**O que muda para quem lê a versão.** `VERSAO` sobe para `checagens_feedback@2`; o worker grava `versao_checagens` com ela (lida do módulo, não escrita à mão) e o teste de ponta a ponta do worker passou a esperar `@2`. **Feedback já `pronto` não é refeito sozinho** (só a edição do check-in e `versao_fatos` desatualizam; ADR 0013, item 2): os textos gravados com `@1` ficam como estão, com `versao_checagens = checagens_feedback@1` na linha, e só um `worker.gerar_feedback --refazer` os confere de novo pelas regras novas. Texto `sem_feedback` é tentado de novo na próxima execução, já com as regras novas. Nenhuma coluna, migração, motivo de `feedback_treino` ou código da API muda: o `motivo` guardado continua `texto_reprovado`; os códigos novos só aparecem em `checar_texto` (e `checar` devolve o primeiro da lista).

## Regras
Todas rodam sempre; o resultado reúne os códigos de todas as que reprovam, na ordem da tabela.

| Código | Quando reprova |
|---|---|
| `numero_fora_do_pacote` | número (inteiro, decimal com vírgula, milhar com ponto, `m:ss`, porcentagem) que não é valor do pacote nem aparece num `*_texto` dele. **Nenhuma conta**: "2 bpm abaixo" só vale se o pacote trouxer a diferença. Data real também cai aqui |
| `unidade_trocada` | o número está no pacote, mas com outra unidade ("5:44 bpm" em vez de "5:44/km"). Número com unidade precisa do par (número, unidade) do pacote; número solto (sem unidade) só precisa ser um valor do pacote. Unidades: `pontos/h`, `pontos`, `s/km`, `km/h`, `km`, `bpm`, `min`, `UA`, `°C`, `%`, `/km`, `m`, `s`, `h` |
| `numero_por_extenso` | uma palavra da lista "por extenso" (abaixo): o número escaparia da conferência escrito em palavras. "um" e "uma" como artigo passam |
| `linguagem_diagnostico`, `linguagem_culpa`, `linguagem_promessa`, `linguagem_causa`, `linguagem_conselho`, `linguagem_quem_fala` | termo da lista correspondente (abaixo) |
| `elogio_sem_fato` | palavra de elogio sem que um fato do pacote a sustente. O fato: linha de base `ok`, ao menos uma métrica `dentro`, nenhuma `fora` e **sem o atalho dor** (com dor, sem elogio em volta). Sem palavra de elogio, "todas as métricas ficaram dentro do seu normal" é só um fato |
| `forma_linhas` | menos de 3 ou mais de 5 linhas (linhas vazias não contam) |
| `forma_tamanho_linha` | linha com mais de 140 caracteres, ou texto com mais de 700 |
| `forma_markdown` | `*`, crase, `__`, título (`#`), citação (`>`), item de lista (`-`, `•`, `1.`) |
| `forma_sem_verbo` | linha sem verbo conjugado. Aceitam-se: um verbo da lista fechada `VERBOS` (é, são, foi, foram, está, tem, teve, houve, fica(ou), marcou, registrou, aparece(m), soma, durou, fez...) ou uma terminação de pretérito (`-ou`, `-eu`, `-iu`, `-aram`, `-eram`, `-iram`, com 3 letras ou mais antes: "percorreu", "nadou"); e três formas curtas dos exemplos aprovados: a linha que **começa com "Sem"** ("Sem comparação com o seu histórico por enquanto."), a que traz o gerúndio **"aprendendo"** (G03) e a **abertura descritiva** do exemplo 6 (começa com natação, ciclismo, corrida ou "treino ...", e traz "com FC média de N bpm"). Uma lista de valores sem isso reprova |
| `conclusao_repetida` | a mesma expressão de conclusão em **duas linhas diferentes**: "dentro do seu normal", "fora do seu normal", "dentro do normal", "perto da mediana", "sem comparação com o seu histórico". Expressões diferentes em linhas diferentes passam (G01: "perto da mediana" na linha 1 e "dentro do seu normal" na 2) |
| `comparacao_mediana` | "dentro da mediana", "dentro de mediana", "dentro da sua mediana" |
| `dor_regra` | com o atalho dor: falta a frase exata "Você registrou dor neste treino.", há outra menção a dor, ou uma parte do corpo |
| `dor_nao_marcada` | fala em dor (dor, dores, doloroso, doer, dói) sem o atalho |
| `atalho_nao_marcado` | cita cansaço, sono ruim, calor, ou trabalho ou estresse sem o atalho marcado |
| `nome_fora_do_pacote` | palavra com inicial maiúscula fora do começo de frase, ou sigla em maiúsculas, que não seja do pacote (`FC`, `PSE`, `UA`, o `C` de `°C`); parte do corpo sem o atalho dor. Pega nome, lugar e o texto livre do check-in |

A comparação é **sem acento e sem diferença de maiúscula**, como palavra inteira ("eu" não está em "seu"; "dor" não está em "calor"). Exceção: **"nós"** só vale com o acento, porque "nos" (em + os)
aparece nos textos bons ("nos 11 treinos"). Antes das listas, tiram-se do texto os **rótulos do check-in**, e só eles (ver "Rótulos do check-in"), e a frase exata **"sono ruim"**, o rótulo do atalho
(fora dela, "ruim" reprova).

## Rótulos do check-in e clima em palavras (revisão da Nina, aceita pelo Theo em 11/11)
- **O rótulo da sensação do pacote passa, com ou sem parênteses.** Se o pacote traz sensação 5 ("muito bem"), "sensação 5 (muito bem)" e "sensação 5, muito bem" passam; se traz sensação 2 ("mal"), "mal" passa; se traz 1 ("muito mal"), passa inteiro. O **mesmo rótulo fora do pacote** não passa: "muito bem" num treino de sensação "mal" é elogio (`elogio_sem_fato`), e "mal" num treino de sensação "bem" é juízo (`linguagem_culpa`). O rótulo da PSE ("repouso", "máximo"...) passa entre parênteses.
- **"quente" é o fato do atalho "calor"**: "calor", "quente(s)" e "abafado(a)" só aparecem se o atalho calor foi marcado (`atalho_nao_marcado`); a temperatura em °C, sozinha, não autoriza a palavra. **"frio", "fria", "gelado(a)" e "friozinho"** não têm atalho nem campo no pacote (ele traz só °C): reprovam como `nome_fora_do_pacote`. Regra única: o texto só chama o clima de uma palavra se o atleta a marcou; o resto são os números do pacote.
- **Contexto, sem barrar texto legítimo:** "melhor tiro" e "esforço" passam (os termos novos são palavras inteiras: "pior", "erro", "risco", "motivo", "efeito"). Limite conhecido: palavras como "erro" e "efeito" reprovam em qualquer sentido, mesmo inocente; o texto do app tem como evitá-las.

## Lista de linguagem proibida (`checagens_feedback@1`)
Ponto de partida: a lista da ADR 0013 (item 4.2), ampliada. Mudar qualquer lista abaixo, ou um limite, **sobe a versão** (`checagens_feedback@2`).
- **Diagnóstico (`linguagem_diagnostico`):** lesão, lesões, lesionado(a), inflamação, tendinite, fratura, distensão, overtraining, sobretreino, supertreino, doença, infecção, sintoma(s), diagnóstico, síndrome, arritmia, desidratação, desidratado, fadiga, esgotamento, exaustão, risco.
- **Culpa e juízo (`linguagem_culpa`):** falhou, fracasso, fracassou, preguiça, desleixo, culpa, fraco(a), decepcionante, "você deveria", "você devia", péssimo, horrível, "treino ruim", "mau treino", ruim, mau, preocupante, alerta, problema, pior, erro, **mal** (só passa como rótulo da sensação do pacote; ver "Rótulos do check-in").
- **Promessa (`linguagem_promessa`):** "vai melhorar", "com certeza", certamente, garanto, prometo, garantido, "você vai conseguir", "na próxima será", "em breve você".
- **Causa afirmada ou sugerida (`linguagem_causa`):** porque, pois, "já que", "visto que", "por causa", "por conta", devido, "graças a", "se deve", "foi por isso", "por isso", causou, explica, explicam, "pode ter sido", "deve ter sido", possivelmente, provavelmente, talvez, pesou, afetou, atrapalhou, influenciou, contribuiu, impactou, consequência, "indica(m) que", "mostra(m) que", significa, reflete, reflexo, "em razão", motivo, efeito, e "resultado do/da/de" (calor, carga...). O texto põe fatos lado a lado; quem liga um ao outro é o atleta (decisão 3 do Angelo, 10/11: sem "possível" nem causa afirmada).
- **Conselho (`linguagem_conselho`):** descanse, descansar, procure, consulte, evite, tente, recomendo, sugiro, "o ideal", precisa, "não esqueça", cuide, hidrate, beba, médico, fisioterapeuta, "fique de olho", "vale a pena", convém, mantenha, continue, aumente, reduza, diminua, "você deve", descanso, recuperação, "fique atento(a)", prefira, considere, lembre-se, priorize. Vale também para a dor (decisão 7).
- **Quem fala (`linguagem_quem_fala`):** professor(a), treinador(a), técnico, coach (a decisão 6: o app fala; o nome do professor só na Meta 10); primeira pessoa (eu, meu, minha, meus, minhas, nosso(a)(s), **nós** com acento; vamos, estou, sou, acho, penso, notei); "inteligência artificial", "modelo de linguagem"; "olá"; **exclamação** e **emoji**.
- **Elogio (`elogio_sem_fato`, só sem fato que o sustente):** ótimo(a), excelente, parabéns, "muito bem", "bom treino", "bom trabalho", "bem feito", "mandou bem", incrível, arrasou, orgulho, evolução, evoluindo, caprichou, perfeito(a), maravilhoso, melhorou, melhora, progresso, superou, evoluiu, superar, melhorar. O rótulo "muito bem" da sensação do pacote não conta (ver abaixo).
- **Por extenso (`numero_por_extenso`):** dois, duas, três, quatro, cinco, seis, sete, oito, nove, dez, onze, doze, treze, quatorze, quinze, dezesseis, dezessete, dezoito, dezenove, vinte, trinta, quarenta, cinquenta, sessenta, setenta, oitenta, noventa, cem, cento, mil, metade, dobro, triplo, dezena, dúzia.
- **Partes do corpo (com dor, `dor_regra`; sem dor, `nome_fora_do_pacote`):** joelho(s), tornozelo, canela, panturrilha, coxa, quadril, costas, ombro, tendão, músculo, perna(s), glúteo, lombar, coluna, calcanhar, pulso, cotovelo, peito, barriga, pescoço.
- **Rótulos dos atalhos:** cansaço (cansado, cansada), sono ruim, calor (quente, quentes, abafado, abafada), trabalho ou estresse (estresse). Só os marcados podem aparecer; a frase da dor é a da decisão 7.

## Referência
Regra própria do projeto, sem artigo (ADR 0013, "Fontes"). Decisões do Angelo de 10/11: tom aprovado como está, observação positiva só quando um fato a sustenta, clima e check-in lado a lado, dor em uma frase neutra.

## Código e teste
- Código: `services/api/app/explicacao/checagens.py` (`VERSAO = "checagens_feedback@2"`; as listas são constantes nomeadas no topo).
- Teste: `services/api/tests/explicacao/test_checagens.py`. **Os 13 textos bons passam e os 82 ruins reprovam com o motivo certo** (listas da #323, [[metricas/fatos-treino-oraculo]], escritas à mão contra os pacotes do oráculo;
  cada ruim tem exatamente um motivo). Mais casos pequenos de cada regra: unidade, número por extenso, acento e maiúscula, palavra inteira, "nós" e "nos", "sono ruim", rótulos da sensação, rótulos da sensação do pacote e de fora dele, "quente" e "frio", um ruim por termo novo da revisão da Nina, elogio com e sem fato, limites de linhas e de
  caracteres, Markdown, dor marcada e não marcada, atalhos, nome próprio e siglas, ordem dos motivos, pureza do módulo.

## Limitações e quando não usar
- Lista de palavras não entende frase: um texto pode estar inexato e passar (o número bate, a frase interpreta mal), e uma frase proibida escrita com palavras fora da lista passa. Reduz o risco, não o elimina (ADR 0013, "Limitações"); a leitura de uma amostra por pessoa é da QA e da Meta 10.
- **Ordinais** ("terceiro") e outros números por extenso fora da lista passam; a lista cobre cardinais, "metade", "dobro" e "triplo".
- Número solto (sem unidade) só precisa ser **algum** valor do pacote: a checagem não sabe a qual campo o texto o atribui ("sensação 4" passa se o 4 existe em outro campo).
- Dia da semana e mês por extenso ("domingo", "novembro") não são números nem estão na lista; o pacote não traz data, então o texto também não deve trazer. Fica para uma versão da lista se aparecer.
- **`forma_sem_verbo` é uma heurística**: não analisa a frase. Uma frase legítima com um verbo fora de `VERBOS` e sem terminação de pretérito (por exemplo, no presente: "Seu pace sobe") reprova por engano; uma lista de valores com um verbo da lista passa ("Treino leve, 47 min, foi isso"). Por isso a lista é ampla e cresce quando um texto legítimo reprovar (sobe a versão). A abertura descritiva e o "Sem ..." são exceções por forma, não por análise: um "Treino indoor com FC média de 140 bpm, 20,0 pontos e 150 UA." passaria.
- **`conclusao_repetida` pega também a repetição legítima**: dizer "dentro do seu normal" de duas métricas diferentes em linhas diferentes reprova. É a escolha: o pedido do Angelo é uma conclusão por texto; o prompt manda juntar as métricas numa linha. Não pega a mesma conclusão com outras palavras ("tudo certo", "como de costume") nem a conclusão que contradiz o estado do pacote (dizer "fora do seu normal" de uma métrica `dentro`).
- **`comparacao_mediana`** confere só a expressão, não o estado da métrica.
- **O app fala em segunda pessoa**; "você" e "seu" passam, e a primeira pessoa reprova. Se o tom mudar (Meta 10, nome do professor), muda a lista e sobe a versão.
- O limite de 140 caracteres por linha vem da ADR ("a confirmar", item 7); o de 700 é o do `CHECK` da coluna.
