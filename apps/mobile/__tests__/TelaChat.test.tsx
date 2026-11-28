import { StyleSheet } from "react-native";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react-native";

import { TelaChat } from "../src/componentes/TelaChat";
import { AVISO_IA, PERGUNTAS_PRONTAS, TEXTO_ERRO_FIXO } from "../src/chat/textos";
import { comLinks, conversa, falha, mensagem, recusaMudanca, recusaTema, reprovada } from "../__fixtures__/chat";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));
jest.setTimeout(20000);

const resposta = (status: number, corpo?: unknown) => ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const treinos = { atleta_id: 1, limite: 1, itens: [{ atividade_id: 107 }], proximo: null };
const limite429 = { detail: "Você fez 20 perguntas na última hora.", espere_texto: "Você pode perguntar de novo em 12 min.", espere_s: 720 };

type Chamada = { metodo: string; url: string; corpo?: { pergunta: string } };
/** API falsa do teste: `responder` decide a resposta de cada POST; o resto é fixo. */
function api(opcoes: { responder?: (c: Chamada) => Promise<Response> | Response; semTreinos?: boolean; conversa?: unknown; conversaStatus?: number } = {}) {
  const chamadas: Chamada[] = [];
  const fetchFn = jest.fn(async (url: string, init?: RequestInit) => {
    const c: Chamada = { metodo: init?.method ?? "GET", url, corpo: init?.body ? JSON.parse(String(init.body)) : undefined };
    chamadas.push(c);
    if (url.includes("/atividades")) return resposta(200, opcoes.semTreinos ? { ...treinos, itens: [] } : treinos);
    if (c.metodo === "GET") return resposta(opcoes.conversaStatus ?? 200, opcoes.conversa ?? conversa());
    return (opcoes.responder ?? (() => resposta(c.url.endsWith("/conversas") ? 201 : 200, c.url.endsWith("/conversas") ? conversa() : mensagem())))(c);
  }) as unknown as typeof fetch;
  return { fetchFn, chamadas, posts: () => chamadas.filter((c) => c.metodo === "POST") };
}

const props = () => ({ aoVoltar: jest.fn(), aoAbrirConversas: jest.fn(), aoAbrirTreino: jest.fn(), aoAbrirEvolucao: jest.fn() });
const tela = (fetchFn: typeof fetch, extra: Record<string, unknown> = {}) => <TelaChat apiUrl="http://api.teste" atletaId={1} fetchFn={fetchFn} {...props()} {...extra} />;
const digitar = (texto: string) => fireEvent.changeText(screen.getByTestId("chat-campo"), texto);

describe("tela do chat: começo", () => {
  it("mostra as 6 perguntas prontas, o aviso do serviço de IA e o cabeçalho", async () => {
    const a = api();
    await render(tela(a.fetchFn));
    expect(await screen.findByText("O que você quer saber sobre os seus treinos?")).toBeTruthy();
    expect(screen.getAllByTestId(/^pergunta-pronta-/)).toHaveLength(6);
    PERGUNTAS_PRONTAS.forEach((q) => expect(screen.getByText(q)).toBeTruthy());
    expect(screen.getByText("Pergunte ao seu treino")).toBeTruthy();
    expect(screen.getByText("Conversas ›")).toBeTruthy();
    expect(screen.getByTestId("chat-aviso-ia").props.children).toBe(AVISO_IA);
  });

  it("atleta sem treinos: sem perguntas prontas, com a frase e o campo ainda ligado", async () => {
    await render(tela(api({ semTreinos: true }).fetchFn));
    expect(await screen.findByTestId("chat-sem-treinos")).toBeTruthy();
    expect(screen.queryByTestId("pergunta-pronta-0")).toBeNull();
    expect(screen.getByTestId("chat-campo").props.editable).toBe(true);
  });

  it("o ↑ fica desligado com o campo vazio e liga ao digitar", async () => {
    await render(tela(api().fetchFn));
    expect(screen.getByTestId("chat-enviar").props.accessibilityState.disabled).toBe(true);
    await digitar("Oi");
    expect(screen.getByTestId("chat-enviar").props.accessibilityState.disabled).toBe(false);
    await digitar("   ");
    expect(screen.getByTestId("chat-enviar").props.accessibilityState.disabled).toBe(true);
  });

  it("o campo para em 1000 caracteres e o contador aparece a partir de 900", async () => {
    await render(tela(api().fetchFn));
    expect(screen.getByTestId("chat-campo").props.maxLength).toBe(1000);
    expect(screen.queryByTestId("chat-contador")).toBeNull();
    await digitar("a".repeat(950));
    expect(screen.getByTestId("chat-contador").props.children).toBe("950 de 1000");
  });

  it("os botões do cabeçalho chamam voltar e conversas", async () => {
    const p = props();
    await render(<TelaChat apiUrl="http://api.teste" atletaId={1} fetchFn={api().fetchFn} {...p} />);
    await fireEvent.press(screen.getByTestId("chat-voltar"));
    await fireEvent.press(screen.getByTestId("chat-conversas"));
    expect(p.aoVoltar).toHaveBeenCalled();
    expect(p.aoAbrirConversas).toHaveBeenCalled();
  });
});

describe("tela do chat: perguntar e responder", () => {
  it("a primeira pergunta cria a conversa; a pergunta pronta é enviada como pergunta comum", async () => {
    const a = api();
    await render(tela(a.fetchFn));
    await fireEvent.press(await screen.findByTestId("pergunta-pronta-0"));
    await screen.findByTestId("chat-resposta");
    expect(a.posts()).toHaveLength(1);
    expect(a.posts()[0]).toMatchObject({ url: "http://api.teste/atletas/1/conversas", corpo: { pergunta: PERGUNTAS_PRONTAS[0] } });
    expect(screen.queryByTestId("chat-comeco")).toBeNull();
    expect(screen.getByText("Nesta semana você correu 3 vezes, 28,4 km no total.")).toBeTruthy();
  });

  it("as seguintes usam enviarMensagem na mesma conversa", async () => {
    const a = api();
    await render(tela(a.fetchFn));
    await digitar("Primeira");
    await fireEvent.press(screen.getByTestId("chat-enviar"));
    await screen.findByTestId("chat-resposta");
    await digitar("Segunda");
    await fireEvent.press(screen.getByTestId("chat-enviar"));
    await waitFor(() => expect(a.posts()).toHaveLength(2));
    expect(a.posts()[1].url).toBe("http://api.teste/atletas/1/conversas/7/mensagens");
    expect(a.posts()[1].corpo).toEqual({ pergunta: "Segunda" });
  });

  it("enquanto pensa: a pergunta já está no histórico, o campo e o ↑ ficam desligados", async () => {
    const a = api({ responder: () => new Promise<Response>(() => {}) });
    await render(tela(a.fetchFn));
    await digitar("Quanto corri?");
    await fireEvent.press(screen.getByTestId("chat-enviar"));
    expect(await screen.findByTestId("chat-pensando")).toBeTruthy();
    expect(screen.getByText("Quanto corri?")).toBeTruthy();
    expect(screen.getByTestId("chat-campo").props.editable).toBe(false);
    expect(screen.getByTestId("chat-enviar").props.accessibilityState.disabled).toBe(true);
    expect(screen.getByTestId("chat-campo").props.value).toBe("");
    expect(screen.getByText("Consultando os seus treinos…")).toBeTruthy();
  });

  it("os links da resposta abrem o treino e a Evolução com a série", async () => {
    const p = props();
    const a = api({ responder: () => resposta(201, conversa({ mensagens: [comLinks] })) });
    await render(<TelaChat apiUrl="http://api.teste" atletaId={1} fetchFn={a.fetchFn} {...p} />);
    await digitar("Como foi minha semana?");
    await fireEvent.press(screen.getByTestId("chat-enviar"));
    await screen.findByTestId("chat-resposta");
    expect(screen.getByText("Abrir na Evolução")).toBeTruthy();
    expect(screen.getByText("Abrir treino · qui 20/03")).toBeTruthy();
    await fireEvent.press(screen.getByTestId("chat-link-0"));
    expect(p.aoAbrirEvolucao).toHaveBeenCalledWith("corrida.volume_km");
    await fireEvent.press(screen.getByTestId("chat-link-1"));
    expect(p.aoAbrirTreino).toHaveBeenCalledWith(107);
    expect(screen.getByText(/Resposta de IA com números do seu histórico/)).toBeTruthy();
  });

  it("a pergunta pronta vinda do Início já é enviada ao abrir (uma vez só)", async () => {
    const a = api();
    await render(tela(a.fetchFn, { perguntaInicial: "Como foi minha semana?" }));
    await screen.findByTestId("chat-resposta");
    expect(a.posts()).toHaveLength(1);
  });
});

describe("tela do chat: estados da API", () => {
  it("recusa não é erro: cartão neutro tracejado, texto da API, sem 'Tentar de novo'", async () => {
    for (const m of [recusaTema, recusaMudanca]) {
      const a = api({ responder: () => resposta(201, conversa({ mensagens: [m] })) });
      const { unmount } = await render(tela(a.fetchFn));
      await digitar("pergunta");
      await fireEvent.press(screen.getByTestId("chat-enviar"));
      const cartao = await screen.findByTestId("chat-recusa");
      expect(within(cartao).getByText(m.texto)).toBeTruthy();
      expect(StyleSheet.flatten(cartao.props.style).borderStyle).toBe("dashed");
      expect(screen.queryByText("Tentar de novo")).toBeNull();
      expect(screen.queryByText(m.motivo as string)).toBeNull();
      await unmount();
    }
  });

  it.each([
    ["erro do provedor", falha],
    ["reprovada", reprovada],
  ])("%s: frase fixa, sem o motivo e com 'Tentar de novo', que reenvia a mesma pergunta", async (_nome, m) => {
    const respostas = [resposta(201, conversa({ mensagens: [{ ...m, pergunta: "Quanto corri?" }] })), resposta(200, mensagem({ pergunta: "Quanto corri?", texto: "Você correu 96,3 km." }))];
    const a = api({ responder: () => respostas.shift() as Response });
    await render(tela(a.fetchFn));
    await digitar("Quanto corri?");
    await fireEvent.press(screen.getByTestId("chat-enviar"));
    const cartao = await screen.findByTestId("chat-erro");
    expect(within(cartao).getByText(TEXTO_ERRO_FIXO)).toBeTruthy();
    expect(screen.queryByText(m.motivo as string)).toBeNull();
    await fireEvent.press(screen.getByTestId("chat-tentar-de-novo"));
    await screen.findByText("Você correu 96,3 km.");
    expect(a.posts()[1]).toMatchObject({ url: "http://api.teste/atletas/1/conversas/7/mensagens", corpo: { pergunta: "Quanto corri?" } });
    // a pergunta que falhou continua no histórico
    expect(screen.getAllByText("Quanto corri?")).toHaveLength(2);
  });

  it("429 com espere_texto: mostra o detail e o espere_texto como vieram, desliga o campo e devolve a pergunta ao campo", async () => {
    const a = api({ responder: () => resposta(429, limite429) });
    await render(tela(a.fetchFn));
    await digitar("Como foi minha semana?");
    await fireEvent.press(screen.getByTestId("chat-enviar"));
    const faixa = await screen.findByTestId("chat-limite");
    expect(within(faixa).getByText("Limite de perguntas")).toBeTruthy();
    expect(within(faixa).getByText("Você fez 20 perguntas na última hora.")).toBeTruthy();
    expect(within(faixa).getByText("Você pode perguntar de novo em 12 min.")).toBeTruthy();
    expect(screen.getByTestId("chat-campo").props.editable).toBe(false);
    expect(screen.getByTestId("chat-campo").props.value).toBe("Como foi minha semana?");
    expect(screen.getByTestId("chat-campo").props.placeholder).toBe("Aguarde para perguntar…");
    expect(screen.getByTestId("chat-enviar").props.accessibilityState.disabled).toBe(true);
  });

  it("429 sem espere_texto: só o detail", async () => {
    const a = api({ responder: () => resposta(429, { detail: limite429.detail, espere_s: 720 }) });
    await render(tela(a.fetchFn));
    await digitar("Oi");
    await fireEvent.press(screen.getByTestId("chat-enviar"));
    const faixa = await screen.findByTestId("chat-limite");
    expect(within(faixa).getByText("Você fez 20 perguntas na última hora.")).toBeTruthy();
    expect(screen.queryByTestId("chat-limite-espere")).toBeNull();
  });

  it("quando o tempo de espere_s acaba, a faixa some e o campo volta sozinho", async () => {
    jest.useFakeTimers();
    try {
      const a = api({ responder: () => resposta(429, { ...limite429, espere_s: 5 }) });
      await render(tela(a.fetchFn));
      await digitar("Oi");
      await act(async () => {
        await fireEvent.press(screen.getByTestId("chat-enviar"));
        await Promise.resolve();
      });
      await screen.findByTestId("chat-limite");
      await act(async () => {
        jest.advanceTimersByTime(5000);
      });
      expect(screen.queryByTestId("chat-limite")).toBeNull();
      expect(screen.getByTestId("chat-campo").props.editable).toBe(true);
    } finally {
      jest.useRealTimers();
    }
  });

  it("sem rede: faixa neutra e a pergunta continua no campo", async () => {
    const a = api({ responder: () => Promise.reject(new Error("x")) });
    await render(tela(a.fetchFn));
    await digitar("Quanto corri?");
    await fireEvent.press(screen.getByTestId("chat-enviar"));
    expect(await screen.findByText("Sem conexão. Verifique a internet e tente de novo.")).toBeTruthy();
    expect(screen.getByTestId("chat-campo").props.value).toBe("Quanto corri?");
    expect(screen.getByTestId("chat-campo").props.editable).toBe(true);
    expect(screen.queryByTestId("chat-pensando")).toBeNull();
  });

  it("erro 500 vira o cartão de erro com a frase fixa", async () => {
    const a = api({ responder: () => resposta(500, { detail: "x" }) });
    await render(tela(a.fetchFn));
    await digitar("Oi");
    await fireEvent.press(screen.getByTestId("chat-enviar"));
    expect(await within(await screen.findByTestId("chat-erro")).findByText(TEXTO_ERRO_FIXO)).toBeTruthy();
  });
});

describe("tela do chat: a espera", () => {
  it("troca o texto aos 10 s e aos 25 s, sem porcentagem", async () => {
    jest.useFakeTimers();
    try {
      const a = api({ responder: () => new Promise<Response>(() => {}) });
      const inicio = jest.fn();
      await render(tela(a.fetchFn, { aoEsperarNoInicio: inicio }));
      await digitar("Oi");
      await act(async () => {
        await fireEvent.press(screen.getByTestId("chat-enviar"));
        await Promise.resolve();
      });
      expect(screen.getByText("Consultando os seus treinos…")).toBeTruthy();
      expect(screen.getByText("Pode levar até 45 segundos.")).toBeTruthy();
      await act(async () => {
        jest.advanceTimersByTime(10000);
      });
      expect(screen.getByText("Ainda consultando. Perguntas sobre vários treinos levam mais tempo.")).toBeTruthy();
      await act(async () => {
        jest.advanceTimersByTime(15000);
      });
      expect(screen.getByText("Está demorando mais que o normal. A resposta pode levar até 45 segundos.")).toBeTruthy();
      expect(screen.queryByText(/%/)).toBeNull();
      await fireEvent.press(screen.getByTestId("chat-esperar-no-inicio"));
      expect(inicio).toHaveBeenCalled();
    } finally {
      jest.useRealTimers();
    }
  });
});

describe("tela do chat: conversa existente", () => {
  it("busca a conversa e mostra o histórico com a hora, o dia e o rótulo de IA", async () => {
    const a = api({ conversa: conversa({ mensagens: [comLinks, mensagem({ id: 2, ordem: 2, pergunta: "E o pace?", texto: "O pace ficou em 5:45." })] }) });
    await render(tela(a.fetchFn, { conversaId: 7, agora: () => new Date(2025, 2, 20, 18, 0, 0) }));
    await screen.findByText("O pace ficou em 5:45.");
    expect(a.chamadas[0].url).toBe("http://api.teste/atletas/1/conversas/7");
    expect(screen.queryByTestId("chat-comeco")).toBeNull();
    expect(screen.getAllByText("hoje")).toHaveLength(1);
    expect(screen.getAllByText("Você · 14:32").length).toBeGreaterThan(0);
  });

  it("404: 'Não encontramos esta conversa.' e o caminho de volta às conversas", async () => {
    const p = props();
    await render(<TelaChat apiUrl="http://api.teste" atletaId={1} fetchFn={api({ conversaStatus: 404, conversa: { detail: "x" } }).fetchFn} conversaId={9} {...p} />);
    expect(await screen.findByText("Não encontramos esta conversa.")).toBeTruthy();
    await fireEvent.press(screen.getByTestId("chat-voltar-conversas"));
    expect(p.aoAbrirConversas).toHaveBeenCalled();
  });

  it("erro ao carregar: 'Tentar de novo' busca outra vez", async () => {
    const respostas = [resposta(500, { detail: "x" }), resposta(200, conversa())];
    const f = jest.fn(async () => respostas.shift() as Response) as unknown as typeof fetch;
    await render(tela(f, { conversaId: 7 }));
    await fireEvent.press(await screen.findByTestId("chat-tentar-carga"));
    await screen.findByText("Nesta semana você correu 3 vezes, 28,4 km no total.");
  });
});

describe("tela do chat: o app não calcula", () => {
  it("o código do chat não usa Math, toFixed, reduce, Intl nem toLocale", () => {
    const fs = require("node:fs");
    for (const arq of ["src/componentes/TelaChat.tsx", "src/componentes/TelaConversas.tsx", "src/componentes/EsperaChat.tsx", "src/componentes/EntradaChat.tsx", "src/chat/hora.ts", "src/chat/textos.ts"]) {
      expect(fs.readFileSync(arq, "utf8")).not.toMatch(/toFixed|Math\.|\.reduce\(|toLocale|Intl\.|mediana\(|parseFloat/);
    }
  });
});
