---
tipo: guia
status: em-uso
dono: nina
atualizado: 2026-11-18
links: [[decisoes/0016-login-e-deploy-do-piloto]], [[produto/meta-13-opcoes-deploy]], [[produto/roadmap]], [[modulos/worker]], [[modulos/banco]], [[glossario]]
---
# Meta 13: backup, restauração e exclusão de conta

> Parte local da #505 (scripts, comando, testes e o ensaio no Docker), pronta e revisada. A **#505 segue aberta** até a restauração no provedor ser feita e registrada; o que depende da conta na DigitalOcean (#504) e do Angelo está em "O que espera".
> Só dado **sintético** aqui. O histórico real do Angelo só entra no servidor **depois** de uma restauração feita e conferida (decisão 5 do Angelo, ADR 0016, item 9).

## Backup diário
`infra/backup/backup.sh` faz `pg_dump` (formato custom) e **cifra com `age`**: no servidor fica só a chave **pública**; a privada fica com o Angelo, fora do servidor e fora do git.
Sem a chave pública o script **para** (nunca grava dump sem cifra). Retenção de **7 dias** (`RETENCAO_DIAS`), apaga só os arquivos `treino-*.dump.age` da pasta.

```
DATABASE_URL=...  BACKUP_DIR=/pasta/segura  BACKUP_RECIPIENT=age1...  infra/backup/backup.sh
```
Saída: só o nome e o tamanho do arquivo (a URL tem senha e nunca é impressa). Agendamento: um job diário no provedor ou o backup gerenciado dele (decisão da #504).

## Restauração (sempre para um banco NOVO e vazio)
`infra/backup/restaurar.sh`: decifra, `pg_restore` no banco novo, **reaplica as exclusões** feitas depois do backup e imprime a contagem de linhas por tabela.
```
BACKUP_ARQUIVO=... BACKUP_CHAVE=/fora-do-servidor/chave.txt RESTAURAR_URL=postgresql://.../banco_novo \
REGISTRO_EXCLUSOES=/fora-do-banco/exclusoes.jsonl CONFERIR_ARGS="--email conta-de-teste@exemplo.com" infra/backup/restaurar.sh   # a senha da conta de teste vem pela entrada padrão
```
Conferência: a contagem por tabela bate com a do banco de origem (menos o que foi excluído depois) e **uma conta entra** (`login: ok`). Só então a API é apontada para o banco restaurado.

## Exclusão de conta (operador, a pedido do atleta)
```
uv run python -m worker.excluir_conta excluir --atleta 3 --confirmar 3 --registro /fora-do-banco/exclusoes.jsonl
```
Apaga a conta, as sessões e **todos** os dados do atleta: atividades e o que pende delas (segmentos, blocos, carga, clima, rótulo de transição, check-in e feedback), carga e
recuperação, limiares e zonas, recordes, semana-padrão, vínculos, a trilha de consentimento e os FIT guardados. O professor e a assessoria ficam; o tipo que o professor confirmou
some junto com a atividade. **Não tem volta.** Antes de apagar, grava `{atleta_id, data}` no registro (só isso).
- **Os backups antigos guardam o dado até a retenção acabar (7 dias):** diga isso ao atleta.
- **Restaurar um backup anterior à exclusão a ressuscitaria:** por isso o registro fica **fora** do banco, e `restaurar.sh` roda `worker.excluir_conta reaplicar` antes de abrir a API.
- Um teste percorre **todas as tabelas** que dependem do atleta por chave estrangeira e **falha** quando aparece tabela nova sem tratamento em `app/servicos/exclusao.py`.

## Registro do ensaio local (Docker, Postgres 16, dado sintético)
`infra/backup/ensaio-local.sh` refaz tudo: banco de origem com dois atletas sintéticos e duas contas, backup cifrado, exclusão do atleta 2 **depois** do backup, restauração para
um banco novo, reaplicação da exclusão e login de uma conta.

| Data | Backup (cifrado) | Resultado |
|---|---|---|
| 18/11/2026 | 87 975 bytes | origem: 2 atletas, 10 atividades, 2 contas; restaurado após reaplicar: 1 atleta, 5 atividades, 1 conta, blocos 42→21, segmentos 72→36, carga 10→5; `login: ok`; arquivo sem o cabeçalho `PGDMP` (cifrado) |

## O que espera (não é da Duda)
1. **Conta e banco na DigitalOcean (Angelo, #504):** onde roda o job diário, onde ficam os backups (mesma região do banco) e o backup gerenciado. A restauração **no provedor** (para um novo cluster) só se ensaia com a conta; a local já está provada.
2. **Chave privada do `age` (Angelo):** decidido pelo Theo (ADR 0016, "A confirmar", 8): `age`, só a chave pública no servidor. O Angelo gera o par, guarda a privada **fora do repositório e do servidor** e passa só a pública (`age1...`). Sem a privada, nenhum backup abre. Instalar o `age` onde o script rodar.
3. **Onde mora o registro de exclusões** em produção (fora do banco que se restaura; só ids e datas). Decidir na #504.
4. **Trilha de consentimento na exclusão (ADR 0016, "A confirmar", 12):** o padrão implementado **apaga** a trilha junto, e fica assim **até a consulta de LGPD** (decisão do Theo). Se ela pedir prova anonimizada, muda.
