import { fireEvent, render, screen, waitFor, within } from "@testing-library/react-native";
import type { Atividade, FeedbackTreino } from "@treino/api-client";
import { AccessibilityInfo, Platform } from "react-native";

import { CartaoFeedback, ORIGEM_AUTOMATICO, ORIGEM_TESTE } from "../src/componentes/CartaoFeedback";
import { TelaTreino } from "../src/componentes/TelaTreino";
import { coresClaro, coresEscuro } from "../src/tema/tokens";
import { atividadesCheckin } from "../__fixtures__/checkin";

jest.mock("@expo/vector-icons", () => {
  const { Text } = require("react-native");
  return { MaterialIcons: ({ name, size }: { name: string; size: number }) => <Text>{`${name}:${size}`}</Text> };
});

jest.setTimeout(20000);

// Só texto marcador sintético (o feedback é dado de saúde derivado).
const TEXTO = "Texto de exemplo do feedback.\nSegunda linha do texto de exemplo.";
const pronto: FeedbackTreino = { estado: "pronto", texto: TEXTO, origem: "automatico" };

describe("cartão Feedback: um teste por estado", () => {
  it("pronto: mostra o texto como veio, o título e a origem automática; sem selo, sem botões", async () => {
    await render(<CartaoFeedback feedback={pronto} aoFazerCheckin={jest.fn()} aoAtualizar={jest.fn()} />);
    const cartao = screen.getByTestId("cartao-feedback");
    expect(cartao.props.accessibilityLabel).toBe("Feedback do treino");
    expect(within(cartao).getByRole("header")).toHaveTextContent("Feedback");
    expect(screen.getByTestId("feedback-texto")).toHaveTextContent(TEXTO);
    expect(screen.getByTestId("feedback-texto").props.selectable).toBe(true);
    expect(screen.getByTestId("feedback-origem")).toHaveTextContent(ORIGEM_AUTOMATICO);
    expect(screen.queryByTestId("selo-teste")).toBeNull();
    expect(screen.queryByText("Atualizar")).toBeNull();
    expect(screen.queryByText("Fazer check-in")).toBeNull();
  });

  it("pronto de teste: selo 'Texto de teste' e a origem trocada", async () => {
    await render(<CartaoFeedback feedback={{ ...pronto, origem: "teste" }} />);
    expect(screen.getByTestId("selo-teste")).toHaveTextContent("Texto de teste");
    expect(screen.getByTestId("feedback-origem")).toHaveTextContent(ORIGEM_TESTE);
    expect(screen.queryByText(ORIGEM_AUTOMATICO)).toBeNull();
  });

  it("sem check-in com prazo aberto: ícone assignment, a mensagem da API e 'Fazer check-in' (secundário, com rótulo próprio)", async () => {
    const fazer = jest.fn();
    await render(
      <CartaoFeedback feedback={{ estado: "sem_checkin", mensagem: "Mensagem da API.", checkin_aberto: true }} aoFazerCheckin={fazer} />,
    );
    expect(screen.getByTestId("feedback-mensagem")).toHaveTextContent("Mensagem da API.");
    expect(screen.getByText("assignment:20")).toBeTruthy();
    const botao = screen.getByTestId("feedback-fazer-checkin");
    expect(botao.props.accessibilityLabel).toBe("Fazer check-in para ver o feedback");
    await fireEvent.press(botao);
    expect(fazer).toHaveBeenCalledTimes(1);
  });

  it("sem check-in com prazo vencido: info-outline e a frase, sem botão", async () => {
    await render(
      <CartaoFeedback feedback={{ estado: "sem_checkin", checkin_aberto: false }} aoFazerCheckin={jest.fn()} />,
    );
    expect(screen.getByTestId("feedback-mensagem")).toHaveTextContent("O prazo do check-in deste treino acabou, então ele fica sem feedback.");
    expect(screen.getByText("info-outline:20")).toBeTruthy();
    expect(screen.queryByTestId("feedback-fazer-checkin")).toBeNull();
  });

  it("sem check-in sem a mensagem: usa a frase de reserva da spec", async () => {
    await render(<CartaoFeedback feedback={{ estado: "sem_checkin", checkin_aberto: true }} aoFazerCheckin={jest.fn()} />);
    expect(screen.getByTestId("feedback-mensagem")).toHaveTextContent("Faça o check-in para ver o feedback.");
  });

  it.each([
    ["pendente", "O feedback deste treino ainda não foi gerado. Toque em Atualizar para ver se já está pronto."],
    ["desatualizado", "Você editou o check-in. O feedback será refeito."],
  ] as const)("%s: info-outline, a mensagem (reserva se faltar) e 'Atualizar'", async (estado, reserva) => {
    const atualizar = jest.fn(async () => pronto);
    await render(<CartaoFeedback feedback={{ estado }} aoAtualizar={atualizar} />);
    expect(screen.getByTestId("feedback-mensagem")).toHaveTextContent(reserva);
    expect(screen.getByText("info-outline:20")).toBeTruthy();
    expect(screen.getByText("refresh:20")).toBeTruthy();
    await fireEvent.press(screen.getByTestId("feedback-atualizar"));
    await waitFor(() => expect(atualizar).toHaveBeenCalledTimes(1));
  });

  it("a mensagem da API vence a frase de reserva", async () => {
    await render(<CartaoFeedback feedback={{ estado: "pendente", mensagem: "Frase vinda da API." }} aoAtualizar={jest.fn()} />);
    expect(screen.getByTestId("feedback-mensagem")).toHaveTextContent("Frase vinda da API.");
    expect(screen.queryByText(/ainda não foi gerado/)).toBeNull();
  });

  it("indisponível: só a mensagem, sem botão; o motivo nunca aparece nem muda o desenho", async () => {
    const { rerender } = await render(
      <CartaoFeedback feedback={{ estado: "indisponivel", motivo: "texto_reprovado" }} aoAtualizar={jest.fn()} aoFazerCheckin={jest.fn()} />,
    );
    expect(screen.getByTestId("feedback-mensagem")).toHaveTextContent("Ainda não foi possível gerar o feedback deste treino. Uma nova tentativa será feita mais tarde.");
    expect(screen.queryByText(/texto_reprovado/)).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
    const arvore = JSON.stringify(screen.toJSON());
    await rerender(
      <CartaoFeedback
        feedback={{ estado: "indisponivel", motivo: "provedor_nao_configurado", mensagem: "O feedback automático não está ligado neste app." }}
        aoAtualizar={jest.fn()}
        aoFazerCheckin={jest.fn()}
      />,
    );
    expect(screen.getByTestId("feedback-mensagem")).toHaveTextContent("O feedback automático não está ligado neste app.");
    expect(screen.queryByText(/provedor_nao_configurado/)).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
    expect(JSON.stringify(screen.toJSON()).replace(/O feedback automático não está ligado neste app\./, "")).toBe(
      arvore.replace(/Ainda não foi possível gerar o feedback deste treino\. Uma nova tentativa será feita mais tarde\./, ""),
    );
  });

  it("pronto sem texto (contrato quebrado): não mostra texto vazio, cai na frase de indisponível", async () => {
    await render(<CartaoFeedback feedback={{ estado: "pronto" }} />);
    expect(screen.queryByTestId("feedback-texto")).toBeNull();
    expect(screen.getByTestId("feedback-mensagem")).toHaveTextContent(/Ainda não foi possível/);
  });

  it("feedback nulo ou ausente: sem cartão", async () => {
    const { rerender } = await render(<CartaoFeedback feedback={null} />);
    expect(screen.queryByTestId("cartao-feedback")).toBeNull();
    await rerender(<CartaoFeedback feedback={undefined} />);
    expect(screen.queryByTestId("cartao-feedback")).toBeNull();
  });

  it("não usa cores de estado: nenhum estilo do cartão traz sucesso, alerta ou erro", async () => {
    await render(<CartaoFeedback feedback={{ estado: "sem_checkin", checkin_aberto: true }} aoFazerCheckin={jest.fn()} />);
    const json = JSON.stringify(screen.toJSON());
    for (const t of [coresClaro, coresEscuro]) {
      for (const nome of ["sucesso", "sucesso-suave", "alerta", "alerta-suave", "erro", "erro-suave"] as const) expect(json).not.toContain(t[nome]);
    }
  });
});

describe("'Atualizar': recarga e anúncio", () => {
  let anuncio: jest.SpyInstance;
  beforeEach(() => {
    anuncio = jest.spyOn(AccessibilityInfo, "announceForAccessibility").mockImplementation(() => {});
  });
  afterEach(() => anuncio.mockRestore());

  it("anuncia 'Feedback pronto.' quando já está pronto, 'ainda não está pronto' quando não, e falha de busca", async () => {
    const atualizar = jest.fn<Promise<FeedbackTreino | null | undefined>, []>();
    await render(<CartaoFeedback feedback={{ estado: "pendente" }} aoAtualizar={atualizar} />);
    atualizar.mockResolvedValueOnce(pronto);
    await fireEvent.press(screen.getByTestId("feedback-atualizar"));
    await waitFor(() => expect(anuncio).toHaveBeenLastCalledWith("Feedback pronto."));
    atualizar.mockResolvedValueOnce({ estado: "pendente" });
    await fireEvent.press(screen.getByTestId("feedback-atualizar"));
    await waitFor(() => expect(anuncio).toHaveBeenLastCalledWith("O feedback ainda não está pronto."));
    atualizar.mockResolvedValueOnce(undefined);
    await fireEvent.press(screen.getByTestId("feedback-atualizar"));
    await waitFor(() => expect(anuncio).toHaveBeenLastCalledWith("Não foi possível atualizar o feedback."));
  });

  it("região viva (Android): elemento sempre montado com accessibilityLiveRegion polite, que recebe o anúncio", async () => {
    const atualizar = jest.fn(async () => pronto as FeedbackTreino | null | undefined);
    await render(<CartaoFeedback feedback={{ estado: "pendente" }} aoAtualizar={atualizar} />);
    const regiao = screen.getByTestId("feedback-anuncio");
    expect(regiao.props.accessibilityLiveRegion).toBe("polite");
    expect(regiao).toHaveTextContent("");
    await fireEvent.press(screen.getByTestId("feedback-atualizar"));
    await waitFor(() => expect(screen.getByTestId("feedback-anuncio")).toHaveTextContent("Feedback pronto."));
    // continua o mesmo elemento mesmo com o cartão trocando de estado
    expect(screen.getByTestId("feedback-anuncio").props.accessibilityLiveRegion).toBe("polite");
  });

  it("no Android a região viva anuncia e o announceForAccessibility não é chamado", async () => {
    const os = Platform.OS;
    Platform.OS = "android";
    try {
      await render(<CartaoFeedback feedback={{ estado: "pendente" }} aoAtualizar={jest.fn(async () => ({ estado: "pendente" }) as FeedbackTreino)} />);
      await fireEvent.press(screen.getByTestId("feedback-atualizar"));
      await waitFor(() => expect(screen.getByTestId("feedback-anuncio")).toHaveTextContent("O feedback ainda não está pronto."));
      expect(anuncio).not.toHaveBeenCalled();
    } finally {
      Platform.OS = os;
    }
  });

  it("enquanto busca, o botão fica desligado ('Atualizando...') e não dispara duas buscas", async () => {
    let solta: (f: FeedbackTreino) => void = () => {};
    const atualizar = jest.fn(() => new Promise<FeedbackTreino>((r) => (solta = r)));
    await render(<CartaoFeedback feedback={{ estado: "pendente" }} aoAtualizar={atualizar} />);
    await fireEvent.press(screen.getByTestId("feedback-atualizar"));
    const botao = await screen.findByTestId("feedback-atualizar");
    expect(botao.props.accessibilityState.disabled).toBe(true);
    expect(within(botao).getByText("Atualizando...")).toBeTruthy();
    await fireEvent.press(botao);
    expect(atualizar).toHaveBeenCalledTimes(1);
    await waitFor(() => solta(pronto));
  });
});

const resposta = (corpo: unknown, status = 200) => ({ ok: status < 300, status, json: async () => corpo }) as Response;

describe("cartão Feedback na tela do treino", () => {
  const comFeedback = (feedback: FeedbackTreino | null | undefined): Atividade => ({ ...atividadesCheckin.comCheckin, feedback }) as Atividade;
  const tela = (f: typeof fetch, extra = {}) => (
    <TelaTreino apiUrl="http://api.teste" atletaId={1} atividadeId={101} fetchFn={f} aoFazerCheckin={jest.fn()} aoEditarCheckin={jest.fn()} {...extra} />
  );

  it("ordem: Check-in, Feedback, Carga pela PSE, Clima", async () => {
    const f = jest.fn(async () => resposta(comFeedback(pronto)));
    await render(tela(f as unknown as typeof fetch));
    await screen.findByTestId("cartao-feedback");
    const ids = [...JSON.stringify(screen.toJSON()).matchAll(/"testID":"(cartao-[a-z-]+)"/g)].map((m) => m[1]);
    const ordem = ["cartao-resumo", "cartao-checkin", "cartao-feedback", "cartao-carga-pse"].filter((i) => ids.includes(i));
    expect(ids.filter((i) => ordem.includes(i))).toEqual(ordem);
    expect(ordem).toContain("cartao-feedback");
    expect(ordem).toContain("cartao-carga-pse");
  });

  it("feedback nulo ou sem o campo: o cartão não aparece", async () => {
    for (const fb of [null, undefined]) {
      const f = jest.fn(async () => resposta(comFeedback(fb)));
      const { unmount } = await render(tela(f as unknown as typeof fetch));
      await screen.findByTestId("cartao-checkin");
      expect(screen.queryByTestId("cartao-feedback")).toBeNull();
      await unmount();
    }
  });

  it("'Fazer check-in' do feedback abre o check-in", async () => {
    const fazer = jest.fn();
    const f = jest.fn(async () => resposta({ ...atividadesCheckin.semCheckin, feedback: { estado: "sem_checkin", checkin_aberto: true } }));
    await render(tela(f as unknown as typeof fetch, { aoFazerCheckin: fazer }));
    await fireEvent.press(await screen.findByTestId("feedback-fazer-checkin"));
    expect(fazer).toHaveBeenCalledTimes(1);
  });

  it("'Atualizar' busca a atividade de novo, troca o miolo para pronto e não apaga o resto da tela", async () => {
    const anuncio = jest.spyOn(AccessibilityInfo, "announceForAccessibility").mockImplementation(() => {});
    const respostas = [comFeedback({ estado: "pendente" }), comFeedback(pronto)];
    let i = 0;
    const f = jest.fn(async () => resposta(respostas[Math.min(i++, 1)]));
    await render(tela(f as unknown as typeof fetch));
    await fireEvent.press(await screen.findByTestId("feedback-atualizar"));
    await waitFor(() => expect(screen.getByTestId("feedback-texto")).toHaveTextContent(TEXTO));
    expect(screen.queryByText("Carregando o treino...")).toBeNull();
    expect(screen.getByTestId("cartao-resumo")).toBeTruthy();
    expect(screen.getByTestId("cartao-checkin")).toBeTruthy();
    expect(f).toHaveBeenCalledTimes(2);
    expect(anuncio).toHaveBeenLastCalledWith("Feedback pronto.");
    anuncio.mockRestore();
  });

  it("'Atualizar' com a busca falhando: o cartão e a tela ficam como estavam", async () => {
    const anuncio = jest.spyOn(AccessibilityInfo, "announceForAccessibility").mockImplementation(() => {});
    let i = 0;
    const f = jest.fn(async () => {
      if (i++ === 0) return resposta(comFeedback({ estado: "pendente" }));
      throw new Error("sem rede");
    });
    await render(tela(f as unknown as typeof fetch));
    await fireEvent.press(await screen.findByTestId("feedback-atualizar"));
    await waitFor(() => expect(anuncio).toHaveBeenLastCalledWith("Não foi possível atualizar o feedback."));
    expect(screen.getByTestId("feedback-mensagem")).toBeTruthy();
    expect(screen.getByTestId("cartao-resumo")).toBeTruthy();
    anuncio.mockRestore();
  });

  it("privacidade: o texto não vai a log nem ao armazenamento, e a busca leva só a URL da atividade", async () => {
    const log = [jest.spyOn(console, "log"), jest.spyOn(console, "warn"), jest.spyOn(console, "error"), jest.spyOn(console, "info")].map((s) => s.mockImplementation(() => {}));
    const setItem = jest.fn();
    const antes = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
    Object.defineProperty(globalThis, "localStorage", { value: { setItem, getItem: jest.fn(), removeItem: jest.fn() }, configurable: true });
    const f = jest.fn(async () => resposta(comFeedback(pronto)));
    await render(tela(f as unknown as typeof fetch));
    await screen.findByTestId("feedback-texto");
    for (const s of log) {
      expect(JSON.stringify(s.mock.calls)).not.toContain("Texto de exemplo");
      s.mockRestore();
    }
    expect(setItem).not.toHaveBeenCalled();
    for (const c of f.mock.calls as unknown as unknown[][]) expect(String(c[0])).not.toContain("Texto");
    if (antes) Object.defineProperty(globalThis, "localStorage", antes);
    else delete (globalThis as { localStorage?: unknown }).localStorage;
  });
});
