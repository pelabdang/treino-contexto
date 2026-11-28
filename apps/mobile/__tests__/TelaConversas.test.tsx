import { fireEvent, render, screen, waitFor, within } from "@testing-library/react-native";

import { TelaConversas } from "../src/componentes/TelaConversas";
import { RODAPE_LISTA, TEXTO_APAGADA, TEXTO_APAGAR, TEXTO_APAGAR_ERRO } from "../src/chat/textos";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));
jest.setTimeout(20000);

const resposta = (status: number, corpo?: unknown) => ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const resumo = (id: number, titulo: string, atualizada_em: string) => ({ id, titulo, criada_em: atualizada_em, atualizada_em });
const lista = { atleta_id: 1, conversas: [resumo(3, "Como foi minha semana?", "2025-03-20T14:32:00-03:00"), resumo(2, "Quanto corri neste mês?", "2025-03-19T20:10:00-03:00"), resumo(1, "Meu pace melhorou?", "2025-03-12T07:45:00-03:00")] };
const agora = () => new Date(2025, 2, 20, 18, 0, 0);

function api(extra: { apagar?: number; lista?: Response } = {}) {
  const chamadas: { metodo: string; url: string }[] = [];
  const fetchFn = jest.fn(async (url: string, init?: RequestInit) => {
    const metodo = init?.method ?? "GET";
    chamadas.push({ metodo, url });
    if (metodo === "DELETE") return resposta(extra.apagar ?? 204);
    return extra.lista ?? resposta(200, lista);
  }) as unknown as typeof fetch;
  return { fetchFn, chamadas };
}
const tela = (fetchFn: typeof fetch, p = { aoVoltar: jest.fn(), aoAbrirConversa: jest.fn(), aoNovaConversa: jest.fn() }) => (
  <TelaConversas apiUrl="http://api.teste" atletaId={1} fetchFn={fetchFn} agora={agora} {...p} />
);

describe("lista de conversas", () => {
  it("mostra título e data de cada conversa, o botão de nova conversa e o rodapé fixo", async () => {
    await render(tela(api().fetchFn));
    expect(await screen.findByText("Como foi minha semana?")).toBeTruthy();
    expect(screen.getByText("hoje, 14:32")).toBeTruthy();
    expect(screen.getByText("ontem, 20:10")).toBeTruthy();
    expect(screen.getByText("qua 12/03, 07:45")).toBeTruthy();
    expect(screen.getByText("Nova conversa")).toBeTruthy();
    expect(screen.getByText(RODAPE_LISTA)).toBeTruthy();
  });

  it("tocar numa linha abre a conversa; 'Nova conversa' abre uma nova", async () => {
    const p = { aoVoltar: jest.fn(), aoAbrirConversa: jest.fn(), aoNovaConversa: jest.fn() };
    await render(tela(api().fetchFn, p));
    await fireEvent.press(await screen.findByTestId("conversa-2"));
    expect(p.aoAbrirConversa).toHaveBeenCalledWith(2);
    await fireEvent.press(screen.getByTestId("nova-conversa"));
    expect(p.aoNovaConversa).toHaveBeenCalled();
    await fireEvent.press(screen.getByTestId("conversas-voltar"));
    expect(p.aoVoltar).toHaveBeenCalled();
  });

  it("lista vazia: frase e botão", async () => {
    await render(tela(api({ lista: resposta(200, { atleta_id: 1, conversas: [] }) }).fetchFn));
    expect(await screen.findByText("Nenhuma conversa ainda. Faça a sua primeira pergunta.")).toBeTruthy();
    expect(screen.getByTestId("nova-conversa")).toBeTruthy();
  });

  it("erro ao carregar: frase e 'Tentar de novo'", async () => {
    const respostas = [resposta(500, {}), resposta(200, lista)];
    const f = jest.fn(async () => respostas.shift() as Response) as unknown as typeof fetch;
    await render(tela(f));
    expect(await screen.findByText("Não deu para carregar as conversas.")).toBeTruthy();
    await fireEvent.press(screen.getByTestId("conversas-tentar"));
    expect(await screen.findByText("Meu pace melhorou?")).toBeTruthy();
  });

  it("apagar: '⋯' abre o menu, o diálogo explica e confirma; a conversa sai da lista com aviso", async () => {
    const a = api();
    await render(tela(a.fetchFn));
    await fireEvent.press(await screen.findByTestId("mais-2"));
    await fireEvent.press(screen.getByTestId("apagar-2"));
    const dialogo = screen.getByTestId("dialogo-apagar");
    expect(within(dialogo).getByText("Apagar esta conversa?")).toBeTruthy();
    expect(within(dialogo).getByText(TEXTO_APAGAR)).toBeTruthy();
    await fireEvent.press(screen.getByTestId("confirmar-apagar"));
    await waitFor(() => expect(screen.queryByTestId("conversa-2")).toBeNull());
    expect(a.chamadas.find((c) => c.metodo === "DELETE")?.url).toBe("http://api.teste/atletas/1/conversas/2");
    expect(screen.getByText(TEXTO_APAGADA)).toBeTruthy();
  });

  it("cancelar não apaga nada", async () => {
    const a = api();
    await render(tela(a.fetchFn));
    await fireEvent.press(await screen.findByTestId("mais-2"));
    await fireEvent.press(screen.getByTestId("apagar-2"));
    await fireEvent.press(screen.getByTestId("cancelar-apagar"));
    expect(a.chamadas.some((c) => c.metodo === "DELETE")).toBe(false);
    expect(screen.getByTestId("conversa-2")).toBeTruthy();
  });

  it("erro ao apagar: aviso e a conversa continua", async () => {
    await render(tela(api({ apagar: 500 }).fetchFn));
    await fireEvent.press(await screen.findByTestId("mais-2"));
    await fireEvent.press(screen.getByTestId("apagar-2"));
    await fireEvent.press(screen.getByTestId("confirmar-apagar"));
    expect(await screen.findByText(TEXTO_APAGAR_ERRO)).toBeTruthy();
    expect(screen.getByTestId("conversa-2")).toBeTruthy();
  });
});
