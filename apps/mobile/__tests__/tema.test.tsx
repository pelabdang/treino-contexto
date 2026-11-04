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
    expect(raio).toEqual({ pequeno: 4, medio: 8, grande: 12, pilula: 999 });
    expect(fonte.corpo).toMatchObject({ fontFamily: "Inter_400Regular", fontSize: 16, lineHeight: 24 });
    expect(fonte["numero-destaque"]).toMatchObject({ fontSize: 40, lineHeight: 44, fontVariant: ["tabular-nums"] });
    expect(fonte.eixo).toMatchObject({ fontSize: 12, fontVariant: ["tabular-nums"] });
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
    expect(screen.getByText("escuro #121517")).toBeTruthy();
  });

  it("usa o claro quando o sistema é claro ou não informa", async () => {
    esquema.mockReturnValue(null);
    await render(<Amostra />);
    expect(screen.getByText("claro #F6F5F1")).toBeTruthy();
  });
});
