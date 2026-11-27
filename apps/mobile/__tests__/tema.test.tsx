import { readFileSync } from "fs";
import { join } from "path";
import { render, screen } from "@testing-library/react-native";
import { Text, useColorScheme } from "react-native";

import { cores, espaco, fonte, raio, useTema } from "../src/tema";

jest.mock("react-native/Libraries/Utilities/useColorScheme", () => ({ default: jest.fn() }));

const TOKENS_MD = join(__dirname, "../../../docs/design/tokens.md");

// Lê a tabela "Cores" de docs/design/tokens.md: | `cor.nome` | `#claro` | `#escuro` | uso |
function lerTabelaCores(): Record<string, { claro: string; escuro: string }> {
  const md = readFileSync(TOKENS_MD, "utf8");
  const secao = md.split("\n## Cores\n")[1].split("\n## ")[0];
  const tabela: Record<string, { claro: string; escuro: string }> = {};
  for (const linha of secao.split("\n")) {
    const m = linha.match(/^\| `cor\.([^`]+)` \| `(#[0-9A-Fa-f]{6})` \| `(#[0-9A-Fa-f]{6})` \|/);
    if (m) tabela[m[1]] = { claro: m[2].toUpperCase(), escuro: m[3].toUpperCase() };
  }
  return tabela;
}

describe("tema x docs/design/tokens.md", () => {
  const tabela = lerTabelaCores();

  it("leu a tabela de cores", () => {
    expect(Object.keys(tabela).length).toBeGreaterThanOrEqual(30);
  });

  it("todo token do guia existe no tema, claro e escuro, com o mesmo valor", () => {
    for (const [nome, v] of Object.entries(tabela)) {
      expect({ nome, claro: (cores.claro as Record<string, string>)[nome]?.toUpperCase() }).toEqual({ nome, claro: v.claro });
      expect({ nome, escuro: (cores.escuro as Record<string, string>)[nome]?.toUpperCase() }).toEqual({ nome, escuro: v.escuro });
    }
  });

  it("o tema não tem cor que o guia não tem", () => {
    expect(Object.keys(cores.claro).sort()).toEqual(Object.keys(tabela).sort());
    expect(Object.keys(cores.escuro).sort()).toEqual(Object.keys(tabela).sort());
  });

  it("espaçamento, raio e tipografia batem com o guia", () => {
    expect(Object.values(espaco)).toEqual([4, 8, 12, 16, 24, 32, 48]);
    expect(raio).toEqual({ pequeno: 4, bloco: 8, botao: 10, cartao: 12, "cartao-destaque": 14, pilula: 999 });
    expect(fonte.corpo).toMatchObject({ fontFamily: "Inter_400Regular", fontSize: 16, lineHeight: 24 });
    expect(fonte["numero-destaque"]).toMatchObject({ fontFamily: "BarlowCondensed_800ExtraBold", fontSize: 30, fontVariant: ["tabular-nums"] });
    expect(fonte["numero-heroi"]).toMatchObject({ fontFamily: "BarlowCondensed_800ExtraBold", fontSize: 76 });
    expect(fonte["titulo-tela"]).toMatchObject({ fontFamily: "Inter_800ExtraBold", fontSize: 26 });
    expect(fonte.eixo).toMatchObject({ fontSize: 12, fontVariant: ["tabular-nums"] });
  });
});

describe("identidade v3", () => {
  it("o volt é a marca e o botão primário muda de tinta no escuro", () => {
    expect(cores.claro.marca).toBe("#C6F432");
    expect(cores.claro.botao).toBe("#12200A");
    expect(cores.claro["sobre-botao"]).toBe("#C6F432");
    expect(cores.escuro.botao).toBe("#D2FF3C");
    expect(cores.escuro["sobre-botao"]).toBe("#121A05");
  });

  it("o teal da v2 saiu do tema", () => {
    for (const nome of ["destaque", "destaque-suave", "destaque-pressionado", "sobre-destaque"]) {
      expect(nome in cores.claro).toBe(false);
      expect(nome in cores.escuro).toBe(false);
    }
  });
});

describe("useTema", () => {
  function Amostra() {
    const { cor, escuro } = useTema();
    return <Text>{`${escuro ? "escuro" : "claro"} ${cor.fundo}`}</Text>;
  }
  const esquema = useColorScheme as unknown as jest.Mock;

  it("segue o tema escuro do sistema", async () => {
    esquema.mockReturnValue("dark");
    await render(<Amostra />);
    expect(screen.getByText("escuro #0F1214")).toBeTruthy();
  });

  it("usa o claro quando o sistema é claro ou não informa", async () => {
    esquema.mockReturnValue(null);
    await render(<Amostra />);
    expect(screen.getByText("claro #F6F5F1")).toBeTruthy();
  });
});

describe("margem da tela", () => {
  it("16 no celular, 24 a partir de 600", () => {
    const { margemDaTela } = require("../src/tema");
    expect(margemDaTela(320)).toBe(16);
    expect(margemDaTela(599)).toBe(16);
    expect(margemDaTela(600)).toBe(24);
    expect(margemDaTela(1280)).toBe(24);
  });
});
