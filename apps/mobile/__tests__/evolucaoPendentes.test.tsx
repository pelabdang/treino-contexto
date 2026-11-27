import { fireEvent, render, screen } from "@testing-library/react-native";

import { fetchEvolucao } from "../__fixtures__/evolucao";
import { TelaEvolucao } from "../src/componentes/TelaEvolucao";
import { pendentes } from "../__fixtures__/checkin";

jest.mock("@expo/vector-icons", () => {
  const { Text } = require("react-native");
  return { MaterialIcons: ({ name, size }: { name: string; size: number }) => <Text>{`${name}:${size}`}</Text> };
});

jest.setTimeout(20000);

const resposta = (status: number, corpo: unknown) =>
  ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;

/** Evolução e pendentes no mesmo `fetch` falso; `pendentesFalha` derruba só a chamada dos pendentes. */
function servidor(opcoes: { pendentesFalha?: boolean; total?: number } = {}) {
  const evolucao = fetchEvolucao();
  return jest.fn(async (url: unknown) => {
    if (String(url).includes("/checkins/pendentes")) {
      if (opcoes.pendentesFalha) throw new Error("x");
      return resposta(200, { ...pendentes, total: opcoes.total ?? pendentes.total });
    }
    return evolucao(url as string);
  }) as unknown as typeof fetch & jest.Mock;
}

const tela = (f: typeof fetch, extra = {}) => (
  <TelaEvolucao apiUrl="http://api.teste" atletaId={1} fetchFn={f} aoAbrirCheckinsPendentes={jest.fn()} {...extra} />
);

describe("entrada 'Check-ins pendentes' na evolução", () => {
  it("busca o total ao abrir e mostra '· 2'", async () => {
    const f = servidor();
    await render(tela(f));
    const linha = await screen.findByTestId("abrir-checkins-pendentes");
    await screen.findByText("Check-ins pendentes · 2");
    expect(linha.props.accessibilityLabel).toBe("Check-ins pendentes, 2");
    expect(f.mock.calls.map((c) => String(c[0]))).toContain("http://api.teste/atletas/1/checkins/pendentes");
  });

  it("sem pendentes (total 0) a linha aparece sem número", async () => {
    await render(tela(servidor({ total: 0 })));
    await screen.findByTestId("frase-evolucao");
    expect(screen.getByText("Check-ins pendentes")).toBeTruthy();
  });

  it("se a busca falhar, a linha aparece sem número e a evolução segue normal", async () => {
    await render(tela(servidor({ pendentesFalha: true })));
    await screen.findByTestId("frase-evolucao");
    expect(screen.getByText("Check-ins pendentes")).toBeTruthy();
  });

  it("tem ícone assignment e chevron-right; tocar chama o callback", async () => {
    const abrir = jest.fn();
    await render(tela(servidor(), { aoAbrirCheckinsPendentes: abrir }));
    const linha = await screen.findByTestId("abrir-checkins-pendentes");
    expect(screen.getByText("assignment:20")).toBeTruthy();
    await fireEvent.press(linha);
    expect(abrir).toHaveBeenCalled();
  });

  it("sem o callback, a linha não aparece e a API de pendentes nem é chamada", async () => {
    const f = servidor();
    await render(<TelaEvolucao apiUrl="http://api.teste" atletaId={1} fetchFn={f} />);
    await screen.findByTestId("frase-evolucao");
    expect(screen.queryByTestId("abrir-checkins-pendentes")).toBeNull();
    expect(f.mock.calls.some((c) => String(c[0]).includes("pendentes"))).toBe(false);
  });

  it("a linha não mostra nada do check-in", async () => {
    await render(tela(servidor()));
    await screen.findByText("Check-ins pendentes · 2");
    expect(screen.queryByText(/PSE|Sensação|Observação/)).toBeNull();
  });
});
