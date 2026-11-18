import { fireEvent, render, screen, waitFor } from "@testing-library/react-native";

import { TEXTO_VAZIO, TelaConsentimento } from "../src/componentes/TelaConsentimento";
import { TelaTermo } from "../src/componentes/TelaTermo";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));

const resposta = (status: number, corpo?: unknown) => ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const vinc = (id: number, nome: string, ativo: boolean, extra = {}) => ({
  professor_id: id,
  nome,
  consentimento: ativo,
  termo_versao: ativo ? "termo@1" : null,
  consentimento_em: ativo ? "2026-11-10T12:00:00Z" : null,
  consentimento_revogado_em: null,
  termo_desatualizado: false,
  ...extra,
});
const LISTA = { atleta_id: 1, termo_vigente: "termo@1", professores: [vinc(12, "Marina Exemplo", true), vinc(11, "Carlos Exemplo", false)] };
const TERMO = { versao: "termo@1", provisorio: true, texto: "Texto sintético do termo.\nSegundo parágrafo sintético." };

type Rota = (init?: RequestInit) => Response | Promise<Response>;
const servidor = (rotas: Record<string, Rota>) =>
  jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const chave = `${init?.method ?? "GET"} ${String(input).replace("http://api.teste", "")}`;
    const r = rotas[chave];
    if (!r) throw new Error(`sem rota ${chave}`);
    return r(init);
  }) as unknown as jest.Mock & typeof fetch;

const lista = (f: typeof fetch, extra = {}) => <TelaConsentimento apiUrl="http://api.teste" atletaId={1} fetchFn={f} aoAbrirTermo={jest.fn()} {...extra} />;

describe("lista de consentimentos", () => {
  it("mostra aguardando primeiro, com ícone e palavra, e o botão certo em cada cartão", async () => {
    await render(lista(servidor({ "GET /atletas/1/professores": () => resposta(200, LISTA) })));
    await screen.findByTestId("professor-11");
    const ordem = screen.getAllByText(/Exemplo/).map((n) => n.props.children);
    expect(ordem).toEqual(["Carlos Exemplo", "Marina Exemplo"]);
    expect(screen.getByText("Aguardando você")).toBeTruthy();
    expect(screen.getByText("Consentido em 10/11/26")).toBeTruthy();
    expect(screen.getByText("[hourglass-empty]", { includeHiddenElements: true })).toBeTruthy();
    expect(screen.getByText("[check-circle-outline]", { includeHiddenElements: true })).toBeTruthy();
    expect(screen.getByTestId("dar-11")).toBeTruthy();
    expect(screen.getByTestId("retirar-12")).toBeTruthy();
    expect(screen.getByTestId("professor-11").props.accessibilityLabel).toBe("Carlos Exemplo, aguardando você");
  });

  it("termo desatualizado volta a 'Aguardando você' com a explicação", async () => {
    const l = { ...LISTA, professores: [vinc(13, "Paulo Exemplo", false, { termo_desatualizado: true, termo_versao: "antigo" })] };
    await render(lista(servidor({ "GET /atletas/1/professores": () => resposta(200, l) })));
    expect(await screen.findByText(/O termo mudou. Leia e dê o consentimento de novo/)).toBeTruthy();
  });

  it("'Ler e dar consentimento' abre o termo do professor", async () => {
    const aoAbrirTermo = jest.fn();
    await render(lista(servidor({ "GET /atletas/1/professores": () => resposta(200, LISTA) }), { aoAbrirTermo }));
    await fireEvent.press(await screen.findByTestId("dar-11"));
    expect(aoAbrirTermo).toHaveBeenCalledWith(11);
  });

  it("vazio, erro de rede e outro erro têm as frases da spec", async () => {
    await render(lista(servidor({ "GET /atletas/1/professores": () => resposta(200, { ...LISTA, professores: [] }) })));
    expect(await screen.findByText(TEXTO_VAZIO)).toBeTruthy();
    const rede = jest.fn(async () => {
      throw new Error("x");
    }) as unknown as typeof fetch;
    await render(lista(rede));
    expect(await screen.findByText("Não foi possível falar com o servidor")).toBeTruthy();
    await render(lista(servidor({ "GET /atletas/1/professores": () => resposta(500, {}) })));
    expect(await screen.findByText("Não foi possível carregar. Tente de novo mais tarde.")).toBeTruthy();
  });

  it("retirar: o diálogo pergunta, 'Cancelar' não chama a API, 'Retirar' chama e recarrega", async () => {
    let apos = false;
    const f = servidor({
      "GET /atletas/1/professores": () => resposta(200, apos ? { ...LISTA, professores: [vinc(12, "Marina Exemplo", false), vinc(11, "Carlos Exemplo", false)] } : LISTA),
      "DELETE /atletas/1/professores/12/consentimento": () => {
        apos = true;
        return resposta(204);
      },
    });
    await render(lista(f));
    await fireEvent.press(await screen.findByTestId("retirar-12"));
    expect(screen.getByText("Retirar o consentimento?")).toBeTruthy();
    expect(screen.getByText(/Marina Exemplo deixa de ver os seus treinos a partir de agora/)).toBeTruthy();
    await fireEvent.press(screen.getByTestId("cancelar-retirar"));
    expect(f.mock.calls.some((c) => c[1]?.method === "DELETE")).toBe(false);
    await fireEvent.press(screen.getByTestId("retirar-12"));
    await fireEvent.press(screen.getByTestId("confirmar-retirar"));
    await waitFor(() => expect(screen.getAllByText("Aguardando você")).toHaveLength(2));
    expect(screen.queryByTestId("retirar-12")).toBeNull();
  });

  it("retirar com erro de rede mantém o estado e avisa", async () => {
    const f = servidor({
      "GET /atletas/1/professores": () => resposta(200, LISTA),
      "DELETE /atletas/1/professores/12/consentimento": () => {
        throw new Error("rede");
      },
    });
    await render(lista(f));
    await fireEvent.press(await screen.findByTestId("retirar-12"));
    await fireEvent.press(screen.getByTestId("confirmar-retirar"));
    expect(await screen.findByText("Não foi possível retirar. Tente de novo.")).toBeTruthy();
    expect(screen.getByTestId("retirar-12")).toBeTruthy();
  });

  it("veio do termo porque o pedido não existe mais: faixa com a frase", async () => {
    await render(lista(servidor({ "GET /atletas/1/professores": () => resposta(200, LISTA) }), { avisoInexistente: true }));
    expect(await screen.findByText("Este pedido não existe mais.")).toBeTruthy();
  });
});

describe("tela do termo", () => {
  const termo = (f: typeof fetch, extra = {}) => (
    <TelaTermo apiUrl="http://api.teste" atletaId={1} professorId={11} fetchFn={f} aoVoltar={jest.fn()} aoConcluir={jest.fn()} aoInexistente={jest.fn()} {...extra} />
  );
  const rotasBase = { "GET /termo-de-consentimento": () => resposta(200, TERMO), "GET /atletas/1/professores": () => resposta(200, LISTA) };

  it("mostra o termo da API, a faixa provisória e o botão desligado até marcar 'Li e concordo' (não vem marcado)", async () => {
    await render(termo(servidor(rotasBase)));
    expect(await screen.findByText("Texto sintético do termo.")).toBeTruthy();
    expect(screen.getByText("Segundo parágrafo sintético.")).toBeTruthy(); // cada linha vira um parágrafo
    expect(screen.getByText(/Você está dando permissão a:/)).toBeTruthy();
    expect(screen.getByText("Carlos Exemplo")).toBeTruthy();
    expect(screen.getByTestId("faixa-provisorio")).toBeTruthy();
    expect(screen.getByText(/Ainda não foi revisto por quem entende de lei e vale só para o piloto/)).toBeTruthy();
    expect(screen.getByText("Texto provisório")).toBeTruthy();
    const caixa = screen.getByTestId("li-e-concordo");
    expect(caixa.props.accessibilityState.checked).toBe(false);
    expect(screen.getByTestId("dar-consentimento").props.accessibilityState.disabled).toBe(true);
    await fireEvent.press(caixa);
    expect(screen.getByTestId("li-e-concordo").props.accessibilityState.checked).toBe(true);
    expect(screen.getByTestId("dar-consentimento").props.accessibilityState.disabled).toBe(false);
  });

  it("a faixa some quando a API diz que o termo não é mais provisório", async () => {
    await render(termo(servidor({ ...rotasBase, "GET /termo-de-consentimento": () => resposta(200, { ...TERMO, provisorio: false }) })));
    await screen.findByText("Texto sintético do termo.");
    expect(screen.queryByTestId("faixa-provisorio")).toBeNull();
  });

  it("dar consentimento envia a versão lida e conclui", async () => {
    const aoConcluir = jest.fn();
    const f = servidor({ ...rotasBase, "PUT /atletas/1/professores/11/consentimento": () => resposta(200, vinc(11, "Carlos Exemplo", true)) });
    await render(termo(f, { aoConcluir }));
    await fireEvent.press(await screen.findByTestId("li-e-concordo"));
    await fireEvent.press(screen.getByTestId("dar-consentimento"));
    await waitFor(() => expect(aoConcluir).toHaveBeenCalled());
    const put = f.mock.calls.find((c) => c[1]?.method === "PUT");
    expect(JSON.parse(String(put?.[1]?.body))).toEqual({ termo_versao: "termo@1" });
  });

  it("sem rede ao salvar: avisa e a caixa continua marcada", async () => {
    const f = servidor({
      ...rotasBase,
      "PUT /atletas/1/professores/11/consentimento": () => {
        throw new Error("rede");
      },
    });
    await render(termo(f));
    await fireEvent.press(await screen.findByTestId("li-e-concordo"));
    await fireEvent.press(screen.getByTestId("dar-consentimento"));
    expect(await screen.findByText("Não foi possível salvar. Tente de novo.")).toBeTruthy();
    expect(screen.getByTestId("li-e-concordo").props.accessibilityState.checked).toBe(true);
  });

  it("409: o termo mudou, recarrega e desmarca a caixa", async () => {
    let versao = "termo@1";
    const f = servidor({
      "GET /termo-de-consentimento": () => resposta(200, { ...TERMO, versao }),
      "GET /atletas/1/professores": () => resposta(200, LISTA),
      "PUT /atletas/1/professores/11/consentimento": () => {
        versao = "termo@2";
        return resposta(409, { detail: "o termo mudou" });
      },
    });
    await render(termo(f));
    await fireEvent.press(await screen.findByTestId("li-e-concordo"));
    await fireEvent.press(screen.getByTestId("dar-consentimento"));
    expect(await screen.findByText("O texto do termo mudou. Leia de novo antes de dar o consentimento.")).toBeTruthy();
    await waitFor(() => expect(screen.getByTestId("li-e-concordo").props.accessibilityState.checked).toBe(false));
  });

  it("404 ao salvar ou professor fora da lista: volta com o aviso", async () => {
    const aoInexistente = jest.fn();
    await render(termo(servidor({ ...rotasBase, "GET /atletas/1/professores": () => resposta(200, { ...LISTA, professores: [] }) }), { aoInexistente }));
    await waitFor(() => expect(aoInexistente).toHaveBeenCalled());
  });

  it("erro ao carregar o termo: frase e 'Tentar de novo'", async () => {
    await render(termo(servidor({ ...rotasBase, "GET /termo-de-consentimento": () => resposta(500, {}) })));
    expect(await screen.findByText("Não foi possível carregar o termo. Tente de novo.")).toBeTruthy();
    expect(screen.getByTestId("tentar-de-novo")).toBeTruthy();
  });
});
