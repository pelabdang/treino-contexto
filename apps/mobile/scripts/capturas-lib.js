// CommonJS (e não .mjs) para o Jest carregar sem flag. Parte pura do comando de capturas (#418): lista de rotas, tamanhos, temas, nomes de arquivo e
// resolução de rota do servidor estático. Testada em __tests__/capturas.test.ts.
const { existsSync, statSync } = require("node:fs");
const { join, normalize, sep } = require("node:path");

// Só dado sintético da API falsa (scripts/api-falsa.mjs). Os ids vêm do cabeçalho daquele arquivo.
// Acesso (#502): o app só abre com sessão. Cada captura começa com um acesso sintético já guardado em sessionStorage (ver ACESSOS), sem passar
// pela tela de entrar: `acesso: null` abre sem acesso; sem o campo, a caixa do dia usa o professor 1 e as demais telas o atleta 1.
// `preencher` digita nos campos (testID, texto) antes dos `clicar`.
const SENHA_SINTETICA = "senha-sintetica-123";
const ACESSOS = {
  atleta: "token-sintetico-atleta-1",
  professor: "token-sintetico-professor-1",
  expirado: "token-sintetico-expirado", // a API falsa responde sempre 401
  trocar: "token-sintetico-trocar", // atleta 1 com a troca de senha obrigatória
  // Atletas de teste do consentimento (ver api-falsa.mjs): 2 sem vínculos, 23 GET derruba, 24 PUT dá 409, 25 PUT derruba, 27 GET dá 500.
  atleta2: "token-sintetico-atleta-2",
  atleta23: "token-sintetico-atleta-23",
  atleta24: "token-sintetico-atleta-24",
  atleta25: "token-sintetico-atleta-25",
  atleta27: "token-sintetico-atleta-27",
};
const ENTRAR_ANA = [["campo-email", "atleta1@exemplo.com"], ["campo-senha", SENHA_SINTETICA]];
const TROCAR_OK = [["campo-senha-atual", SENHA_SINTETICA], ["campo-senha-nova", "outra-senha-sintetica"], ["campo-senha-repetida", "outra-senha-sintetica"]];
const ROTAS = [
  { nome: "treino-pronto", caminho: "/treino/107" }, // check-in feito, feedback pronto, carga pela PSE
  { nome: "treino-feedback-pendente", caminho: "/treino/112" },
  { nome: "treino-feedback-desatualizado", caminho: "/treino/113" },
  { nome: "treino-feedback-indisponivel", caminho: "/treino/114" },
  { nome: "treino-sem-checkin", caminho: "/treino/101" },
  { nome: "treino-prazo-vencido", caminho: "/treino/108" },
  { nome: "treino-carga-sem-fc", caminho: "/treino/106" }, // carga sem_carga com o motivo; forma calculada com treino sem carga no dia
  { nome: "treino-forma-aprendendo", caminho: "/treino/108" }, // carga calculada; forma aprendendo (sem CTL, ATL, TSB)
  { nome: "treino-carga-pendente", caminho: "/treino/109" },
  { nome: "treino-normal-fora", caminho: "/treino/101" }, // linha_base@3: pace e carga por hora fora do normal, FC dentro
  { nome: "treino-normal-aprendendo", caminho: "/treino/108" }, // uma métrica aprendendo e outra sem dado
  { nome: "treino-normal-sem-tipo", caminho: "/treino/112" }, // aviso neutro com o texto da API
  { nome: "treino-normal-multiesporte", caminho: "/treino/110" }, // sem o cartão
  { nome: "treino-esforcos-ciclismo", caminho: "/treino/109" }, // velocidade no lugar do pace
  { nome: "treino-esforcos-muitos", caminho: "/treino/130" }, // 12 esforços: mostra 8 e "Ver todos"
  { nome: "checkin-pergunta1", caminho: "/checkin/101" },
  // Caixa do dia do professor (#426). O professor vem do acesso sintético da captura (professor 1, ver ACESSOS). `clicar` abre linhas
  // do acordeão (testID) antes da captura; `simular` troca a resposta da caixa no navegador (ver SIMULACOES), sem outro export.
  { nome: "caixa-do-dia", caminho: "/caixa-do-dia" },
  { nome: "caixa-do-dia-detalhe", caminho: "/caixa-do-dia", clicar: ["treino-501", "treino-novo-512"] }, // observação só com o texto marcador
  { nome: "caixa-do-dia-sem-alunos", caminho: "/caixa-do-dia", simular: "vazio" },
  { nome: "caixa-do-dia-sem-motivo", caminho: "/caixa-do-dia", simular: "sem-motivo" },
  { nome: "caixa-do-dia-erro-rede", caminho: "/caixa-do-dia", simular: "rede" },
  { nome: "caixa-do-dia-404", caminho: "/caixa-do-dia", simular: "404" },
  // Lote (#427): `rolarAoFim` rola a lista até o fim (o último cartão tem de caber inteiro acima da barra); `teclar` aperta teclas (anel de foco por teclado); as demais abrem a folha, selecionam e salvam.
  { nome: "caixa-do-dia-foco", caminho: "/caixa-do-dia", teclar: ["Tab", "Tab"] },
  { nome: "caixa-do-dia-selecao", caminho: "/caixa-do-dia", clicar: ["selecionar-511", "mudar-tipo-512", "tipo-longo"], rolarAoFim: true },
  { nome: "caixa-do-dia-folha", caminho: "/caixa-do-dia", clicar: ["selecionar-511", "mudar-tipo-512"] },
  { nome: "caixa-do-dia-salvando", caminho: "/caixa-do-dia", simular: "salvando", clicar: ["selecionar-511", "selecionar-512", "salvar-lote"] },
  { nome: "caixa-do-dia-lote-erro", caminho: "/caixa-do-dia", simular: "lote-erro", clicar: ["selecionar-511", "selecionar-512", "salvar-lote"] },
  { nome: "caixa-do-dia-lote-salvo", caminho: "/caixa-do-dia", simular: "lote-salvo", clicar: ["selecionar-511", "mudar-tipo-512", "tipo-longo", "salvar-lote"] },
  // Entrar, sair, trocar a senha e acesso expirado (#502, spec docs/design/telas/entrar.md).
  { nome: "entrar", caminho: "/entrar", acesso: null },
  { nome: "entrar-preenchido", caminho: "/entrar", acesso: null, preencher: ENTRAR_ANA },
  { nome: "entrar-senha-visivel", caminho: "/entrar", acesso: null, preencher: ENTRAR_ANA, clicar: ["campo-senha-ver"] },
  { nome: "entrar-entrando", caminho: "/entrar", acesso: null, simular: "entrando", preencher: ENTRAR_ANA, clicar: ["botao-entrar"] },
  { nome: "entrar-erro-401", caminho: "/entrar", acesso: null, preencher: [["campo-email", "atleta1@exemplo.com"], ["campo-senha", "senha-errada-sintetica"]], clicar: ["botao-entrar"] },
  { nome: "entrar-muitas-tentativas", caminho: "/entrar", acesso: null, preencher: [["campo-email", "muitas@exemplo.com"], ["campo-senha", "qualquer-sintetica"]], clicar: ["botao-entrar"] },
  { nome: "entrar-sem-rede", caminho: "/entrar", acesso: null, simular: "entrar-rede", preencher: ENTRAR_ANA, clicar: ["botao-entrar"] },
  { nome: "entrar-erro-servidor", caminho: "/entrar", acesso: null, preencher: [["campo-email", "servidor@exemplo.com"], ["campo-senha", "qualquer-sintetica"]], clicar: ["botao-entrar"] },
  { nome: "entrar-expirou", caminho: "/treino/101", acesso: "expirado" },
  { nome: "acesso-verificando", caminho: "/", simular: "verificar-pendurado" },
  { nome: "acesso-sem-rede", caminho: "/", simular: "verificar-rede" },
  { nome: "trocar-senha-primeiro-acesso", caminho: "/", acesso: "trocar" },
  { nome: "trocar-senha", caminho: "/trocar-senha" },
  { nome: "trocar-senha-preenchida", caminho: "/trocar-senha", preencher: TROCAR_OK },
  { nome: "trocar-senha-diferentes", caminho: "/trocar-senha", preencher: [["campo-senha-atual", SENHA_SINTETICA], ["campo-senha-nova", "outra-senha-sintetica"], ["campo-senha-repetida", "outra-senha-diferente"]], clicar: ["botao-salvar"] },
  { nome: "trocar-senha-atual-errada", caminho: "/trocar-senha", preencher: [["campo-senha-atual", "senha-errada-sintetica"], ["campo-senha-nova", "outra-senha-sintetica"], ["campo-senha-repetida", "outra-senha-sintetica"]], clicar: ["botao-salvar"] },
  { nome: "trocar-senha-nova-invalida", caminho: "/trocar-senha", preencher: [["campo-senha-atual", SENHA_SINTETICA], ["campo-senha-nova", "curta"], ["campo-senha-repetida", "curta"]], clicar: ["botao-salvar"] },
  { nome: "trocar-senha-salva", caminho: "/trocar-senha", simular: "troca-ok", preencher: TROCAR_OK, clicar: ["botao-salvar"] },
  // Navegação por abas (UX, auditoria da Lia): barra na base (390) e menu lateral (1280). Início e Evolução mostram os tiros de 1 km.
  { nome: "aba-inicio", caminho: "/" },
  { nome: "aba-treinos", caminho: "/treinos" },
  { nome: "aba-evolucao", caminho: "/evolucao" },
  { nome: "aba-conta", caminho: "/conta" }, // atleta 1 tem pedido de consentimento: selo na aba e no item
  { nome: "aba-conta-sem-pedido", caminho: "/conta", acesso: "atleta2" },
  { nome: "aba-conta-professor", caminho: "/conta", acesso: "professor" },
  { nome: "aba-caixa-do-dia", caminho: "/caixa-do-dia" },
  { nome: "sair-dialogo", caminho: "/conta", clicar: ["conta-sair"] },
  // Consentimento do atleta (#503, spec docs/design/telas/consentimento.md).
  { nome: "consentimento", caminho: "/consentimento" },
  { nome: "consentimento-registrado", caminho: "/consentimento?aviso=registrado" },
  { nome: "consentimento-vazio", caminho: "/consentimento", acesso: "atleta2" },
  { nome: "consentimento-erro-rede", caminho: "/consentimento", acesso: "atleta23" },
  { nome: "consentimento-erro", caminho: "/consentimento", acesso: "atleta27" },
  { nome: "consentimento-retirar", caminho: "/consentimento", clicar: ["retirar-12"] },
  { nome: "consentimento-termo", caminho: "/consentimento/11" },
  { nome: "consentimento-termo-marcado", caminho: "/consentimento/11", clicar: ["li-e-concordo"] },
  { nome: "consentimento-termo-definitivo", caminho: "/consentimento/11", simular: "termo-definitivo" },
  { nome: "consentimento-termo-erro-salvar", caminho: "/consentimento/11", acesso: "atleta25", clicar: ["li-e-concordo", "dar-consentimento"] },
  { nome: "consentimento-termo-mudou", caminho: "/consentimento/11", acesso: "atleta24", clicar: ["li-e-concordo", "dar-consentimento"] },
  { nome: "consentimento-termo-erro", caminho: "/consentimento/11", simular: "termo-erro" },
];

// Acesso sintético que a captura guarda no navegador antes de abrir a rota (`null`: sem acesso).
function acessoDaRota(rota) {
  if ("acesso" in rota) return rota.acesso ? ACESSOS[rota.acesso] : null;
  return rota.caminho.startsWith("/caixa-do-dia") ? ACESSOS.professor : ACESSOS.atleta;
}

// Respostas simuladas da caixa do dia (só dado sintético). `alterar` recebe o JSON da API falsa; `abortar` derruba a conexão.
const SIMULACOES = {
  vazio: { alterar: (c) => ({ ...c, alunos: [], novos: [] }) },
  "sem-motivo": { alterar: (c) => ({ ...c, alunos: c.alunos.filter((a) => a.sem_motivo), novos: [] }) },
  rede: { abortar: true },
  // Lote: `put` troca a resposta do `PUT` (`pendurar` nunca responde: estado "salvando"); `depois` altera as leituras seguintes da caixa.
  salvando: { put: { pendurar: true } },
  "lote-erro": { put: { status: 404, corpo: { detail: [{ loc: ["body"], msg: "atividade não encontrada", type: "atividade_nao_encontrada" }] } } },
  "lote-salvo": { depois: (c) => ({ ...c, novos: [] }) },
  // Entrar (#502): `sessao` troca a resposta de `/sessao` no método dado (`abortar` derruba a conexão, `pendurar` nunca responde);
  // `senha` responde o `PUT /conta/senha` sem tocar na API falsa (que revogaria o acesso das outras capturas).
  "entrar-rede": { sessao: { metodo: "POST", abortar: true } },
  entrando: { sessao: { metodo: "POST", pendurar: true } },
  "verificar-rede": { sessao: { metodo: "GET", abortar: true } },
  "verificar-pendurado": { sessao: { metodo: "GET", pendurar: true } },
  "troca-ok": { senha: { token: "token-sintetico-atleta-1", expira_em: "2099-12-31T23:59:59Z" } },
  // Termo (#503): `termo` altera ou derruba a resposta de `GET /termo-de-consentimento` no navegador.
  "termo-definitivo": { termo: { alterar: (t) => ({ ...t, provisorio: false }) } },
  "termo-erro": { termo: { status: 500, corpo: { detail: "erro sintético" } } },
  "404": { status: 404, corpo: { detail: [{ loc: ["path", "professor_id"], msg: "professor inexistente", type: "professor_inexistente" }] } },
};
const TAMANHOS = [
  { nome: "390", largura: 390, altura: 844 },
  { nome: "1280", largura: 1280, altura: 900 },
];
const TAMANHO_ALTO = { nome: "390-alto", largura: 390, altura: 844, alto: true };
const ALTURA_MAXIMA = 3000;
const TEMAS = ["claro", "escuro"];
const PORTAS_PROIBIDAS = [8000, 5433];

const nomeArquivo = (rota, tema, tamanho) => `${rota.nome}-${tema}-${tamanho.nome}.png`;

// Todas as combinações rota x tema x tamanho, na ordem rota, tema, tamanho. `so` filtra rotas pelo nome.
// `alto` acrescenta o 390 com a altura do conteúdo (sufixo -390-alto), sem mudar os tamanhos padrão.
function planoDeCapturas(so = [], alto = false) {
  const rotas = so.length ? ROTAS.filter((r) => so.includes(r.nome)) : ROTAS;
  const plano = [];
  const tamanhos = alto ? [...TAMANHOS, TAMANHO_ALTO] : TAMANHOS;
  for (const rota of rotas) for (const tema of TEMAS) for (const tamanho of tamanhos) plano.push({ rota, tema, tamanho });
  return plano;
}

// Recusa porta de API proibida (8000 é a API de verdade; 5433 é o Postgres) e URL que não seja local.
function validarApiUrl(url) {
  let u;
  try {
    u = new URL(url);
  } catch {
    throw new Error(`CAPTURAS_API_URL inválida: ${url}`);
  }
  if (!["localhost", "127.0.0.1"].includes(u.hostname)) throw new Error("CAPTURAS_API_URL precisa ser local (localhost ou 127.0.0.1).");
  if (PORTAS_PROIBIDAS.includes(Number(u.port))) throw new Error(`Porta ${u.port} não é permitida: use a API falsa ou outra porta.`);
  return u.origin;
}

const ehArquivo = (p) => {
  try {
    return existsSync(p) && statSync(p).isFile();
  } catch {
    return false;
  }
};

// Arquivo do export estático para um caminho de URL: o próprio arquivo, `<caminho>.html`, `<caminho>/index.html`,
// a rota dinâmica `<pasta>/[id].html`, ou o index.html (rota desconhecida, como num host de página única).
function arquivoDaRota(raiz, caminho) {
  const limpo = normalize(decodeURIComponent(caminho.split("?")[0])).replace(/^(\.\.[/\\])+/, "");
  const base = join(raiz, limpo);
  const padrao = join(raiz, "index.html");
  if (!base.startsWith(raiz)) return padrao;
  const candidatos = [base, `${base}.html`, join(base, "index.html")];
  const partes = limpo.split(sep).filter(Boolean);
  if (partes.length >= 2) candidatos.push(join(raiz, ...partes.slice(0, -1), "[id].html"));
  return candidatos.find(ehArquivo) ?? padrao;
}

// Altura da janela para o modo alto: a do conteúdo medido (scrollHeight), no mínimo a do celular e no máximo ALTURA_MAXIMA.
function alturaAlta(medida, minima = 844) {
  const n = Number.isFinite(medida) ? Math.ceil(medida) : minima;
  return Math.min(ALTURA_MAXIMA, Math.max(minima, n));
}

// Encerramento idempotente: roda as limpezas (em ordem inversa) uma só vez, mesmo chamado várias vezes.
function criarEncerramento(limpezas) {
  let promessa = null;
  return () => {
    promessa ??= (async () => {
      for (const f of limpezas.splice(0).reverse()) {
        try {
          await f();
        } catch {}
      }
    })();
    return promessa;
  };
}

module.exports = { ACESSOS, SENHA_SINTETICA, acessoDaRota, SIMULACOES, TAMANHO_ALTO, ALTURA_MAXIMA, alturaAlta, criarEncerramento, ROTAS, TAMANHOS, TEMAS, PORTAS_PROIBIDAS, nomeArquivo, planoDeCapturas, validarApiUrl, arquivoDaRota };
