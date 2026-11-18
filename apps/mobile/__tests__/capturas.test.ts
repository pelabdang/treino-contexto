// Parte pura do comando `npm run capturas` (#418). O navegador em si não roda no `npm test`.
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { ACESSOS, SENHA_SINTETICA, acessoDaRota, SIMULACOES, ALTURA_MAXIMA, alturaAlta, criarEncerramento, ROTAS, TAMANHOS, TEMAS, arquivoDaRota, nomeArquivo, planoDeCapturas, validarApiUrl } = require("../scripts/capturas-lib.js");

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

describe("rotas da caixa do dia (#426)", () => {
  const caixa = ROTAS.filter((r: any) => r.nome.startsWith("caixa-do-dia"));
  it("tem a rota principal, o detalhe aberto e os estados simulados, em 390 e 1280, claro e escuro", () => {
    expect(caixa.map((r: any) => r.nome)).toEqual([
      "caixa-do-dia",
      "caixa-do-dia-detalhe",
      "caixa-do-dia-sem-alunos",
      "caixa-do-dia-sem-motivo",
      "caixa-do-dia-erro-rede",
      "caixa-do-dia-404",
      "caixa-do-dia-foco",
      "caixa-do-dia-selecao",
      "caixa-do-dia-folha",
      "caixa-do-dia-salvando",
      "caixa-do-dia-lote-erro",
      "caixa-do-dia-lote-salvo",
    ]);
    expect(caixa.every((r: any) => r.caminho === "/caixa-do-dia")).toBe(true);
    const plano = planoDeCapturas(["caixa-do-dia"], true);
    expect(plano.map((p: any) => nomeArquivo(p.rota, p.tema, p.tamanho))).toEqual([
      "caixa-do-dia-claro-390.png",
      "caixa-do-dia-claro-1280.png",
      "caixa-do-dia-claro-390-alto.png",
      "caixa-do-dia-escuro-390.png",
      "caixa-do-dia-escuro-1280.png",
      "caixa-do-dia-escuro-390-alto.png",
    ]);
  });
  it("a captura -selecao rola a lista até o fim", () => {
    expect(caixa.find((r: any) => r.nome === "caixa-do-dia-selecao").rolarAoFim).toBe(true);
  });
  it("toda simulação pedida existe", () => {
    for (const r of caixa) if (r.simular) expect(SIMULACOES[r.simular]).toBeDefined();
  });
  it("as simulações de lista só tiram dados da caixa", () => {
    const base = { alunos: [{ sem_motivo: false }, { sem_motivo: true }], novos: [1] };
    expect(SIMULACOES.vazio.alterar(base)).toEqual({ alunos: [], novos: [] });
    expect(SIMULACOES["sem-motivo"].alterar(base)).toEqual({ alunos: [{ sem_motivo: true }], novos: [] });
    expect(SIMULACOES["404"].status).toBe(404);
  });
  it("as simulações do lote: PUT pendurado, PUT recusado e leituras seguintes sem novos", () => {
    expect(SIMULACOES.salvando.put.pendurar).toBe(true);
    expect(SIMULACOES["lote-erro"].put.status).toBe(404);
    expect(SIMULACOES["lote-salvo"].depois({ alunos: [1], novos: [1, 2] })).toEqual({ alunos: [1], novos: [] });
  });
  it("toda rota que clica ou tecla tem só testIDs e teclas conhecidas", () => {
    for (const r of caixa) {
      for (const id of r.clicar ?? []) expect(id).toMatch(/^[a-z0-9-]+$/);
      for (const t of r.teclar ?? []) expect(["Tab", "Enter", "Escape"]).toContain(t);
    }
  });
});

describe("rotas de entrar, sair e trocar a senha (#502)", () => {
  const conta = ROTAS.filter((r: any) => /^(entrar|acesso|trocar-senha|conta-menu|sair)/.test(r.nome));
  it("cobre os estados da spec da Lia", () => {
    const nomes = conta.map((r: any) => r.nome);
    for (const n of ["entrar", "entrar-erro-401", "entrar-muitas-tentativas", "entrar-sem-rede", "entrar-expirou", "trocar-senha-primeiro-acesso", "trocar-senha-diferentes", "conta-menu", "conta-menu-professor", "sair-dialogo"]) {
      expect(nomes).toContain(n);
    }
  });
  it("sem o campo `acesso`: a caixa do dia abre como professor e as demais telas como atleta; `acesso: null` abre sem acesso", () => {
    expect(acessoDaRota({ nome: "x", caminho: "/caixa-do-dia" })).toBe(ACESSOS.professor);
    expect(acessoDaRota({ nome: "x", caminho: "/treino/1" })).toBe(ACESSOS.atleta);
    expect(acessoDaRota({ nome: "x", caminho: "/entrar", acesso: null })).toBeNull();
    expect(acessoDaRota({ nome: "x", caminho: "/", acesso: "trocar" })).toBe("token-sintetico-trocar");
  });
  it("toda simulação pedida existe e só dado sintético vai nos campos", () => {
    for (const r of conta) {
      if (r.simular) expect(SIMULACOES[r.simular]).toBeDefined();
      for (const [id, texto] of r.preencher ?? []) {
        expect(id).toMatch(/^campo-[a-z-]+$/);
        if (id === "campo-email") expect(texto).toMatch(/@exemplo\.com$/);
      }
    }
    expect(SENHA_SINTETICA).toMatch(/sintetica/);
  });
  it("a troca de senha capturada não passa pela API falsa (não revoga o acesso das outras capturas)", () => {
    expect(SIMULACOES["troca-ok"].senha.token).toBe(ACESSOS.atleta);
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

describe("modo alto", () => {
  it("não muda o plano padrão e acrescenta o 390-alto por rota e tema", () => {
    expect(planoDeCapturas()).toHaveLength(ROTAS.length * 4);
    const plano = planoDeCapturas(["treino-pronto"], true);
    expect(plano).toHaveLength(6);
    const nomes = plano.map((p: any) => nomeArquivo(p.rota, p.tema, p.tamanho));
    expect(nomes).toContain("treino-pronto-claro-390-alto.png");
    expect(nomes).toContain("treino-pronto-escuro-390-alto.png");
  });
  it("limita a altura entre a do celular e o teto", () => {
    expect(alturaAlta(100)).toBe(844);
    expect(alturaAlta(1500.2)).toBe(1501);
    expect(alturaAlta(99999)).toBe(ALTURA_MAXIMA);
    expect(alturaAlta(NaN)).toBe(844);
  });
});

describe("criarEncerramento", () => {
  it("roda as limpezas uma só vez, em ordem inversa, mesmo chamado duas vezes", async () => {
    const ordem: string[] = [];
    const limpezas = [() => ordem.push("a"), async () => void ordem.push("b")];
    const encerrar = criarEncerramento(limpezas);
    await Promise.all([encerrar(), encerrar()]);
    await encerrar();
    expect(ordem).toEqual(["b", "a"]);
  });
  it("segue em frente se uma limpeza falhar", async () => {
    const ordem: string[] = [];
    await criarEncerramento([() => ordem.push("a"), () => { throw new Error("x"); }])();
    expect(ordem).toEqual(["a"]);
  });
});
