import type { SerieCarga } from "@treino/api-client";
import { render, screen } from "@testing-library/react-native";

import { CartaoQuinzena, pontos } from "../src/componentes/CartaoQuinzena";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));

const dia = (i: number, ctl: number, atl: number, aprendendo = false) => ({
  data: `2025-03-${String(7 + i).padStart(2, "0")}`,
  ctl,
  atl,
  tsb: ctl - atl,
  carga: 0,
  atividades: 0,
  calculadas: 0,
  sem_carga: 0,
  aprendendo,
  ctl_texto: `${ctl}`,
  atl_texto: `${atl}`,
});
const serie = (extra: Partial<SerieCarga> = {}): SerieCarga =>
  ({
    atleta_id: 1,
    aviso: null,
    dias: [dia(0, 40, 50), dia(1, 42, 55), dia(2, 44, 58)],
    frase_forma: { tipo: "acima", tendencia: "subiu", texto: "Sua fadiga está acima do seu condicionamento.", versao: "frase_forma@1" },
    periodo: null,
    totais: {} as SerieCarga["totais"],
    versao: "serie_carga@2",
    versao_carga: "carga@2",
    ...extra,
  }) as SerieCarga;

describe("pontos do gráfico", () => {
  it("o maior valor fica no alto e o zero embaixo; eixo compartilhado", () => {
    expect(pontos([0, 100], 100)).toBe("8.0,102.0 292.0,8.0");
    expect(pontos([50], 100)).toBe("150.0,55.0");
    expect(pontos([5, 5], 0)).toBe("8.0,102.0 292.0,102.0");
  });
});

describe("cartão da quinzena", () => {
  it("título, selo de estimativa, duas linhas, valores finais e a frase da API", async () => {
    await render(<CartaoQuinzena serie={serie()} />);
    expect(screen.getByText("Seus últimos 14 dias")).toBeTruthy();
    expect(screen.getByText("estimativa")).toBeTruthy();
    expect(screen.getByText("Condicionamento")).toBeTruthy();
    expect(screen.getByText("Fadiga")).toBeTruthy();
    expect(screen.getByTestId("valor-condicionamento").props.children).toBe("44");
    expect(screen.getByTestId("valor-fadiga").props.children).toBe("58");
    expect(screen.getByTestId("frase-quinzena").props.children).toBe("Sua fadiga está acima do seu condicionamento.");
    expect(screen.queryByText(/CTL|ATL|TSB/)).toBeNull();
  });

  it("aprendendo: sem gráfico, só a frase", async () => {
    await render(<CartaoQuinzena serie={serie({ frase_forma: { tipo: "aprendendo", tendencia: null, texto: "Ainda estamos aprendendo.", versao: "frase_forma@1" } })} />);
    expect(screen.queryByTestId("grafico-quinzena", { includeHiddenElements: true })).toBeNull();
    expect(screen.getByTestId("frase-quinzena").props.children).toBe("Ainda estamos aprendendo.");
  });

  it("sem dias nem frase: texto de reserva", async () => {
    await render(<CartaoQuinzena serie={serie({ dias: [], frase_forma: null })} />);
    expect(screen.getByTestId("frase-quinzena").props.children).toMatch(/aprendendo/);
  });
});
