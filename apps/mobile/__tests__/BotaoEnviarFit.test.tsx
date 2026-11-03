import type { EvolucaoTiros1km } from "@treino/api-client";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import * as DocumentPicker from "expo-document-picker";

import exemplo from "../../../packages/api-client/exemplos/evolucao-tiros-1km.json";
import { TelaEvolucao } from "../src/componentes/TelaEvolucao";

jest.mock("expo-document-picker", () => ({ getDocumentAsync: jest.fn() }));
const escolher = DocumentPicker.getDocumentAsync as jest.Mock;

const evolucao = exemplo as unknown as EvolucaoTiros1km;
const resposta = (status: number, corpo: unknown) =>
  ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const ok = { resultado: "inserida", atividade_id: 7, avisos: [] };

/** fetch falso: GET devolve a evolução; POST devolve `post` (ou rejeita). */
function fetchFalso(post: () => Promise<Response>) {
  return jest.fn(async (url: string, init?: RequestInit) =>
    init?.method === "POST" ? post() : resposta(200, evolucao),
  ) as unknown as typeof fetch & jest.Mock;
}
const gets = (f: jest.Mock) => f.mock.calls.filter((c) => c[1]?.method !== "POST").length;

async function abrir(f: typeof fetch) {
  await render(<TelaEvolucao apiUrl="http://api.teste" atletaId={1} fetchFn={f} />);
  await screen.findByTestId("lista-sessoes");
}
const clicar = async () => {
  await fireEvent.press(screen.getByText("Enviar arquivo FIT"));
};

beforeEach(() => {
  escolher.mockReset();
  escolher.mockResolvedValue({
    canceled: false,
    assets: [{ uri: "file:///tmp/upload_intervalado_5x1km.fit", name: "upload_intervalado_5x1km.fit", mimeType: "application/octet-stream" }],
  });
});

describe("botão Enviar arquivo FIT", () => {
  it("201: mostra enviando, depois 'Atividade adicionada' e busca a evolução de novo", async () => {
    let liberar!: (r: Response) => void;
    const f = fetchFalso(() => new Promise<Response>((res) => (liberar = res)));
    await abrir(f);
    expect(gets(f)).toBe(1);
    void clicar(); // não espera: o envio fica pendente de propósito
    expect(await screen.findByText("Enviando...")).toBeTruthy();
    await act(async () => liberar(resposta(201, ok)));
    expect(await screen.findByText("Atividade adicionada")).toBeTruthy();
    await waitFor(() => expect(gets(f)).toBe(2));
    const post = f.mock.calls.find((c) => c[1]?.method === "POST");
    expect(post[0]).toBe("http://api.teste/atletas/1/atividades/fit");
  });

  it("200: 'Essa atividade já estava aqui'", async () => {
    await abrir(fetchFalso(async () => resposta(200, { ...ok, resultado: "ignorada" })));
    await clicar();
    expect(await screen.findByText("Essa atividade já estava aqui")).toBeTruthy();
  });

  it("400: mostra o detail da API e não busca de novo", async () => {
    const f = fetchFalso(async () => resposta(400, { detail: "Arquivo FIT inválido" }));
    await abrir(f);
    await clicar();
    expect(await screen.findByText("Arquivo FIT inválido")).toBeTruthy();
    expect(gets(f)).toBe(1);
  });

  it("413: mostra o detail da API", async () => {
    await abrir(fetchFalso(async () => resposta(413, { detail: "Arquivo maior que 10 MB" })));
    await clicar();
    expect(await screen.findByText("Arquivo maior que 10 MB")).toBeTruthy();
  });

  it("rede: mensagem de falha de conexão", async () => {
    await abrir(fetchFalso(() => Promise.reject(new Error("Network request failed"))));
    await clicar();
    expect(await screen.findByText(/Não foi possível falar com o servidor/)).toBeTruthy();
  });

  it("cancelar o seletor não envia nada", async () => {
    escolher.mockResolvedValue({ canceled: true, assets: null });
    const f = fetchFalso(async () => resposta(201, ok));
    await abrir(f);
    await clicar();
    await waitFor(() => expect(escolher).toHaveBeenCalled());
    expect(f.mock.calls.some((c) => c[1]?.method === "POST")).toBe(false);
    expect(screen.queryByText("Enviando...")).toBeNull();
  });
});
