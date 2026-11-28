---
tipo: decisao
status: proposta
dono: caio
atualizado: 2026-11-28
links: [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0010-carga-de-treino]], [[decisoes/0011-linha-de-base-e-semana-padrao]], [[decisoes/0012-check-in-pos-treino]], [[decisoes/0013-feedback-automatico]], [[decisoes/0014-recuperacao-diaria]], [[decisoes/0016-login-e-deploy-do-piloto]], [[metricas/checagens-feedback]], [[metricas/evolucao-series]], [[metricas/linha-base]], [[produto/roadmap]], [[produto/plano-mvp-execucao]], [[glossario]]
---
# ADR: 0017 Chat do atleta com ferramentas de consulta

> **Proposta** (issue #591, Meta 14), para o Theo aceitar e o Angelo ler. **Nenhuma linha de código nem migração muda neste PR.** Todos os
> números, textos e exemplos são **sintéticos**. Pergunta, resultado de ferramenta e resposta são dado pessoal e de saúde: nada disso, real,
> no repositório, em log ou em captura.
> Dá base para #592 (fixtures), #593 e #594 (ferramentas), #595 (`checagens_chat@1`), #596 (laço), #597 (banco), #598 (rotas), #599 e #600 (tela).
> **Falta a revisão da Duda** nos itens 4, 8 e 9 (banco, rotas e camada de LLM): os valores deles estão marcados como padrão em "A confirmar".

## Contexto
A Meta 14 entrega o chat "Pergunte ao seu treino": o atleta escreve (ou toca num atalho) e recebe uma resposta sobre os próprios treinos, com
números do código e links para o treino e a Evolução. É a seção 4.5 do [[produto/plano-mvp-execucao]], com ferramentas no lugar do catálogo fixo.

Princípio que organiza tudo, o mesmo da [[decisoes/0013-feedback-automatico]]: **quem calcula é o código; a IA só escolhe o que consultar e redige.**
A diferença é que no feedback o pacote de fatos é montado antes; aqui o modelo **pede** os fatos por ferramentas, e as checagens conferem o texto
contra o que as ferramentas devolveram naquela pergunta.

### Decisões do Angelo (28/11) que esta ADR respeita
2. **Provedor Groq, inclusive com o dado real dele.** O Angelo disse que o dado dele não é tão sensível e **aceita o risco**. Vale para o dado dele;
   aluno real segue dependendo da consulta de LGPD (ADR 0016, item 14).
3. **Sem "ainda não sei".** O chat responde qualquer pergunta que faça sentido sobre os treinos do atleta, não só o catálogo da Evolução, e recusa
   com educação só o que não é sobre treino. A IA chama ferramentas de consulta; **os números vêm do código**; as checagens continuam valendo.
4. **As conversas ficam guardadas.** O professor não vê as conversas do atleta (decisão 7).
7. **Professor vê tudo do aluno, menos a Evolução e o chat do atleta.** Na Meta 16 ele terá o **próprio chat** sobre os alunos; por isso as
   ferramentas recebem "quem pergunta" desde já (item 2).

Do 10/11 (ADR 0013) segue valendo: tom sem diagnóstico, culpa, promessa nem causa afirmada; nada do texto em log.

### O que o código do `main` mostra (conferido em 28/11, commit `e94a248`)
- Já existem, por código, tudo o que as ferramentas precisam ler: lista paginada de atividades (`servicos/lista_atividades.py`), `fatos_treino`
  (`explicacao/fatos_treino.py`), linha de base (`servicos/linha_base_leitura.py`, `linha_base@3`), carga e forma (`servicos/carga_leitura.py`,
  `carga@2`, `serie_carga@2`), esforços (`esforcos@1`), clima (`clima_atividade`), check-in (`checkin_treino`), recuperação (`recuperacao_dia`,
  ADR 0014) e o catálogo de séries (`servicos/evolucao_series.py`).
- `app/llm/camada.py` só tem `Redator.redigir` e `ProvedorLLM.completar(sistema, usuario, timeout_s)`: **não há chamada de ferramentas**. O
  `ProvedorFalso` e as regras de não logar nada ficam como são.
- `app/explicacao/checagens.py` tem `checagens_feedback@6` com listas de linguagem proibida e extrator de números. A `checagens_chat@1` **reusa
  as funções puras** e as listas; mudar uma lista de lá passa a exigir subir as duas versões.
- A última migração é a `0018_feedback_transicao_visto`; a do chat será a **`0019`**.
- **LiteLLM 1.108.4 (o do `uv.lock`), conferido hoje no mapa local de modelos:** `supports_function_calling("groq/openai/gpt-oss-120b")` é
  `True` e `supports_function_calling("groq/llama-3.3-70b-versatile")` é `False`. O mapa local pode estar atrás do provedor: **o que vale é a
  rodada real com o Groq e as fixtures (#603)**, não o mapa. A ADR exige que o `LLM_MODEL` do chat seja um modelo com chamada de ferramentas
  confirmada nessa rodada.

## Decisão

### 1. Catálogo de ferramentas
Todas **só leem**, nunca gravam. Nenhuma tem `atleta_id`, `conta_id` nem `professor_id` entre os argumentos (item 2). Datas são sempre as
**locais do atleta** (ADR 0003). Todo resultado traz `versao`, `estado` (`ok`, `sem_dados`, `parcial`) e, quando falta dado, um `motivo_texto`
pronto, para o modelo dizer o que falta em vez de "não sei". Todo número sai com o texto já formatado (`valor_texto`, como no pacote de fatos),
**e só esse texto é citável**. O modelo nunca soma, subtrai nem converte.

| Ferramenta | Argumentos | O que devolve | Quem usa |
|---|---|---|---|
| `listar_atividades` | `modalidade?` (corrida, natacao, ciclismo), `periodo?` (item abaixo), `tipo_treino?`, `ordem?` (`recentes`, `maiores`), `limite?` (1 a 20, padrão 10) | por treino: `atividade_id`, data local, modalidade, tipo, distância e duração em texto, pace ou velocidade, FC média em texto, estado do check-in; mais `total` | atleta e professor |
| `ver_atividade` | `atividade_id` | o pacote de fatos da atividade (`fatos_treino`, sem o texto livre do check-in): treino, linha de base, esforços, clima, carga (FC e PSE), check-in (PSE, sensação, atalhos) | atleta e professor |
| `listar_checkins` | `periodo?`, `limite?` | PSE, sensação e atalhos marcados por treino; **nunca a observação livre** (item 6) | atleta e professor |
| `ler_serie` | `serie_id` (do catálogo de [[metricas/evolucao-series]]), `periodo?` | pontos da série (data e `valor_texto`), faixa do normal, estado `disponivel` ou o motivo | **só o atleta** (a Evolução não é do professor) |
| `comparar_periodos` | `serie_id`, `periodo_a`, `periodo_b` | por código: valor de cada período, diferença em texto e `direcao` (`maior`, `menor`, `parecido` dentro da margem da série) | **só o atleta** |
| `ler_carga_forma` | `data?` (padrão: hoje do atleta) | CTL, ATL e TSB do dia, em texto, com `versao` (`serie_carga@2`) e o estado (por exemplo, poucos dias de histórico) | atleta e professor |
| `ler_linha_base` | `modalidade`, `tipo_treino` | mediana e faixa do normal de cada métrica do tipo, `n` e estado (`ok`, `aprendendo`) | atleta e professor |
| `ler_recuperacao` | `periodo?` | sono, VFC e FC de repouso por noite e a faixa do normal (ADR 0014); `sem_dados` se não importou | atleta e professor |
| `recusar` | `motivo`: `fora_do_tema` ou `pedido_de_mudanca` | nada: o **código** responde com o texto fixo (item 4) | atleta e professor |

`periodo` é uma lista fechada, resolvida pelo código a partir do "hoje" do atleta: `ultimos_7_dias`, `ultimos_28_dias`, `ultimas_12_semanas`,
`ultimos_6_meses`, `ultimo_ano`, ou um par `de` e `ate` em `AAAA-MM-DD`. **Janelas e mínimos são os das séries e da linha de base**
(12 semanas, mínimo de 8 treinos, 3 pontos por janela, 2 nos tiros): a ferramenta não inventa critério, e abaixo do mínimo devolve `parcial`
ou `sem_dados` com o motivo.

`serie_id` aceita só ids do catálogo; id fora dele devolve `{"estado": "erro", "codigo": "serie_desconhecida"}` com a lista dos ids válidos.
`recusar` é uma ferramenta para que **a recusa e o encaminhamento ao professor sejam texto fixo do código**, não texto do modelo (item 4).

**Exemplo sintético de chamada e resultado** (atleta fictício; nada real):
```json
{"nome": "comparar_periodos", "argumentos": {"serie_id": "corrida.pace.leve", "periodo_a": "ultimos_28_dias", "periodo_b": "ultimos_28_dias_anteriores"}}
```
```json
{"versao": "evolucao_series@1", "estado": "ok", "serie_id": "corrida.pace.leve",
 "a": {"n": 6, "mediana_texto": "5:41/km"}, "b": {"n": 5, "mediana_texto": "5:52/km"},
 "diferenca_texto": "11 s/km mais rápido", "direcao": "menor", "margem_texto": "4 s/km"}
```
(`ultimos_28_dias_anteriores` entra na lista fechada de `periodo` como o par de comparação.)

### 2. Escopo por sessão e "quem pergunta"
- **O `atleta_id` de toda ferramenta vem da sessão, nunca do modelo.** O executor recebe um objeto `Consulta(quem, atleta_id, escopo)` montado **pela
  rota** (`atleta_da_sessao`, ADR 0016, item 5) e o passa a cada ferramenta como **parâmetro do código**, não como argumento da chamada. O
  esquema de argumentos que vai ao provedor **não tem** campo de atleta; o validador usa `additionalProperties: false`, e um argumento extra
  (inclusive `atleta_id`) **reprova a chamada** com `{"estado": "erro", "codigo": "argumento_invalido"}`. Ele não é aceito em silêncio nem ignorado.
- **Ids que o modelo cita são conferidos contra o dono.** `ver_atividade(atividade_id)` carrega a atividade **com** `atleta_id = Consulta.atleta_id`;
  atividade de outro atleta e atividade inexistente devolvem o **mesmo** resultado `nao_encontrada` (mesmos bytes, como o `404` do item 5 da ADR 0016).
- **Teste obrigatório (#593):** para cada ferramenta, dois atletas sintéticos; a sessão do A pedindo o id do B, com e sem `atleta_id` no argumento,
  não devolve nada do B. Um teste de cobertura percorre o registro de ferramentas e falha para ferramenta nova sem o caso.
- **Quem pergunta.** `Consulta.quem` é `Quem(papel, conta_id)`. Hoje só existe `papel = "atleta"`. O registro de ferramentas declara, para cada uma, os
  **papéis** que podem usá-la (coluna "Quem usa" acima), e o esquema enviado ao provedor **só inclui as ferramentas do papel**; o executor confere
  de novo, porque o modelo pode citar uma ferramenta que não recebeu (`ferramenta_nao_permitida`, mesmo tratamento de erro).
- **Extensão ao professor (Meta 16, só desenho agora).** O `atleta_id` passa a vir da **escolha do aluno na rota do professor**
  (`/professores/{id}/...`, `professor_da_sessao`), **filtrado pelo vínculo com consentimento ativo e a versão do termo** (o filtro
  `atletas_do_professor`, ADR 0015, item 3, e o item 7 da ADR 0016), **sempre com o `professor_id` da sessão**, nunca o do caminho nem o do
  modelo. O papel `professor` **não recebe** `ler_serie` nem `comparar_periodos` (decisão 7: sem a Evolução). O professor não vê as conversas do atleta:
  a conversa dele é **outra** (`conversa.dono_papel`, `dono_conta_id`; item 7), e as rotas do atleta respondem `404` para ele. Nada disso é implementado
  na Meta 14: o que entra agora é só o parâmetro `quem` e o registro com papéis, com um teste de que um `Consulta` de papel `professor` não vê as
  ferramentas da Evolução.

### 3. Laço
Pergunta -> o código envia mensagens e esquemas das ferramentas ao provedor (método novo `conversar`, item 8) -> o modelo devolve texto **ou**
chamadas de ferramenta -> o código executa e devolve os resultados -> repete, até o texto final.
- **No máximo 6 chamadas de ferramenta por pergunta** (chamadas paralelas na mesma volta contam uma a uma) e **no máximo 8 chamadas ao provedor**
  (as voltas do laço mais, no máximo, uma regeneração do item 4). Passou do teto: `estado = erro`, `motivo = limite_de_ferramentas`.
- **Tempo:** 20 s por chamada ao provedor e 45 s por pergunta, no total. Estourou: `tempo_limite`. Sem nova tentativa dentro de uma chamada.
- **Erro de ferramenta** (`argumento_invalido`, `serie_desconhecida`, falha de banco): o resultado `{"estado": "erro", "codigo": ...}` volta ao
  modelo **uma vez** para ele corrigir. No segundo erro da mesma pergunta, encerra com `motivo = ferramenta_erro`. A mensagem da exceção é descartada
  (só o tipo vira código), como na camada atual.
- **Erro do provedor** (rede, 429, resposta vazia): `provedor_erro`, `provedor_tempo_limite` ou `limite_de_chamadas` (os motivos que a camada
  já tem). O atleta vê uma frase fixa de "não consegui responder agora"; a pergunta fica guardada e ele pode repetir.
- **Histórico enviado ao provedor:** as **últimas 6 trocas** (pergunta e resposta final aprovada), sem os resultados das ferramentas antigas. O modelo
  precisa chamar de novo para citar número. Só o que foi **aprovado** volta como contexto; nunca texto reprovado.
- O `sistema` (instruções) é um texto versionado no código (`prompt_chat@1`), sem dado do atleta, com o "hoje" do atleta e a lista de recusas.

### 4. Checagens do texto final (`checagens_chat@1`)
Função pura, sem banco, sem rede, sem IA, sem log, como a `checagens_feedback`. Recebe o texto, **a lista de resultados das ferramentas daquela
pergunta** e o `Quem`. Devolve aprovado ou **só os códigos** dos motivos (nunca o texto nem o termo que reprovou). Fonte: regra própria do
projeto, sem artigo (decisões do Angelo de 10/11 e 28/11; listas da `checagens_feedback@6`). Cada mudança sobe a versão.

| Código | Reprova quando |
|---|---|
| `numero_fora_dos_resultados` | há número no texto que não aparece como `*_texto` ou valor em algum resultado de ferramenta **da mesma pergunta** (mesma conferência da `numero_fora_do_pacote`: forma, vírgula e unidade; data e hora do treino contam como número) |
| `numero_por_extenso`, `unidade_trocada` | como na `checagens_feedback` (número escrito por extenso; unidade diferente da do resultado) |
| `sem_ferramenta` | o texto traz número, data ou comparação, mas a pergunta teve **zero** chamadas de ferramenta bem-sucedidas |
| `linguagem_diagnostico`, `linguagem_culpa`, `linguagem_promessa`, `linguagem_causa`, `linguagem_julgamento`, `linguagem_quem_fala` | listas da `checagens_feedback@6`, incluindo causa afirmada ("foi por causa do calor") |
| `prescricao` | o texto manda ou sugere treino, pace, descanso ou carga ("faça", "descanse", "treine mais", "o ideal é") |
| `comparacao_sem_ferramenta` | o texto compara períodos ("melhorou", "piorou", "mais rápido que") sem um resultado de `comparar_periodos` (ou de uma ferramenta com `direcao`) naquela pergunta; `direcao = parecido` só aceita "parecido" |
| `dor_regra` | há atalho `dor` nos resultados e o texto traz algo além da frase neutra da ADR 0013 (decisão 7) sobre a dor |
| `dado_ausente_afirmado` | o texto fala de métrica cujo resultado é `sem_dados` como se existisse |
| `forma` | mais de 8 linhas, mais de 900 caracteres, Markdown, emoji, nome próprio ou link escrito pelo modelo |
| `fora_do_escopo_respondido` | pergunta que a ferramenta `recusar` já classificou foi respondida em texto (a recusa é sempre o texto fixo) |

**Recusa e encaminhamento são texto fixo do código**, devolvido quando o modelo chama `recusar`:
- `fora_do_tema`: "Eu respondo perguntas sobre os seus treinos. Pergunte, por exemplo, sobre o seu pace, a sua carga ou como foi a sua semana."
- `pedido_de_mudanca`: "Mudar o treino é com o seu professor. Posso mostrar o que os seus treinos dizem, se isso ajudar na conversa com ele."
  (sem professor vinculado, só a primeira frase; a rota decide).

O modelo decide **só** se chama `recusar`; o que o atleta lê é sempre o texto fixo. Os 5 casos "fora do tema" e os 3 "pedem mudança" das fixtures (#592)
provam as duas pontas: a recusa quando devia, e a **não** recusa de uma pergunta de treino sensata.

**Links** (treino e Evolução) **são montados pelo código**, a partir dos `atividade_id` e `serie_id` que apareceram nos resultados das ferramentas
daquela pergunta e que o texto realmente cita (data ou nome da série). O modelo não escreve link.

**Texto reprovado:** uma regeneração por pergunta, com os **códigos** do motivo no lugar do texto (nunca o texto reprovado de volta). Reprovou de
novo: `estado = reprovada`, o texto é descartado (**nunca gravado, nunca enviado ao app**, nem em campo de depuração), o app mostra a mesma frase
fixa dos erros e a API devolve o motivo em código. Nenhum texto de reserva escrito por regra.

### 5. O que vai ao provedor e o que nunca vai
**Vai:** a pergunta como o atleta digitou, as últimas 6 trocas aprovadas, o "hoje" do atleta, os esquemas das ferramentas e os **resultados das
ferramentas** (números e rótulos em texto, datas locais dos treinos, modalidade, tipo, clima, check-in só com PSE, sensação e atalhos marcados).
**Nunca vai:**
- **a observação livre do check-in** (padrão revisável, pergunta ao Angelo em "A confirmar", 1);
- nome, e-mail, hash de senha, token de sessão, `conta_id`, `atleta_id` (o provedor não precisa de identificador: a sessão é do código);
- posição, coordenadas, trajeto, nome de lugar e o arquivo FIT;
- a observação de qualquer outra tabela e o texto de feedback de outro treino que o código não tenha aprovado.

**Pergunta livre é do atleta:** ele pode digitar um nome ou um lugar, e isso segue ao provedor porque ele escreveu. A tela dirá, sob o campo, que "a
pergunta vai a um serviço de IA" (texto da Lia, no termo da Nina). Não há como o código garantir que a pergunta não tenha dado.

**Log:** **nada** de pergunta, resposta, argumento ou resultado de ferramenta, nem a mensagem de exceção. Só tipo da exceção, motivo em código, nome
da ferramenta, duração e `conta_id` (como no item 9 da ADR 0016). A configuração do LiteLLM da camada atual (sem log de conteúdo, sem callbacks,
`redact_messages_in_exceptions`) vale para o método novo. **Um teste** faz uma pergunta com marcas sintéticas e provedor falso que falha, e confere
que nenhuma marca aparece na saída capturada.

### 6. O que o Angelo aceitou e o que ainda é pergunta
O Angelo aceitou o Groq com o dado dele (decisão 2). Isso **não** responde à observação do check-in: o texto livre é onde o atleta escreve
"dor no joelho" ou o que quiser. **Padrão desta ADR: a observação fica fora do provedor.** Se o Angelo quiser a observação no chat, entra uma ferramenta
`ler_observacao(atividade_id)` à parte, com o aviso na tela, sem mexer no resto. Está em "A confirmar", 1.

### 7. Modelo de dados (para a aprovação do Theo)
Uma migração `0019`, **só aditiva**. Revisão da Duda pendente.

| Tabela | Colunas | Observações |
|---|---|---|
| `conversa` | `id`; `atleta_id` FK `atleta.id` `ON DELETE CASCADE`; `dono_papel` (`atleta` na Meta 14; `professor` na 16); `dono_conta_id` FK `conta.id` `ON DELETE CASCADE`; `titulo` (texto 80, vem da primeira pergunta cortada, **sem passar pelo provedor**); `criada_em`; `atualizada_em` | `CHECK dono_papel IN ('atleta','professor')`. Na Meta 14 todo registro é `atleta`. A lista do atleta filtra `dono_papel = 'atleta' AND atleta_id = sessão`. |
| `mensagem` | `id`; `conversa_id` FK `conversa.id` `ON DELETE CASCADE`; `ordem` (inteiro, `UNIQUE (conversa_id, ordem)`); `pergunta` (texto, até 1000); `chamadas_ferramenta` (JSONB: lista de `{nome, argumentos, resultado}`); `resposta` (texto, anulável, até 900); `estado` (`respondida`, `recusada`, `reprovada`, `erro`); `motivo` (código, anulável); `versao_checagens` (`checagens_chat@1`); `versao_prompt` (`prompt_chat@1`); `provedor`; `modelo`; `criada_em` | `CHECK (estado = 'respondida') = (resposta IS NOT NULL AND motivo IS NULL)` (recusada grava o texto fixo; reprovada e erro **sem texto**). Uma linha por pergunta e resposta. |

- **Resultado das ferramentas é guardado** (padrão, "A confirmar", 3): é o que permite repetir a checagem e abrir o "por que esse número?" depois. É
  dado de saúde, apagado com a conta e fora de log, como o feedback.
- **Apagadas com a conta** (item 9 da ADR 0016): `atleta_id` com `CASCADE`, `mensagem` por `conversa`. O teste de exclusão, que percorre as tabelas com
  `atleta_id` ou chave para `atividade`, **ganha `conversa` e `mensagem`**; `mensagem` não tem `atleta_id` e o teste cobre isso pela `conversa`.
  **O que já foi ao provedor de LLM não se apaga por nós**, e o termo diz isso.
- **Apagar uma conversa:** o atleta apaga uma conversa pela rota (`DELETE`), `CASCADE` nas mensagens.
- **O professor não vê:** não há rota do professor para `conversa`, e a leitura do aluno pela caixa do dia (ADR 0015) não faz join com essas tabelas;
  um teste de rota prova `404` para o professor com vínculo e consentimento ativos.
- **Sem retenção automática** no piloto: a conversa fica até o atleta apagar ou excluir a conta.
- Rotas ficam para a #598 (adendo da ADR 0004), com o `{id}` comparado com a sessão (item 5 da ADR 0016) e **síncronas** nesta meta (sem streaming).

### 8. Provedor e camada trocável
- **Groq, pelo LiteLLM**, `LLM_PROVIDER` e `LLM_MODEL` do `.env` (ADR 0013, item 3). Nunca chamar o provedor direto.
- A camada ganha um **método novo** `conversar(mensagens, ferramentas, timeout_s)` que devolve **ou** texto **ou** a lista de chamadas
  (`nome`, `argumentos` já validados como JSON). `completar` não muda. Mesmas regras: nunca levanta (devolve motivo), sem log de conteúdo, sem nova
  tentativa dentro da chamada, limite de chamadas por instância.
- **Chamada de ferramentas pelo LiteLLM:** o parâmetro `tools` e `tool_choice="auto"` do formato OpenAI; `drop_params` **não** deve se aplicar a
  `tools` (sem ferramenta o laço não funciona: o `ProvedorLiteLLM` do chat falha com `provedor_erro` se o modelo não tiver suporte). Conferência
  feita hoje, só no mapa local: ver o fim de "O que o código do `main` mostra". **A conferência que vale é a rodada real do #603.**
- **Provedor falso nos testes e no CI**, sem rede: `ProvedorFalso` ganha `conversar` com um **roteiro** (lista de respostas: chamadas e texto),
  para cada fixture da #592 reproduzir a pergunta, as ferramentas esperadas e a resposta. CI nunca chama o Groq.
- **Limite de uso:** o Groq no plano gratuito tem limite de requisições e tokens por minuto. Além do limite por instância, **20 perguntas por hora por
  atleta** (padrão, "A confirmar", 5), com resposta `429` e frase fixa. Sem fila, sem nova tentativa em segundo plano.

### 9. Fixtures (#592, só o contrato)
`services/api/tests/fixtures/chat/` com `atletas.json` (os atletas fictícios das Metas 7 e 11, **sem nenhum dado real**) e `perguntas.json`: 20 a 30
perguntas de treino (evolução, um treino, comparação de períodos, check-ins, carga e forma, clima), 5 fora do tema (receita, política, diagnóstico
médico) e 3 que pedem mudança de treino. Cada caso: `id`, `categoria`, `pergunta`, `atleta`, `hoje`, `ferramentas_esperadas` (nome, argumentos,
resultado), `resposta_boa` e `resposta_ruim` (texto e `motivos_esperados`). Um teste carrega tudo, confere que a boa passa na `checagens_chat@1` e
que cada ruim reprova exatamente pelos motivos esperados; outro confere que os nomes e argumentos batem com o registro de ferramentas.

## Alternativas descartadas
- **Catálogo fixo de perguntas** (a versão antiga da Meta 14): descartado pela decisão 3 do Angelo (qualquer pergunta sensata, sem "ainda não sei").
- **Pacote de fatos grande montado antes**, como no feedback: caro em tokens, sem resposta para perguntas fora do pacote (comparar períodos, outro mês).
- **Texto-para-SQL pelo modelo:** daria acesso a qualquer coluna, inclusive a observação, e tiraria do código o controle do escopo e dos números.
- **O modelo fazer as contas** (diferença, média, tendência): é onde o texto inventa número. A `comparar_periodos` existe para isso.
- **`atleta_id` como argumento com validação:** um erro de validação vira vazamento entre atletas; sem o campo no esquema, não há o que validar.
- **Recusa escrita pelo modelo:** pode virar conselho ou diagnóstico; o texto fixo é testável.
- **Guardar só o texto, sem resultado das ferramentas:** não dá para repetir a checagem nem auditar um número.
- **Streaming de resposta:** o texto só pode ser mostrado depois das checagens, então não faz sentido nesta meta.
- **Modelo do provedor sem chamada de ferramentas confirmada (por exemplo, o padrão do mapa local para o Llama 3.3 70B):** fica fora até a rodada real.

## A confirmar (padrão em negrito; sem resposta, vale o padrão)
1. **Observação livre do check-in no provedor** (pergunta ao Angelo). **Fica fora**, em todas as ferramentas. Alternativa: ferramenta `ler_observacao`
   à parte, com o aviso na tela, para ele poder perguntar "o que eu escrevi no treino de ontem?".
2. **Regeneração depois de reprovar.** **Uma**, com os códigos do motivo. Alternativa: nenhuma (o atleta repete a pergunta), mais simples.
3. **Guardar os resultados das ferramentas na mensagem** (Duda). **Sim.** Alternativa: só nome e argumentos, e a conferência refaz a consulta.
4. **Banco e rotas** (Duda): `conversa`/`mensagem` como no item 7, uma linha por pergunta; rotas `POST` e `GET` em `/atletas/{id}/conversas`,
   `GET` e `DELETE` por id e `POST .../mensagens` síncrono. **Padrão: como está.** Sem resposta dela, vale.
5. **Limite por atleta.** **20 perguntas por hora.** Alternativa: só o limite por instância da camada.
6. **Laço:** **6 ferramentas, 8 chamadas ao provedor, 20 s por chamada, 45 s por pergunta, 1 correção de erro de ferramenta** (valores nossos, sem fonte).
7. **`LLM_MODEL` do chat** (Duda e Angelo). **`openai/gpt-oss-120b` no Groq** (suporte confirmado no mapa local). Vale só depois da rodada real do #603.
8. **Histórico de contexto:** **6 trocas aprovadas**, sem resultados antigos. Alternativa: só a pergunta atual.
9. **Dica de pergunta e atalhos** são da Lia (#599); aqui o atalho é só uma pergunta pronta que entra no mesmo fluxo.
10. **Conversa do professor (Meta 16):** **conversa própria** (`dono_papel = 'professor'`), sem ver a do atleta. Alternativa: nenhuma conversa guardada para ele.

## Consequências
- **Bom:** o chat responde qualquer pergunta sobre os treinos sem catálogo; número nenhum vem do modelo; o escopo do atleta não depende de o
  modelo se comportar; a recusa e o encaminhamento são texto fixo; o professor entra depois sem mudar as ferramentas, só o papel.
- **Custo:** `conversar` na camada, oito ferramentas com teste de escopo cada, uma migração, `checagens_chat@1` com a manutenção das listas em
  dois lugares, e uma rodada real no Groq antes de confiar no modelo.
- **Risco aceito:** o dado do Angelo vai ao Groq (decisão 2); o modelo pode chamar `recusar` sem precisar ou deixar de chamar (as fixtures medem, a
  rodada real confirma); o atleta pode digitar dado pessoal na pergunta; texto reprovado após duas tentativas vira uma frase fixa de erro, e isso
  pode frustrar quem pergunta com frequência.
