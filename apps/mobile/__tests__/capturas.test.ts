// Parte pura do comando `npm run capturas` (#418). O navegador em si não roda no `npm test`.
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { ROTAS, TAMANHOS, TEMAS, arquivoDaRota, nomeArquivo, planoDeCapturas, validarApiUrl } = require("../scripts/capturas-lib.js");

describe("plano de capturas", () => {
  it("combina cada rota com os dois temas e os dois tamanhos (390 x 844 e 1280)", () => {
    expect(TEMAS).toEqual(["claro", "escuro"]);
    expect(TAMANHOS.map((t: { largura: number; altura: number }) => [t.largura, t.altura])).toEqual([
      [390, 844],
      [1280, 900],
    ]);
    expect(planoDeCapturas()).toHaveLength(ROTAS.length * 4);
  });

  it("filtra por nome de rota e gera nomes únicos", () => {
    const plano = planoDeCapturas(["treino-pronto"]);
    expect(plano).toHaveLength(4);
    const nomes = plano.map((p: any) => nomeArquivo(p.rota, p.tema, p.tamanho));
    expect(new Set(nomes).size).toBe(4);
    expect(nomes).toContain("treino-pronto-escuro-390.png");
  });

  it("não tem rota repetida e inclui a tela do treino com feedback", () => {
    const nomes = ROTAS.map((r: any) => r.nome);
    expect(new Set(nomes).size).toBe(nomes.length);
    expect(ROTAS.some((r: any) => r.caminho === "/treino/107")).toBe(true);
  });
});

describe("validarApiUrl", () => {
  it("aceita API local em outra porta", () => {
    expect(validarApiUrl("http://127.0.0.1:8791")).toBe("http://127.0.0.1:8791");
    expect(validarApiUrl("http://localhost:8010/")).toBe("http://localhost:8010");
  });
  it("recusa as portas 8000 e 5433 e hosts que não são locais", () => {
    expect(() => validarApiUrl("http://localhost:8000")).toThrow(/8000/);
    expect(() => validarApiUrl("http://127.0.0.1:5433")).toThrow(/5433/);
    expect(() => validarApiUrl("https://exemplo.com:9000")).toThrow(/local/);
    expect(() => validarApiUrl("lixo")).toThrow(/inválida/);
  });
});

describe("arquivoDaRota", () => {
  const raiz = mkdtempSync(join(tmpdir(), "capturas-teste-"));
  beforeAll(() => {
    mkdirSync(join(raiz, "treino"));
    writeFileSync(join(raiz, "index.html"), "i");
    writeFileSync(join(raiz, "treino", "[id].html"), "t");
    writeFileSync(join(raiz, "semana-padrao.html"), "s");
  });
  afterAll(() => rmSync(raiz, { recursive: true, force: true }));

  it("resolve rota dinâmica, página estática e raiz", () => {
    expect(arquivoDaRota(raiz, "/treino/107")).toBe(join(raiz, "treino", "[id].html"));
    expect(arquivoDaRota(raiz, "/semana-padrao")).toBe(join(raiz, "semana-padrao.html"));
    expect(arquivoDaRota(raiz, "/")).toBe(join(raiz, "index.html"));
  });
  it("cai no index.html em rota desconhecida e não sai da pasta", () => {
    expect(arquivoDaRota(raiz, "/nada")).toBe(join(raiz, "index.html"));
    expect(arquivoDaRota(raiz, "/../../etc/passwd")).toBe(join(raiz, "index.html"));
  });
});
