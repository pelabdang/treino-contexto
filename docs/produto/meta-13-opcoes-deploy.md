---
tipo: nota
status: em-uso
dono: duda
atualizado: 2026-11-17
links: [[decisoes/0016-login-e-deploy-do-piloto]], [[produto/roadmap]], [[produto/plano-mvp-execucao]], [[decisoes/0006-upload-de-fit]], [[modulos/api]], [[modulos/worker]]
---
# Meta 13: opções de hospedagem, login e custo para o piloto (#472)

> Só leitura de páginas públicas, consultadas em **17/11/2026**. **Nenhuma conta criada, nenhum cartão, nenhum gasto.** Preços em dólar, sem imposto, mudam sem aviso: conferir de novo no dia de criar a conta. Para o ensaio do plano (1 professor e 10 atletas, seção 9). Dá a base da seção 10 da [[decisoes/0016-login-e-deploy-do-piloto]].

## O que o piloto precisa
API (FastAPI), worker (comandos agendados: carga, feedback, esforços, clima), PostgreSQL, o app web estático (Expo), **HTTPS sem domínio próprio** e **upload de FIT até 10 MB**. Decisões do Angelo (17/11): DigitalOcean, e-mail e senha na própria API, sem domínio e sem e-mail transacional.

## Hospedagem na DigitalOcean (fontes: [App Platform](https://www.digitalocean.com/pricing/app-platform), [bancos gerenciados](https://www.digitalocean.com/pricing/managed-databases), [Droplets](https://www.digitalocean.com/pricing/droplets), [regiões](https://docs.digitalocean.com/platform/regional-availability/), [backups do PostgreSQL](https://docs.digitalocean.com/products/databases/postgresql/how-to/restore-from-backups/), [limites do App Platform](https://docs.digitalocean.com/products/app-platform/details/limits/); todas consultadas em 17/11/2026)

| | **A. App Platform + PostgreSQL gerenciado** (recomendada) | **B. Droplet com Docker Compose** + banco no próprio Droplet | **C. Droplet + PostgreSQL gerenciado** |
|---|---|---|---|
| API | serviço de US$ 10 (1 vCPU, 1 GiB) | no Droplet de US$ 12 (2 GiB) | idem B |
| Worker | componente de US$ 5 (1 vCPU, 512 MiB) | no mesmo Droplet | idem B |
| App web | site estático, US$ 0 (até 3 no plano grátis, 1 GiB de saída cada) | servido pelo proxy do Droplet | idem B |
| Banco | PostgreSQL gerenciado, a partir de **US$ 15,15** (1 GiB, 1 vCPU, 10 a 30 GiB de disco) | no Droplet (sem custo extra, **mas** a gente cuida de atualização e backup) | idem A |
| Backup | diário, **7 dias**, restauração para um **novo** cluster (gerenciado) | backup do Droplet: +20% semanal ou +30% diário (US$ 2,40 a 3,60 no de 2 GiB) | gerenciado + opcional do Droplet |
| HTTPS sem domínio | **sim**, no endereço `*.ondigitalocean.app` | **não direto**: certificado pede um nome de domínio; sem domínio próprio sobra o IP puro ou um serviço de terceiros | idem B |
| Atualização do sistema | do provedor | **nossa** (Docker, sistema, proxy) | nossa |
| Limite de 10 MB | a API já impõe (ADR 0006); o provedor **não documenta** limite de corpo configurável, só 600 s de timeout de upload | configurável no proxy (Caddy ou nginx) | idem B |
| **Custo mensal estimado** | **US$ 10 + 5 + 15,15 = US$ 30,15** (+ saída acima do incluído a US$ 0,02/GiB, irrelevante no ensaio) | **US$ 12 a 15,60** (com backup) | **US$ 27 a 31** |
| Esforço para pôr no ar | médio (um `app.yaml` e as imagens) | maior (servidor, proxy, certificado) | maior |

**Recomendação: A.** O que decide é o HTTPS sem domínio próprio (decisão do Angelo) e não ter servidor para manter: o time é pequeno e a Meta 13 já tem login, backup e consentimento para fazer. B é a mais barata, mas o certificado sem domínio e a manutenção do servidor viram trabalho e risco de segurança num app com dado de saúde. O worker em A pode ser um componente de worker ou um job agendado; a #504 escolhe quando a conta existir.

**Teto proposto: US$ 40 por mês** (A custa cerca de US$ 30; o resto é folga para um plano maior de API, se o ensaio pedir). Acima disso o time para e pergunta.

## Região: não há no Brasil
A lista de regiões não tem nenhuma no Brasil nem na América do Sul. Com banco gerenciado e App Platform: Nova York (`nyc1`, `nyc2`, `nyc3`), São Francisco (`sfo2`, `sfo3`), Toronto (`tor1`), Amsterdã, Frankfurt, Londres, Singapura, Bangalore, Sydney; Atlanta (`atl1`), Richmond e Kansas City só com alguns planos. **Recomendação: `nyc3`** (a mais próxima do Brasil em rede, com todos os produtos). Consequência: os dados ficam **fora do Brasil**, o que é transferência internacional de dados pessoais (LGPD, art. 33). No piloto (sintético e o dado do próprio Angelo) o risco é dele; para o **primeiro aluno real**, a consulta de LGPD precisa cobrir isso.

## Login (o que cada opção pede)
| Opção | Custo | Conta nova | Muda no código | Para o piloto |
|---|---|---|---|---|
| **E-mail e senha na própria API** (decisão do Angelo) | US$ 0 | nenhuma | tabelas `conta` e `sessao`, hash Argon2id, rotas `/sessao` | **sim**; "esqueci a senha" por comando do operador |
| Link mágico por e-mail | e-mail transacional (conta e domínio de envio) | provedor de e-mail | um serviço a mais | **não**: pede e-mail transacional, fora do piloto |
| Provedor de identidade (terceiro) | grátis até um número de usuários, depois pago | conta no provedor | integração, e o dado de login sai do nosso banco | **não** agora: um serviço novo e uma conta a mais para 10 pessoas |

## O que muda no código e no repositório (para a #504)
Dockerfile da API e do worker; `.do/app.yaml` sem segredo; passo de migração no deploy; `Settings` lendo tudo do ambiente; resposta de erro `422` sem eco do campo digitado; logs sem dado de saúde ([[decisoes/0016-login-e-deploy-do-piloto]], item 9).

## PRECISA DO ANGELO
1. **Região:** `nyc3` (recomendada), ou outra da lista? Sabendo que não há região no Brasil.
2. **Teto de custo mensal:** US$ 40 serve?
3. **Titular da conta** da DigitalOcean (pessoa física ou CNPJ): não muda o código.
4. **Criar a conta** (só ele), colocar o cartão e me dizer quando estiver pronta; o time **nunca** cria conta nem cadastra cartão.

## Fora
Domínio próprio, e-mail transacional, CDN, monitoramento pago, ambiente de homologação separado.
