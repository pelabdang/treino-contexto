// Ajustes da revisão da Lia na caixa rodando (#452): espaço medido da barra, fundo da folha e texto do feedback pendente.
import { fireEvent, render, screen, within } from "@testing-library/react-native";

import type { CaixaDoDia } from "../src/caixa/api";
import { TelaCaixaDoDia } from "../src/componentes/TelaCaixaDoDia";
import { caixa } from "../__fixtures__/caixaDoDia";

jest.mock("@expo/vector-icons", () => {
  const { Text } = require("react-native");
  return { MaterialIcons: ({ name, size }: { name: string; size: number }) => <Text>{`${name}:${size}`}</Text> };
});

jest.setTimeout(20000);

const resposta = (status: number, corpo: unknown) => ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const copia = (): CaixaDoDia => JSON.parse(JSON.stringify(caixa));
const api = (get: CaixaDoDia = caixa, put: () => Response = () => resposta(200, { confirmados: 1, corrigidos: 0 })) =>
  jest.fn(async (_u: RequestInfo | URL, init?: RequestInit) => (init?.method === "PUT" ? put() : resposta(200, get))) as unknown as typeof fetch;
const aberta = async (f: typeof fetch) => {
  await render(<TelaCaixaDoDia apiUrl="http://api.teste" professorId={7} fetchFn={f} />);
  await screen.findByTestId("resumo");
};
const espacoFinal = () => {
  const estilo = [screen.getByTestId("rolagem-tela").props.contentContainerStyle].flat(5).filter(Boolean);
  return estilo.reduce((a: number | undefined, x: { paddingBottom?: number }) => x.paddingBottom ?? a, undefined) as number | undefined;
};
const medir = (altura: number) => fireEvent(screen.getByTestId("barra-lote"), "layout", { nativeEvent: { layout: { x: 0, y: 0, width: 390, height: altura } } });

describe("espaço no fim da lista = altura medida da barra + espaco.4", () => {
  it("usa a altura medida (e não um valor fixo)", async () => {
    await aberta(api());
    await fireEvent.press(screen.getByTestId("selecionar-511"));
    await medir(171);
    expect(espacoFinal()).toBe(171 + 16);
  });

  it("acompanha a barra quando ela cresce com o aviso de erro e quando encolhe", async () => {
    const f = api(caixa, () => resposta(404, { detail: [{ type: "atividade_nao_encontrada" }] }));
    await aberta(f);
    await fireEvent.press(screen.getByTestId("selecionar-511"));
    await medir(140);
    expect(espacoFinal()).toBe(156);
    await fireEvent.press(screen.getByText("Salvar 1 tipo"));
    await screen.findByTestId("erro-lote");
    await medir(236);
    expect(espacoFinal()).toBe(252);
    await medir(140);
    expect(espacoFinal()).toBe(156);
  });

  it("sem barra, não reserva espaço extra", async () => {
    await aberta(api());
    expect(espacoFinal()).toBeUndefined();
  });
});

describe("fundo da folha de tipo", () => {
  it("fica fora da ordem de foco e da árvore de acessibilidade; só o botão 'Fechar' tem esse rótulo", async () => {
    await aberta(api());
    await fireEvent.press(screen.getByTestId("mudar-tipo-511"));
    const fundo = screen.getByTestId("fundo-folha", { includeHiddenElements: true });
    expect(fundo.props.accessible).toBe(false);
    expect(fundo.props.focusable).toBe(false);
    expect(fundo.props["aria-hidden"]).toBe(true);
    expect(fundo.props.importantForAccessibility).toBe("no");
    expect(fundo.props.accessibilityLabel).toBeUndefined();
    expect(screen.getAllByLabelText("Fechar")).toHaveLength(1);
  });

  it("tocar no fundo e o botão 'Fechar' continuam fechando; a folha não fica dentro do fundo oculto", async () => {
    await aberta(api());
    await fireEvent.press(screen.getByTestId("mudar-tipo-511"));
    await fireEvent.press(screen.getByTestId("fundo-folha", { includeHiddenElements: true }));
    expect(screen.queryByText("Tipo do treino")).toBeNull();
    await fireEvent.press(screen.getByTestId("mudar-tipo-511"));
    expect(screen.getByText("Tipo do treino")).toBeTruthy();
    await fireEvent.press(screen.getByLabelText("Fechar"));
    expect(screen.queryByText("Tipo do treino")).toBeNull();
  });
});

describe("feedback pendente na caixa", () => {
  it("diz 'O feedback ainda não está pronto.' e não manda tocar em Atualizar", async () => {
    const c = copia();
    c.alunos[0].treinos[0].detalhe.feedback = {
      estado: "pendente",
      mensagem: "O feedback deste treino ainda não foi gerado. Toque em Atualizar para ver se já está pronto.",
    };
    await aberta(api(c));
    await fireEvent.press(screen.getByTestId("treino-501"));
    const d = screen.getByTestId("detalhe-501");
    expect(within(d).getByText("O feedback ainda não está pronto.")).toBeTruthy();
    expect(screen.queryByText(/Toque em Atualizar/)).toBeNull();
  });

  it("os outros estados seguem a mensagem da API", async () => {
    await aberta(api());
    await fireEvent.press(screen.getByTestId("treino-503"));
    expect(within(screen.getByTestId("detalhe-503")).getByText("O prazo do check-in deste treino acabou.")).toBeTruthy();
  });
});
