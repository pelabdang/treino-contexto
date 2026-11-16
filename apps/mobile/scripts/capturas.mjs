// Capturas da tela web por comando, sem extensão de navegador (#418). Uso: npm run capturas
//   npm run capturas -- --so=treino-pronto,treino-sem-checkin   (só algumas rotas)
//   npm run capturas -- --alto   (ou CAPTURAS_ALTURA=1: acrescenta o 390 com a altura do conteúdo, `-390-alto.png`)
// Variáveis: CAPTURAS_PASTA (padrão apps/mobile/capturas, ignorada pelo git),
//            CAPTURAS_API_URL (API local; padrão: sobe a API falsa numa porta livre; nunca 8000 nem 5433).
// Exporta a web (com a URL da API embutida), serve o export, abre as rotas num Chromium sem janela
// (Playwright), troca o tema por prefers-color-scheme e derruba tudo no fim. Só dado sintético.
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { createServer } from "node:http";
import { createServer as servidorTcp } from "node:net";
import { tmpdir } from "node:os";
import { dirname, extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import lib from "./capturas-lib.js";

const { arquivoDaRota, nomeArquivo, planoDeCapturas, validarApiUrl, alturaAlta, criarEncerramento } = lib;

const app = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const pasta = resolve(process.env.CAPTURAS_PASTA ?? join(app, "capturas"));
const so = (process.argv.find((a) => a.startsWith("--so=")) ?? "").slice(5).split(",").filter(Boolean);
const alto = process.argv.includes("--alto") || !!process.env.CAPTURAS_ALTURA;
const TIPOS = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".ttf": "font/ttf", ".png": "image/png", ".ico": "image/x-icon", ".svg": "image/svg+xml" };

const portaLivre = () =>
  new Promise((ok, falha) => {
    const s = servidorTcp();
    s.once("error", falha);
    s.listen(0, "127.0.0.1", () => {
      const { port } = s.address();
      s.close(() => ok(port));
    });
  });
const esperar = async (url, tentativas = 50) => {
  for (let i = 0; i < tentativas; i++) {
    try {
      await fetch(url);
      return;
    } catch {
      await new Promise((r) => setTimeout(r, 200));
    }
  }
  throw new Error(`Nada respondeu em ${url}`);
};

const limpezas = [];
let api = null;
let saida = null;
// Mata a API primeiro e depois faz o resto; idempotente (dois sinais, ou sinal e fim normal, rodam uma vez só).
const matarApi = () => {
  try {
    api?.kill();
  } catch {}
};
const limpar = criarEncerramento(limpezas);
const encerrar = () => {
  matarApi();
  return limpar();
};
for (const sinal of ["SIGINT", "SIGTERM"]) process.on(sinal, () => encerrar().finally(() => process.exit(130)));
// Último recurso, síncrono: se o processo sair por qualquer caminho, a API e o tmp não ficam.
process.on("exit", () => {
  matarApi();
  if (saida) rmSync(saida, { recursive: true, force: true });
});

const executar = (cmd, args, opcoes) =>
  new Promise((ok, falha) => {
    const filho = spawn(cmd, args, opcoes);
    limpezas.push(() => filho.kill());
    filho.on("error", falha);
    filho.on("exit", (codigo) => (codigo === 0 ? ok() : falha(new Error(`${cmd} ${args[0]} saiu com código ${codigo}`))));
  });

async function principal() {
  const plano = planoDeCapturas(so, alto);
  if (!plano.length) throw new Error(`Nenhuma rota com esses nomes: ${so.join(", ")}`);
  const inicio = Date.now();

  let apiUrl;
  if (process.env.CAPTURAS_API_URL) {
    apiUrl = validarApiUrl(process.env.CAPTURAS_API_URL);
  } else {
    const porta = await portaLivre();
    apiUrl = validarApiUrl(`http://127.0.0.1:${porta}`);
    api = spawn(process.execPath, [join(app, "scripts/api-falsa.mjs"), String(porta)], { stdio: "ignore" });
    await esperar(`${apiUrl}/atletas/1/atividades/107`);
  }

  saida = mkdtempSync(join(tmpdir(), "capturas-web-"));
  limpezas.push(() => rmSync(saida, { recursive: true, force: true }));
  console.log("Exportando a web...");
  await executar("npx", ["expo", "export", "--platform", "web", "--output-dir", saida], {
    cwd: app,
    stdio: "inherit",
    env: { ...process.env, CI: "1", EXPO_PUBLIC_API_URL: apiUrl, EXPO_PUBLIC_ATLETA_ID: "1" },
  });

  const web = createServer((req, res) => {
    const arquivo = arquivoDaRota(saida, req.url ?? "/");
    res.writeHead(200, { "content-type": TIPOS[extname(arquivo)] ?? "application/octet-stream" }).end(readFileSync(arquivo));
  });
  await new Promise((ok) => web.listen(0, "127.0.0.1", ok));
  limpezas.push(() => new Promise((ok) => web.close(ok)));
  const base = `http://127.0.0.1:${web.address().port}`;

  let chromium;
  try {
    ({ chromium } = await import("playwright"));
  } catch {
    throw new Error("Playwright não está instalado. Rode `npm ci` em apps/mobile.");
  }
  let navegador;
  try {
    navegador = await chromium.launch();
  } catch (e) {
    throw new Error(`Navegador não encontrado. Rode uma vez: npx playwright install chromium-headless-shell\n${e.message.split("\n")[0]}`);
  }
  limpezas.push(() => navegador.close());

  mkdirSync(pasta, { recursive: true });
  for (const { rota, tema, tamanho } of plano) {
    const ctx = await navegador.newContext({
      viewport: { width: tamanho.largura, height: tamanho.altura },
      colorScheme: tema === "escuro" ? "dark" : "light",
      locale: "pt-BR",
      deviceScaleFactor: 1,
    });
    const pagina = await ctx.newPage();
    await pagina.goto(base + rota.caminho, { waitUntil: "networkidle" });
    await pagina.evaluate(() => document.fonts.ready);
    await pagina.waitForTimeout(300);
    if (tamanho.alto) {
      // O conteúdo rola dentro de um elemento da tela, não na página: mede o maior scrollHeight e redimensiona a janela.
      const medida = await pagina.evaluate(() => Math.max(...[...document.querySelectorAll("*")].map((e) => e.scrollHeight)));
      await pagina.setViewportSize({ width: tamanho.largura, height: alturaAlta(medida, tamanho.altura) });
      await pagina.waitForTimeout(300);
    }
    const arquivo = join(pasta, nomeArquivo(rota, tema, tamanho));
    await pagina.screenshot({ path: arquivo, fullPage: true });
    console.log(`  ${arquivo}`);
    await ctx.close();
  }
  console.log(`OK: ${plano.length} capturas em ${pasta} (${Math.round((Date.now() - inicio) / 1000)} s).`);
}

principal()
  .catch((e) => {
    console.error(`FALHOU: ${e.message}`);
    process.exitCode = 1;
  })
  .finally(encerrar);
