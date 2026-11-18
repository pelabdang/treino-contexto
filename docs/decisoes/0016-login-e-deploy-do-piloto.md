---
tipo: decisao
status: proposta
dono: duda
atualizado: 2026-11-17
links: [[decisoes/0001-modelo-de-dados-minimo]], [[decisoes/0004-contrato-tela-evolucao]], [[decisoes/0006-upload-de-fit]], [[decisoes/0009-treino-de-transicao]], [[decisoes/0012-check-in-pos-treino]], [[decisoes/0013-feedback-automatico]], [[decisoes/0015-caixa-do-dia-do-professor]], [[produto/roadmap]], [[produto/meta-13-opcoes-deploy]], [[modulos/api]], [[modulos/banco]], [[glossario]]
---
# ADR: 0016 Login, papéis, consentimento pelo atleta e deploy do piloto

> **Proposta** (issue #497, Meta 13), para o Theo aprovar com a revisão do Caio. **Nenhuma linha de código, migração ou conta muda neste PR.**
> Todos os nomes, e-mails, números e textos são **sintéticos**. Nenhum segredo, senha, token ou endereço de servidor com credencial entra aqui.
> Check-in, feedback, carga e recuperação são dado pessoal e de saúde: nada disso, real, no repositório, em log, em captura ou em fixture.
> Dá base para #499 (contas e sessão), #500 (controle de acesso), #501 (consentimento), #504 (deploy), #505 (backup e exclusão) e #506 (dados no piloto).

## Contexto
Até a Meta 12 o app não sabe quem está olhando: o atleta é fixo por `EXPO_PUBLIC_ATLETA_ID` (ADR 0004, item 8) e o professor por `PROFESSOR_ID` no ambiente (ADR 0015, item 2), "sem rede". A ADR 0015 deixou dito que, com login, **a rota não muda de forma, só a origem da identidade**. Esta ADR fixa essa origem e o que vem junto para pôr o piloto no ar.

### Decisões do Angelo (17/11, "ok para as nove") que esta ADR respeita
1. Provedor **DigitalOcean**; **a conta é criada pelo Angelo**, nunca pelo time; região e teto pela #472; acima do teto, o time para e pergunta.
2. **E-mail e senha na própria API**, senha com hash, sem serviço novo.
3. **Sem domínio próprio** (endereço do provedor, com HTTPS) e **sem e-mail transacional**.
4. CNPJ e consulta de LGPD são condição para o **primeiro aluno real**, não para pôr no ar: no ar só dado sintético e o do Angelo; o termo de consentimento é **provisório e marcado**.
5. O histórico real do Angelo no servidor **só depois do backup com restauração testada**.
6. Em aberto: titular da conta do provedor (pessoa física ou CNPJ). O código não muda com a resposta.
7. Da Meta 12: com login, **só o atleta dono corrige a transição**.

### Decisões do Theo sobre o contrato (17/11, comentário do PR #512, spec das telas da Lia)
1. O acesso fica no cofre do aparelho (Expo) e em `sessionStorage` na web, e vai em cabeçalho, **sem cookie**. 2. **Um papel por conta** no piloto. 3. Conta desativada responde o **mesmo `401`** do e-mail inexistente. 4. Senha com mínimo de 10 caracteres e sem outras regras; a senha provisória do operador **obriga a troca** no primeiro acesso (`troca_de_senha_obrigatoria`). 5. Prazo do acesso: **30 dias**; sair e trocar a senha o invalidam no servidor. 6. `429` com `espere_s`. 7. Vínculo professor-atleta **criado pelo operador**, sem convite por e-mail. 8. `termo_versao` gravado junto de `consentimento_em`. 9. Retirar o consentimento **mantém o vínculo** e volta a "Aguardando você", sem aviso ao professor no piloto. 10. O termo segue provisório e marcado até o texto definitivo, antes do primeiro aluno real. Estas decisões prevalecem sobre qualquer padrão abaixo.

## Decisão

### 1. Contas: o que entra no banco (modelo para aprovação)
Uma migração `0017`, **só aditiva** (tabelas novas e duas colunas anuláveis; nenhuma linha existente muda).

| Tabela | Colunas | Observações |
|---|---|---|
| `conta` | `id`; `email` (texto 254, **único**, guardado em minúsculas); `senha_hash` (texto); `atleta_id` FK `atleta.id` anulável **único**; `professor_id` FK `professor.id` anulável **único**; `ativa` (bool, padrão verdadeiro); `deve_trocar_senha` (bool); `criada_em`; `senha_trocada_em` | `CHECK ((atleta_id IS NULL) <> (professor_id IS NULL))`: **um papel por conta** (decisão 2 do Theo); quem testa os dois lados, como o Angelo, tem duas contas e dois e-mails. Sem papel "administrador": o operador age por comando, não por rota (item 6). |
| `sessao` | `id`; `conta_id` FK `conta.id` `ON DELETE CASCADE`; `token_hash` (SHA-256 em hexa, **único**); `criada_em`; `expira_em` (30 dias depois de `criada_em`); `revogada_em` anulável | O token em si **nunca** é guardado (só o hash), então um vazamento do banco não entrega sessões. |
| `tentativa_login` | `id`; `email_hash` (SHA-256 do e-mail em minúsculas); `ocorrida_em`; `ok` (bool) | Só para limitar força bruta (item 3). Sem IP no piloto (atrás do proxy do provedor o IP real depende de cabeçalho; ver "A confirmar", 7). Limpeza por comando: `limpar-sessoes-expiradas` apaga as tentativas com **mais de 30 dias** (o hash do e-mail é dado pessoal pseudonimizado; revisão do Caio, P3). |
| `vinculo_professor_atleta` (existente) | **+** `termo_versao` (texto 40, anulável, gravado **junto** de `consentimento_em`); **+** `consentimento_revogado_em` (datetime com fuso, anulável) | `consentimento_em` continua sendo "quando o atleta aceitou". O filtro da ADR 0015 (item 3) ganha `AND consentimento_revogado_em IS NULL`. |
| `consentimento_evento` | `id`; `atleta_id`; `professor_id`; `acao` (`aceito` ou `revogado`); `termo_versao`; `ocorrida_em` | **Só se acrescenta, nunca se altera** (trilha para a consulta de LGPD). O estado atual está no vínculo; o evento é a história. |

**O que não entra:** nome, telefone, data de nascimento ou documento na conta (o nome já está em `atleta` e `professor`); tabela de papéis (são duas colunas); tabela de "esqueci a senha" (item 6); IP e dispositivo.

**Alternativa recusada:** `consentimento` como tabela única de estado e histórico (uma linha por aceite, com `revogado_em`). Obrigaria reescrever o filtro de vínculo da ADR 0015, usado por toda rota de professor; ficam as duas colunas no vínculo e o evento à parte.

### 2. Senha
- **Hash: Argon2id** (biblioteca `argon2-cffi`, parâmetros padrão atuais da biblioteca, que seguem o OWASP: pelo menos 19 MiB de memória, 2 iterações, 1 de paralelismo). O hash carrega os parâmetros, então subir o custo depois só pede rehash no próximo login (`check_needs_rehash`).
- **Regra da senha:** mínimo **10 caracteres**, máximo 128, **sem regra de composição** (NIST SP 800-63B), recusa uma lista curta de senhas comuns guardada no código e recusa a senha igual ao e-mail. A senha **nunca** aparece em log, em erro nem em resposta.
- **Tempo constante:** e-mail inexistente também gasta um hash (de uma senha falsa fixa), para a resposta não revelar quais e-mails existem.

### 3. Sessão
- **Token opaco**, 32 bytes aleatórios (`secrets.token_urlsafe(32)`), devolvido **uma vez** no `POST /sessao`. O app manda `Authorization: Bearer <token>`. Sem cookie: no celular e na web o mesmo mecanismo, e sem cookie não há CSRF.
- **Por que não JWT:** não dá para revogar no logout nem na troca de senha sem uma lista no servidor, e já temos o banco. Token opaco com hash na tabela `sessao` é mais simples e revogável.
- **Validade: 30 dias** desde o login, fixos (sem renovar a cada uso; nenhuma escrita por requisição). Depois, entrar de novo.
- **Revogação:** `DELETE /sessao` revoga a sessão atual; trocar a senha revoga **todas** as sessões da conta, a atual inclusive (a resposta traz um token novo); desativar a conta revoga todas.
- **Força bruta:** depois de **5 falhas em 15 minutos** para o mesmo e-mail, o `POST /sessao` responde `429` com `espere_s` (segundos até poder tentar; o cabeçalho `Retry-After` repete) até a janela passar, **mesmo com a senha certa**. É por e-mail porque não confiamos num IP que o proxy repassa. Custo conhecido: quem sabe o e-mail de outro pode travar a conta dele por 15 minutos; no piloto (10 contas, sem cadastro aberto) é aceitável.
- **Onde o app guarda o token** (decisão 1 do Theo): no celular, o cofre do aparelho (`expo-secure-store`); na web, `sessionStorage` (morre ao fechar a aba). Sempre em cabeçalho, nunca em cookie. Risco conhecido: um XSS na web leria o token. Mitigação: CORS só com a origem do app, sem HTML de terceiros, CSP no proxy da web (#504).

### 4. Rotas de identidade
| Rota | Quem | O que faz |
|---|---|---|
| `POST /sessao` | pública | corpo `{email, senha}`; `200` com `{token, expira_em, papel, atleta_id, professor_id, nome, troca_de_senha_obrigatoria}` (um dos dois ids é `null`); credencial errada, e-mail inexistente e conta inativa dão a **mesma** `401`; `429` na força bruta |
| `GET /sessao` | sessão | quem sou: `papel`, `atleta_id`, `professor_id`, `nome`, `expira_em`, `troca_de_senha_obrigatoria`. É daqui que o app sabe o id; **somem** `EXPO_PUBLIC_ATLETA_ID` e `EXPO_PUBLIC_PROFESSOR_ID` (ficam só no modo de captura da API falsa) |
| `DELETE /sessao` | sessão | revoga a atual; `204` |
| `PUT /conta/senha` | sessão | `{senha_atual, senha_nova}`; revoga todas as sessões, devolve `{token, expira_em}` novo e zera `deve_trocar_senha` |

**Nome do campo (decisão do Theo):** nas respostas de `POST /sessao` e `GET /sessao` o campo é `troca_de_senha_obrigatoria`; `deve_trocar_senha` é só o nome da **coluna** em `conta`. **Erros de `PUT /conta/senha`:** `422` no formato do pydantic, com `type` `senha_atual_incorreta` (loc `senha_atual`) ou `senha_nova_invalida` (loc `senha_nova`) e o motivo em `msg`; a senha nunca é repetida.

`/health` e `POST /sessao` são as **únicas** rotas sem sessão. Em produção, `/docs` e `/openapi.json` ficam desligados (o `openapi.json` versionado em `packages/api-client/` continua sendo gerado por script).

### 5. Papéis e acesso: quem vê e quem corrige o quê
A forma das rotas **não muda**: `/atletas/{atleta_id}/...` e `/professores/{professor_id}/...`. Muda que o id do caminho é **comparado com a sessão**.

- **Sem sessão válida: `401`** com `WWW-Authenticate: Bearer`.
- **Recurso de outro:** `404` com o mesmo corpo de "não existe" (nunca `403`: não confirma que existe), como na Meta 11.
- **`/atletas/{id}/...`:** só a conta cuja `atleta_id` é `{id}`. **O professor não usa essas rotas**: o que ele pode ver do aluno chega pela caixa do dia (`detalhe`), já filtrado por vínculo e consentimento (ADR 0015, item 3).
- **`/professores/{id}/...`:** só a conta cuja `professor_id` é `{id}`; o filtro de vínculo e consentimento usa **sempre o `professor_id` da sessão**, nunca o do caminho.
- **Uma dependência só** (`conta_atual`, mais `atleta_da_sessao` e `professor_da_sessao`) em todo roteador, aplicada no `include_router`, não rota a rota. **Teste de cobertura:** percorre o OpenAPI do app real e falha para toda rota fora da lista explícita acima que responda algo diferente de `401` sem sessão. Rota nova sem proteção quebra o teste.

| Ação | Quem faz | Quem não faz |
|---|---|---|
| Upload de FIT, check-in, PSE, correção da **transição** (`PUT`/`DELETE`), semana-padrão, ler treino, carga, linha de base, feedback | só o **atleta dono** | professor (`404`), outro atleta (`404`) |
| Confirmar ou corrigir o **tipo** do treino (`PUT` em lote) | só o **professor** com vínculo + consentimento ativo | atleta (a rota é de professor); professor sem consentimento (`404`) |
| Registrar e revogar o **consentimento** | só o **atleta** | professor |
| Criar conta, vínculo, redefinir senha, desativar, excluir | só o **operador**, por comando (item 6) | ninguém por rota |

**A ordem das respostas é `401` (sem sessão), depois `403` (`troca_de_senha_obrigatoria`, item 6), depois `404` (de outro ou inexistente, com o mesmo corpo), depois `422` (corpo ou parâmetro inválido) e `409` (`editavel = false`)**, com um teste para a ordem (`test_acesso.py`, #500). O `404` de atleta alheio tem os mesmos bytes do de atleta inexistente, e o de professor alheio os do `professor_inexistente`. Isto cumpre a pergunta B da Meta 12 (só o atleta dono corrige a transição). O `409` por `transicao.editavel = false` (ADR 0004, adendo 12) continua valendo, depois da checagem de dono.

### 6. Operador, não administrador
Sem painel e sem rota de administração. Quem cuida do piloto (o Angelo e o time, com acesso ao servidor) usa **comandos** do pacote da API, o mesmo caminho dos workers:
`criar-conta` (no código, `python -m worker.conta criar`; os demais seguem o mesmo padrão: `vincular`, `redefinir-senha`, `desativar`, `limpar`; e-mail, atleta e/ou professor; pede a senha **sem eco**, nunca como argumento de linha de comando, para não cair no histórico do shell), `vincular` (professor e atleta, **sem** consentimento), `redefinir-senha`, `desativar-conta`, `excluir-conta` e `limpar-sessoes-expiradas`.
- **Redefinição de senha sem e-mail (decisão 3 do Angelo):** o atleta pede ao operador (fora do app); `redefinir-senha` gera uma senha temporária aleatória, **mostra uma vez no terminal**, marca `deve_trocar_senha` e revoga todas as sessões. O app força a tela de troca antes de qualquer outra rota (as rotas, fora `PUT /conta/senha`, `GET /sessao` e `DELETE /sessao`, respondem `403` com `type` `troca_de_senha_obrigatoria` enquanto a marca estiver ligada; isso **não contradiz** o `404` para recurso de outra pessoa: o `403` vale para a própria conta, antes de qualquer checagem de recurso, e não revela nada de ninguém). O operador passa a senha temporária por um canal que o atleta confia; ela vale só até a troca.
- Cada comando grava uma linha de log **sem e-mail, sem senha e sem dado de saúde**: só a ação, o `conta_id` e a hora.

### 7. Consentimento registrado pelo atleta
- O **vínculo** (professor X acompanha o atleta Y) é criado pelo operador. O **consentimento** é do atleta, e só dele.
- Rotas do atleta dono: `GET /atletas/{id}/professores` (vínculos com `nome` do professor, `consentimento` ativo ou não, `termo_versao`), `PUT /atletas/{id}/professores/{professor_id}/consentimento` (aceita a versão atual do termo; corpo `{termo_versao}`, recusado com `409` se a versão não for a vigente) e `DELETE` no mesmo caminho (revoga). `GET /termo-de-consentimento` (com sessão) devolve `{versao, provisorio, texto}`.
- **Efeito imediato:** ao revogar, a próxima leitura do professor já não traz o atleta (o filtro é calculado a cada leitura). **O vínculo permanece** e o atleta volta ao estado "Aguardando você"; o professor **não é avisado** no piloto (decisão 9). Os **dados do atleta não são apagados** pela revogação; a exclusão da conta é outra ação (item 9).
- Cada aceite e revogação grava um `consentimento_evento`.
- **Onde mora a versão vigente do termo:** numa **constante do código** (`TERMO_VIGENTE`). O filtro `atletas_do_professor` (ADR 0015, item 3) é a **única** função que decide quem o professor vê e ganha as duas condições novas: `consentimento_revogado_em IS NULL` e `termo_versao = TERMO_VIGENTE` (versão diferente vale como sem consentimento). Caixa, `detalhe`, `PUT` em lote do tipo, lista de alunos, contagem e `checkin_vencendo` passam por ela e por nenhuma outra. Teste da #501: o atleta revoga, e então nenhuma dessas respostas traz o atleta nem muda uma contagem (não vaza que o aluno existe).
- **Reaceite devolve o histórico todo.** Pelo desenho (vínculo e `consentimento_em <= agora`), quem aceita de novo volta a ser visto pelo professor **em tudo** que a rota expõe (a janela da caixa e o `detalhe`), não só do novo aceite em diante. O termo diz isso. É pergunta da consulta de LGPD (consentimento por período?).
- **Revogar não desfaz o que o professor registrou.** O tipo confirmado ou corrigido por ele (`tipo_confirmado_por/_em`) **continua** no treino do atleta; o professor só deixa de ler. O feedback que ficou `desatualizado` pelo tipo continua sendo refeito pelo worker, sem professor envolvido. O app do atleta não mostra o nome de quem confirmou.
- **O termo, provisório.** A versão de hoje se chama `termo@0-provisorio`. A API a devolve com `provisorio: true` e o app mostra, no alto, a faixa "Texto provisório, ainda sem revisão jurídica". Rascunho (sintético, **não é aconselhamento jurídico** e vale só para o Angelo e dados sintéticos):

  > **Termo de consentimento (provisório).** Ao aceitar, você autoriza o professor indicado a ver, no aplicativo, os seus treinos, o seu check-in (esforço percebido, sensação, atalhos e a observação que você escrever) e o feedback do treino, que pode citar o seu sono e a sua variabilidade da frequência cardíaca, para acompanhar a sua preparação. O professor não vê a sua carga de treino em números, a recuperação, o clima nem a sua semana-padrão, e não vê os dados de outros atletas; você também não vê os dos outros. **Quando o feedback automático estiver ligado**, um resumo do treino (números, sensação, esforço percebido e atalhos, entre eles o de dor, sem o seu nome e **sem a observação que você escrever**) é enviado a um serviço de inteligência artificial de terceiros, fora do Brasil, para redigir o feedback; esse envio não pode ser apagado por nós. Você pode revogar quando quiser, em Consentimento: a partir daí o professor deixa de ver os seus dados, mas o que ele já confirmou no seu treino (como o tipo) continua. Se você aceitar de novo, ele volta a ver todo o seu histórico. Revogar não apaga os seus dados: para apagar, peça ao operador. Estes são dados pessoais de saúde.

  **Os pontos sobre o serviço de IA, sobre o reaceite e sobre o que o professor mantém entram na revisão jurídica** (e valem só com o feedback ligado, ver o item 9). Trocar o texto sobe a versão (`termo@1`...) e **pede novo aceite**: o vínculo com `termo_versao` diferente da vigente vale como **sem consentimento** até o atleta aceitar de novo. O aceite do termo definitivo (depois da consulta de LGPD) é condição para o **primeiro aluno real** (decisão 4 do Angelo).

### 8. O que sai do `ATLETA_ID` e do `PROFESSOR_ID`
| Hoje | Depois |
|---|---|
| `PROFESSOR_ID` no ambiente (`Settings.professor_id`) | **removido**; o professor vem da sessão. A resposta uniforme `professor_inexistente` continua para qualquer id que não seja o da sessão |
| `EXPO_PUBLIC_ATLETA_ID` e `EXPO_PUBLIC_PROFESSOR_ID` | **removidos** do app real; o app chama `GET /sessao`. Ficam só na API falsa e nas capturas (fixtures sintéticas) |
| Testes de rota sem sessão | continuam chamando as rotas, com a conta de teste injetada por **sobrescrita da dependência** (`app.dependency_overrides`) num helper único. **Não existe variável nem flag que desligue o login no servidor**: a única forma de rodar sem sessão é o override em teste, para o ambiente de produção não ter como subir "aberto" por engano |
| Adendo curto na ADR 0015 (item 2) | aponta para esta ADR: a identidade do professor passa a vir da sessão e o `PROFESSOR_ID` some (feito neste PR) |
| Comandos do worker (`calcular_carga` etc.) | **não mudam**: falam com o banco, não com a API |
| Guias `meta-2` a `meta-12-como-rodar` | passam a citar a conta de teste; a Nina atualiza na #507 |

### 9. Segredos, logs, backup e exclusão
- **Segredos só no provedor** (variáveis de ambiente do serviço, marcadas como segredo), **fora do git**: URL do banco. **Sem chaves de LLM no provedor**: o `gerar_feedback` fica **desligado no servidor** (`LLM_PROVIDER` não configurado, motivo `provedor_nao_configurado`) até um novo "sim" explícito do Angelo, porque o limite da ADR 0013 (item 9, "só localmente, nunca CI nem servidor") continua valendo; o feedback real segue só local. Se o Angelo disser sim, entram a chave como segredo do provedor, a revisão do termo e a consulta de LGPD sobre o envio a terceiro (retenção do provedor ainda não verificada, ADR 0013, "A confirmar" 10). Não existe segredo de assinatura de sessão (token opaco). `.env.example` só com nomes e valores de exemplo. `SecretStr` em tudo que for chave, como hoje. Rotação: trocar no provedor e reimplantar; a senha do banco rotaciona sem mexer em dado.
- **Logs sem dado de saúde.** Proibidos em log: corpo de requisição, `Authorization`, senha, e-mail, check-in, observação, texto de feedback, valor de carga, FC, posição. Permitidos: método, caminho **com ids**, status, duração, `conta_id`. O log de acesso do servidor não grava query string; o handler de erro `422` **não devolve o campo `input`** do pydantic em produção (ele ecoaria a senha ou a observação digitada); exceção não tratada loga só o tipo e o local, não a mensagem. **A regra vale também para o worker**: o `gerar_feedback` e as exceções do provedor de LLM (LiteLLM) não escrevem pacote, prompt nem texto de feedback; só o tipo da exceção e o motivo em código. Um teste faz um `POST /sessao`, um check-in e uma geração de feedback com provedor falso que falha, todos com marcas sintéticas, e confere que nenhuma aparece na saída capturada do log.
- **Upload:** limite de **10 MB** (`TAMANHO_MAX_FIT`, ADR 0006) já é imposto pela API lendo em pedaços; o proxy repete o limite quando o provedor deixar configurar (#504). Detalhe em [[produto/meta-13-opcoes-deploy]].
- **Backup:** diário, retenção de **7 dias**, **na mesma região do banco**, acesso restrito à conta do provedor. Backup guarda dado de saúde: vale a mesma regra do banco. **Antes de o histórico real do Angelo entrar, uma restauração para um banco novo tem de ser feita e conferida** (contagem de linhas por tabela e uma conta que entra), registrada no guia (#505). Destruir o cluster destrói os backups do provedor; por isso o `pg_dump` periódico, cifrado, fica para a #505 decidir (ver "A confirmar", 8).
- **Exclusão de conta** (a pedido do atleta, pelo operador): `excluir-conta` apaga a conta, as sessões e **todos** os dados do atleta (atividades e tudo que pende delas, check-in, feedback, recuperação, carga, vínculos, eventos de consentimento do atleta). Um teste percorre **todas as tabelas com `atleta_id` ou chave para `atividade`** e prova que nada sobra, e falha quando uma tabela nova aparece sem ser tratada. A trilha `consentimento_evento` do atleta **também é apagada** (padrão, mais simples; ver "A confirmar", 12). Os backups antigos guardam o dado até a retenção acabar (7 dias); isso vai dito ao atleta. **Restaurar um backup depois de uma exclusão a ressuscitaria**: por isso o operador mantém um registro mínimo de exclusões (só `atleta_id` e data, **sem dado pessoal**, fora do banco que se restaura) e a restauração **reaplica as exclusões posteriores ao backup antes de abrir a API** (passo do guia da #505). **O que já foi enviado a um provedor de LLM não se apaga por nós**: com o feedback desligado no servidor, não houve envio e o atleta é informado disso; se ele for ligado, o termo e a exclusão dizem que o envio fica sob a política do provedor.
- **O que o professor mantém:** nenhum dado de leitura do aluno depois da revogação ou da exclusão. Na exclusão, o `tipo_confirmado_por` (id do professor em atividade) some junto com a atividade; na revogação, o tipo confirmado fica (item 7).

### 10. Deploy do piloto
- **DigitalOcean, só leitura de páginas públicas até o Angelo criar a conta.** Comparação e custo em [[produto/meta-13-opcoes-deploy]]. **Recomendação:** App Platform (API, worker e web estática) com PostgreSQL gerenciado, **porque dá HTTPS no endereço do provedor sem domínio próprio** (decisão 3 do Angelo), sem servidor para atualizar e com backup diário gerenciado.
- **Região: ainda a escolher pelo Angelo.** A DigitalOcean **não tem região no Brasil**; as mais próximas são Nova York (`nyc1`/`nyc3`), Atlanta (`atl1`, com restrições) e Toronto. Isso é **transferência internacional de dados** (LGPD, art. 33), que a consulta de LGPD precisa cobrir **antes do primeiro aluno real**; no piloto (sintético e dado do próprio Angelo) o risco é dele. Ver "A confirmar", 1.
- **Reproduzível:** a especificação do app (`.do/app.yaml`, sem segredo), `Dockerfile` da API e do worker e um passo de migração no deploy ficam no repositório (#504). O ensaio em Docker local vem antes da conta.
- **No ar só dado sintético e o do Angelo** (decisão 4). Nenhum outro aluno real antes da consulta de LGPD e do CNPJ.
- **Fora:** domínio próprio, e-mail transacional ("esqueci a senha" por e-mail), link mágico, login social, autoatendimento de cadastro, 2FA.

### 11. O que muda e quando
| O quê | Issue | Depende de |
|---|---|---|
| Migração `0017` (`conta`, `sessao`, `tentativa_login`, colunas do vínculo, `consentimento_evento`); `POST/GET/DELETE /sessao`, `PUT /conta/senha`; comandos do operador; `PROFESSOR_ID` removido | #499 | esta ADR aceita |
| `conta_atual` em todos os roteadores; `401` e `404`; teste que percorre o OpenAPI; transição só pelo dono; testes existentes com o override | #500 | #499 |
| Rotas e termo do consentimento; filtro de vínculo com revogação e versão do termo | #501 | #499 |
| Telas de entrar, sair, trocar senha e consentimento | #502, #503 | #498, #499, #501 |
| Imagens, `.do/app.yaml`, proxy, logs sem dado de saúde | #504 | esta ADR, #472; a subida, a conta do Angelo |
| Backup, restauração testada, `excluir-conta` | #505 | #504 (o script local adianta) |
| Contas e dados sintéticos no piloto; o histórico do Angelo só depois da #505 | #506 | #504, #500, #505 |

## A confirmar (padrão em negrito; sem resposta, vale o padrão)
1. **Região do provedor.** **`nyc3` (Nova York)**, a mais próxima do Brasil com todos os produtos. Alternativa: `tor1`. Pergunta ao Angelo, com o aviso da transferência internacional (art. 33 da LGPD) para a consulta.
2. **Teto de custo mensal.** **US$ 40** para o ensaio (estimativa em torno de US$ 31, em [[produto/meta-13-opcoes-deploy]]).
3. ~~Papéis por conta~~ **Decidido (Theo, 17/11): um papel por conta.**
4. ~~Validade da sessão~~ **Decidido: 30 dias fixos.**
5. **5 falhas em 15 minutos para o `429`.** Padrão nosso, sem fonte além das recomendações do NIST e do OWASP (a senha de 10 caracteres já está decidida).
6. ~~Token da web~~ **Decidido: `sessionStorage` na web, cofre no celular, cabeçalho, sem cookie.** Cookie `HttpOnly` fica para depois, se o piloto crescer.
7. **Limite de tentativas por e-mail, sem IP.** **Sim.** Alternativa: por IP, que exige confiar no cabeçalho do proxy.
8. **`pg_dump` cifrado além do backup do provedor.** **Decidir na #505**, porque destruir o cluster destrói os backups gerenciados e o piloto tem pouco dado; o custo é guardar o dump em outro lugar sob o mesmo cuidado.
9. **Professor lê o treino do aluno só pela caixa.** **Sim**, no piloto. A tela de treino do aluno para o professor vira outra meta, com a spec da Lia.
10. **Semana-padrão: só o atleta dono grava** nesta meta. Hoje o `definido_por` admite o professor; passar isso para uma rota `/professores/{id}/...` fica para quando houver a tela.
11. **Titular da conta do provedor** (decisão 6 do Angelo, em aberto): o código e esta ADR não dependem da resposta.
12. **Trilha de consentimento na exclusão** (revisão do Caio, T7). **Apagar junto** com o resto, mais simples. Alternativa: manter um evento anonimizado (sem `atleta_id`) como prova de que houve consentimento. Perguntar na consulta de LGPD.
13. **Feedback no servidor.** **Desligado** até um "sim" explícito do Angelo (item 9). Pergunta ao Angelo: ligar o `gerar_feedback` no servidor, com o texto real no banco do servidor e o pacote saindo para o provedor de LLM?
14. **Termo definitivo.** A revisão jurídica cobre o envio ao provedor de IA, o reaceite com histórico todo e o que o professor mantém depois da revogação.

## Consequências
- **Bom:** cada atleta e cada professor vê só o que é seu, por uma dependência única e um teste que impede rota esquecida; nenhum serviço novo além do banco; revogação e exclusão reais; sem `flag` que deixe a produção aberta.
- **Custo:** os testes de rota existentes passam por um helper de conta (trabalho da #500); sem e-mail, a senha esquecida depende do operador; o token da web morre ao fechar a aba (`sessionStorage`); a região é fora do país.
- **Risco aceito:** força bruta travando a conta de outra pessoa por 15 minutos; o termo é provisório até a consulta de LGPD.
