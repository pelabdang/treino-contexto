// Foco, rolagem e atalho da caixa do dia (revisão da Lia na #427). `focar` e `rolarAte` viram espiões: o Jest não tem DOM de verdade,
// então o que se confere é a ordem e o alvo; o comportamento real no Chromium está nas capturas (`-foco`, `-folha-foco`).
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react-native";

import type { CaixaDoDia } from "../src/caixa/api";
import { TelaCaixaDoDia } from "../src/componentes/TelaCaixaDoDia";
import { caixa } from "../__fixtures__/caixaDoDia";

jest.mock("@expo/vector-icons", () => {
  const { Text } = require("react-native");
  return { MaterialIcons: ({ name, size }: { name: string; size: number }) => <Text>{`${name}:${size}`}</Text> };
});
jest.mock("../src/navegacao/foco", () => ({
  ...jest.requireActual("../src/navegacao/foco"),
  focar: jest.fn(),
  rolarAte: jest.fn(),
}));

jest.setTimeout(20000);

const foco = jest.requireMock("../src/navegacao/foco") as { focar: jest.Mock; rolarAte: jest.Mock };
const resposta = (status: number, corpo: unknown) => ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const copia = (): CaixaDoDia => JSON.parse(JSON.stringify(caixa));
const api = (get: CaixaDoDia = caixa) =>
  jest.fn(async (_u: RequestInfo | URL, init?: RequestInit) =>
    init?.method === "PUT" ? resposta(200, { confirmados: 1, corrigidos: 0 }) : resposta(200, get),
  ) as unknown as typeof fetch;
const aberta = async (f: typeof fetch) => {
  await render(<TelaCaixaDoDia apiUrl="http://api.teste" professorId={7} fetchFn={f} />);
  await screen.findByTestId("resumo");
};

beforeEach(() => {
  foco.focar.mockClear();
  foco.rolarAte.mockClear();
});

describe("foco depois de salvar", () => {
  it("o foco vai ao título 'Treinos novos'", async () => {
    await aberta(api());
    await fireEvent.press(screen.getByTestId("selecionar-511"));
    foco.focar.mockClear();
    await fireEvent.press(screen.getByText("Salvar 1 tipo"));
    await screen.findByTestId("sucesso-lote");
    expect(foco.focar).toHaveBeenCalled();
    expect(foco.focar.mock.calls[foco.focar.mock.calls.length - 1][0]).toBeTruthy();
  });
});

describe("folha de tipo", () => {
  it("leva o foco ao título ao abrir e devolve ao 'Mudar tipo' ao fechar", async () => {
    await aberta(api());
    await fireEvent.press(screen.getByTestId("mudar-tipo-511"));
    await waitFor(() => expect(foco.focar).toHaveBeenCalled());
    await fireEvent.press(screen.getAllByLabelText("Fechar")[1]);
    expect(screen.queryByText("Tipo do treino")).toBeNull();
  });
});

describe("atalho 'Confirmar ou corrigir em Treinos novos'", () => {
  it("só no detalhe de divergência que está em novos; rola e foca a linha", async () => {
    const c = copia();
    c.novos = [{ ...c.novos[0], atividade_id: 502, atleta_id: 2, atleta_nome: "Atleta Fixture Bruno" }, ...c.novos];
    await aberta(api(c));
    await fireEvent.press(screen.getByTestId("treino-501")); // sem divergência: sem atalho
    expect(screen.queryByText("Confirmar ou corrigir em Treinos novos")).toBeNull();
    await fireEvent.press(screen.getByTestId("treino-502"));
    foco.focar.mockClear();
    await fireEvent.press(screen.getByText("Confirmar ou corrigir em Treinos novos"));
    expect(foco.rolarAte).toHaveBeenCalledTimes(1);
    expect(foco.focar).toHaveBeenCalledTimes(1);
    expect(foco.focar.mock.calls[0][0]).toBeTruthy();
    expect(foco.rolarAte.mock.calls[0][1]).toBe(foco.focar.mock.calls[0][0]);
  });

  it("divergência que não está mais em 'Treinos novos' não mostra o atalho", async () => {
    await aberta(api());
    await fireEvent.press(screen.getByTestId("treino-502"));
    expect(screen.queryByText("Confirmar ou corrigir em Treinos novos")).toBeNull();
  });
});

describe("chip do tipo", () => {
  it("fica em cor.superficie quando a linha está selecionada (contraste AA)", async () => {
    await aberta(api());
    const chip = () => within(screen.getByTestId("novo-511")).getByText("Intervalado").parent!;
    const fundo = (n: { props: { style?: unknown } }) =>
      [n.props.style as never].flat(5).filter(Boolean).map((x: { backgroundColor?: string }) => x.backgroundColor).filter(Boolean).pop();
    const antes = fundo(chip());
    await fireEvent.press(screen.getByTestId("selecionar-511"));
    expect(fundo(chip())).toBe("#FFFFFF");
    expect(antes).not.toBe("#FFFFFF");
  });
});
