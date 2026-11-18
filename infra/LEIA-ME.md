# Deploy do piloto: preparação local (issue #504)

Rascunho da Duda para o Theo e a Nina. **Nada foi aplicado no provedor**: a conta é do Angelo. Aqui está só o que o repositório já traz e o que ainda espera por ele.
Contexto: [[decisoes/0016-login-e-deploy-do-piloto]] (itens 9 e 10) e [[produto/meta-13-opcoes-deploy]]. Só dado sintético.

## O que há no repositório
| Arquivo | Para quê |
|---|---|
| `services/api/Dockerfile` | uma imagem só para a API, a migração e os comandos do worker (contexto do build = raiz). Roda sem root, sem segredo, sem chave de LLM |
| `.do/app.yaml` | App Platform: serviço `api` (em `/api`), job `migrar` (`PRE_DEPLOY`, `alembic upgrade head`), site estático `web` (em `/`) e o PostgreSQL gerenciado. Sem segredo: a URL do banco é o binding `${banco.DATABASE_URL}` |
| `infra/docker-compose.ensaio-deploy.yml` e `infra/ensaio-deploy.sh` | ensaio local da mesma imagem com um Postgres descartável |
| `infra/backup/` | backup cifrado, restauração e ensaio (#505) |

## Ensaio local (feito)
`infra/ensaio-deploy.sh` sobe a imagem de produção e confere: migração e `/health`; `/docs`, `/redoc` e `/openapi.json` dão 404; rota de dado sem sessão dá 401; login, 200 no próprio dado e 404 no de outro atleta;
upload de 11 MB recusado (413); log com método, caminho e status, **sem** query string, senha, token nem marca. O web estático foi exportado (`expo export`) com `EXPO_PUBLIC_API_URL` e a URL entrou no bundle.

## Variáveis de ambiente (nomes; sem valores)
| Variável | Onde | Para quê |
|---|---|---|
| `DATABASE_URL` | api, migrar (segredo, binding do banco) | aceita `postgresql://` do provedor; a API converte para o driver psycopg |
| `AMBIENTE` | api | `producao` desliga `/docs`, `/redoc` e `/openapi.json` |
| `CORS_ORIGENS` | api | `${APP_URL}` (mesma origem, por segurança) |
| `FIT_DIR` | api | pasta dos FIT guardados (disco efêmero, ver abaixo) |
| `EXPO_PUBLIC_API_URL` | web, em tempo de build | `${APP_URL}/api` |
| `LLM_*`, chaves de LLM, `GARMIN_*` | **não existem no servidor** | `gerar_feedback` desligado (item 13) |

`PROFESSOR_ID` saiu do `Settings` e do `.env.example`: o professor vem da sessão.

## Worker
Sem componente contínuo (economiza US$ 5/mês e não há processo a manter): os comandos rodam sob demanda na mesma imagem, pelo console do componente `api`
(`python -m worker.<comando>`; por exemplo `worker.conta criar`, `worker.carregar_piloto`, `worker.excluir_conta`). Uma rotina agendada entra como job quando houver uma que precise (ex.: `preencher_clima`).

## Backup diário e registro de exclusões (proposta)
- **Backup diário, 7 dias:** o do PostgreSQL gerenciado (já na nota de opções), restaurável para um **novo** cluster.
- **`pg_dump` cifrado com age (#505):** rodado pelo operador a partir de uma máquina dele (não há disco persistente no App Platform nem Spaces no orçamento). A chave **privada** fica com o Angelo.
- **Registro de exclusões:** arquivo do operador, **fora** do banco que se restaura (só `atleta_id` e data). `worker.excluir_conta` roda do operador contra o banco do provedor; `restaurar.sh` o reaplica.

## O que o App Platform não tem (decisões para o Theo)
1. **Disco persistente:** os FIT enviados (`FIT_DIR`) somem a cada deploy. O que se perde é o arquivo bruto guardado; as atividades já importadas ficam no banco. Opções: aceitar no piloto; ou mover para armazenamento de objetos (Spaces, custo e código novos).
2. **Limite de 10 MB no proxy:** o provedor não documenta limite de corpo configurável. A API já recusa acima de 10 MB (413, testado no ensaio); o corpo grande ainda chega até ela.
3. **CORS e `Authorization`:** `allow_headers=[]` em `app/main.py` não libera `Authorization` nem `Content-Type: application/json` para outra origem. Em produção (mesma origem) não importa; para o web em desenvolvimento (`localhost:8081` chamando a API) a #502 vai precisar liberar esses dois cabeçalhos.
4. **Rotas do app ainda usam `EXPO_PUBLIC_ATLETA_ID`:** até a #502 (telas de entrar) o app não consegue entrar; a API responde 401.

## PRECISA DO ANGELO
Região (`nyc` no spec; o banco em `nyc3`), teto de custo (US$ 40/mês; estimativa sem o worker, em torno de US$ 25), titular da conta, **criar a conta e o cluster**, autorizar o GitHub no App Platform e **guardar a chave privada do age**.
