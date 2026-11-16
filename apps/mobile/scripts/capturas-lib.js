// CommonJS (e não .mjs) para o Jest carregar sem flag. Parte pura do comando de capturas (#418): lista de rotas, tamanhos, temas, nomes de arquivo e
// resolução de rota do servidor estático. Testada em __tests__/capturas.test.ts.
const { existsSync, statSync } = require("node:fs");
const { join, normalize, sep } = require("node:path");

// Só dado sintético da API falsa (scripts/api-falsa.mjs). Os ids vêm do cabeçalho daquele arquivo.
const ROTAS = [
  { nome: "treino-pronto", caminho: "/treino/107" }, // check-in feito, feedback pronto, carga pela PSE
  { nome: "treino-feedback-pendente", caminho: "/treino/112" },
  { nome: "treino-feedback-desatualizado", caminho: "/treino/113" },
  { nome: "treino-feedback-indisponivel", caminho: "/treino/114" },
  { nome: "treino-sem-checkin", caminho: "/treino/101" },
  { nome: "treino-prazo-vencido", caminho: "/treino/108" },
  { nome: "checkin-pergunta1", caminho: "/checkin/101" },
];
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

module.exports = { TAMANHO_ALTO, ALTURA_MAXIMA, alturaAlta, criarEncerramento, ROTAS, TAMANHOS, TEMAS, PORTAS_PROIBIDAS, nomeArquivo, planoDeCapturas, validarApiUrl, arquivoDaRota };
