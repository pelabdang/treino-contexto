import { fireEvent, render, screen, waitFor, within } from "@testing-library/react-native";
import type { Atividade } from "@treino/api-client";

import { TelaCheckin } from "../src/componentes/TelaCheckin";
import { atividadesCheckin, checkinExemplo, MARCADOR } from "../__fixtures__/checkin";

jest.mock("@expo/vector-icons", () => {
  const { Text } = require("react-native");
  return { MaterialIcons: ({ name, size }: { name: string; size: number }) => <Text>{`${name}:${size}`}</Text> };
});

jest.setTimeout(20000);

type Servidor = {
  atividade?: Atividade | Error | number;
  put?: { status: number; corpo?: unknown } | Error;
  del?: { status: number } | Error;
};

/** `fetch` falso que responde por método: GET da atividade, PUT e DELETE do check-in. */
function servidor(s: Servidor) {
  const ok = (status: number, corpo?: unknown) =>
    ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
  return jest.fn(async (_url: unknown, init?: RequestInit) => {
    const metodo = init?.method ?? "GET";
    if (metodo === "PUT") {
      if (s.put instanceof Error) throw s.put;
      const { status, corpo } = s.put ?? { status: 200 };
      if (corpo !== undefined || status !== 200) return ok(status, corpo);
      const enviado = JSON.parse(String(init?.body));
      return ok(200, {
        ...checkinExemplo,
        ...enviado,
        pse_texto: String(enviado.pse),
        sensacao_texto: ["", "Muito mal", "Mal", "Normal", "Bem", "Muito bem"][enviado.sensacao],
        atalhos: enviado.atalhos.map((c: string) => ({ chave: c, texto: c })),
      });
    }
    if (metodo === "DELETE") {
      if (s.del instanceof Error) throw s.del;
      return ok(s.del?.status ?? 204);
    }
    if (s.atividade instanceof Error) throw s.atividade;
    if (typeof s.atividade === "number") return ok(s.atividade, { detail: "atividade não encontrada" });
    return ok(200, s.atividade ?? atividadesCheckin.semCheckin);
  }) as unknown as typeof fetch & jest.Mock;
}

const metodos = (f: jest.Mock, m: string) => f.mock.calls.filter((c) => (c[1]?.method ?? "GET") === m);

async function abrir(f: typeof fetch, extra: Record<string, unknown> = {}) {
  const props = { aoVoltar: jest.fn(), aoConcluir: jest.fn(), aoApagado: jest.fn(), ...extra };
  await render(<TelaCheckin apiUrl="http://api.teste" atletaId={1} atividadeId={101} fetchFn={f} {...props} />);
  return props;
}

const pergunta1 = () => screen.findByText("Qual foi o esforço do treino?");

describe("tela de check-in: criar", () => {
  it("mostra carregando com esqueleto e depois a pergunta 1", async () => {
    const f = jest.fn(() => new Promise<Response>(() => {})) as unknown as typeof fetch;
    await abrir(f);
    expect(screen.getByText("Carregando o check-in...")).toBeTruthy();
    expect(screen.getByTestId("esqueleto-checkin", { includeHiddenElements: true })).toBeTruthy();
  });

  it("pergunta 1: título, progresso, treino e onze botões de PSE com a âncora fixa", async () => {
    await abrir(servidor({}));
    await pergunta1();
    expect(screen.getByText("Check-in do treino")).toBeTruthy();
    expect(screen.getByText("Pergunta 1 de 3")).toBeTruthy();
    expect(screen.getByText("52 min · 18/03/25")).toBeTruthy();
    expect(screen.getByText("Corrida")).toBeTruthy();
    for (let n = 0; n <= 10; n++) expect(screen.getByTestId(`pse-${n}`)).toBeTruthy();
    expect(screen.getByLabelText("PSE 5, difícil")).toBeTruthy();
    expect(screen.getByLabelText("PSE 6")).toBeTruthy();
    expect(screen.getByLabelText("PSE 10, máximo")).toBeTruthy();
    expect(screen.getByText("0 é repouso e 10 é o máximo. É a sua percepção.")).toBeTruthy();
    expect(screen.getByText("A PSE é só sua: não se compara com a de outros atletas.")).toBeTruthy();
  });

  it("nada a relatar fecha em 3 toques, com um único PUT no fim", async () => {
    const f = servidor({});
    await abrir(f);
    await pergunta1();
    await fireEvent.press(screen.getByTestId("pse-5"));
    await screen.findByText("Como você se sentiu no treino?");
    expect(screen.getByText("Pergunta 2 de 3")).toBeTruthy();
    expect(metodos(f, "PUT")).toHaveLength(0);
    await fireEvent.press(screen.getByTestId("sensacao-4"));
    await screen.findByText("Quer registrar mais alguma coisa?");
    expect(metodos(f, "PUT")).toHaveLength(0);
    await fireEvent.press(screen.getByTestId("nada-a-relatar"));
    await screen.findByText("Check-in salvo");
    const puts = metodos(f, "PUT");
    expect(puts).toHaveLength(1);
    expect(String(puts[0][0])).toBe("http://api.teste/atletas/1/atividades/101/checkin");
    expect(JSON.parse(puts[0][1].body)).toEqual({ pse: 5, sensacao: 4, nada_a_relatar: true, atalhos: [], texto: null });
    expect(screen.getByText("Voltar ao treino")).toBeTruthy();
  });

  it("com atalho são 4 toques: o botão Salvar fica desligado até haver atalho ou texto, e explica o motivo", async () => {
    const f = servidor({});
    await abrir(f);
    await pergunta1();
    await fireEvent.press(screen.getByTestId("pse-7"));
    await screen.findByText("Como você se sentiu no treino?");
    await fireEvent.press(screen.getByTestId("sensacao-2"));
    await screen.findByText("Quer registrar mais alguma coisa?");
    const salvar = screen.getByTestId("salvar-checkin");
    expect(salvar.props.accessibilityState.disabled).toBe(true);
    expect(screen.getByText("Marque um atalho, escreva algo ou toque em Nada a relatar.")).toBeTruthy();
    await fireEvent.press(salvar);
    expect(metodos(f, "PUT")).toHaveLength(0);
    // vários atalhos, sem salvar sozinho
    await fireEvent.press(screen.getByTestId("atalho-sono_ruim"));
    await fireEvent.press(screen.getByTestId("atalho-dor"));
    expect(metodos(f, "PUT")).toHaveLength(0);
    expect(screen.getByTestId("atalho-dor").props.accessibilityState.checked).toBe(true);
    expect(screen.queryByText("Marque um atalho, escreva algo ou toque em Nada a relatar.")).toBeNull();
    await fireEvent.press(screen.getByTestId("salvar-checkin"));
    await screen.findByText("Check-in salvo");
    // atalhos na ordem fixa da lista, não na ordem dos toques
    expect(JSON.parse(metodos(f, "PUT")[0][1].body)).toEqual({
      pse: 7,
      sensacao: 2,
      nada_a_relatar: false,
      atalhos: ["dor", "sono_ruim"],
      texto: null,
    });
  });

  it("só texto também salva; o texto é aparado e o contador mostra N de 500", async () => {
    const f = servidor({});
    await abrir(f);
    await pergunta1();
    await fireEvent.press(screen.getByTestId("pse-3"));
    await fireEvent.press(await screen.findByTestId("sensacao-3"));
    const campo = await screen.findByTestId("campo-texto");
    expect(campo.props.maxLength).toBe(500);
    await fireEvent.changeText(campo, `  ${MARCADOR}  `);
    expect(screen.getByText(`${MARCADOR.length + 4} de 500`)).toBeTruthy();
    await fireEvent.press(screen.getByTestId("salvar-checkin"));
    await screen.findByText("Check-in salvo");
    expect(JSON.parse(metodos(f, "PUT")[0][1].body).texto).toBe(MARCADOR);
  });

  it("acima de 450 caracteres o contador ganha o ícone de alerta", async () => {
    await abrir(servidor({}));
    await pergunta1();
    await fireEvent.press(screen.getByTestId("pse-3"));
    await fireEvent.press(await screen.findByTestId("sensacao-3"));
    const campo = await screen.findByTestId("campo-texto");
    await fireEvent.changeText(campo, "a".repeat(450));
    expect(screen.queryByText("warning-amber:16")).toBeNull();
    await fireEvent.changeText(campo, "a".repeat(451));
    expect(screen.getByText("warning-amber:16")).toBeTruthy();
  });

  it("'Nada a relatar' com atalho marcado pede confirmação antes de apagar e salvar", async () => {
    const f = servidor({});
    await abrir(f);
    await pergunta1();
    await fireEvent.press(screen.getByTestId("pse-3"));
    await fireEvent.press(await screen.findByTestId("sensacao-3"));
    await fireEvent.press(await screen.findByTestId("atalho-calor"));
    await fireEvent.press(screen.getByTestId("nada-a-relatar"));
    expect(screen.getByText("Descartar o que você marcou?")).toBeTruthy();
    expect(screen.getByText("Nada a relatar apaga os atalhos e o texto desta pergunta.")).toBeTruthy();
    expect(metodos(f, "PUT")).toHaveLength(0);
    await fireEvent.press(screen.getByText("Cancelar"));
    expect(screen.queryByText("Descartar o que você marcou?")).toBeNull();
    expect(screen.getByTestId("atalho-calor").props.accessibilityState.checked).toBe(true);
    await fireEvent.press(screen.getByTestId("nada-a-relatar"));
    const dialogo = screen.getByText("Descartar o que você marcou?").parent!.parent!;
    await fireEvent.press(within(dialogo).getByText("Nada a relatar"));
    await screen.findByText("Check-in salvo");
    expect(JSON.parse(metodos(f, "PUT")[0][1].body)).toMatchObject({ nada_a_relatar: true, atalhos: [], texto: null });
  });

  it("Voltar volta de pergunta, mantém as respostas e na pergunta 1 sai da tela", async () => {
    const f = servidor({});
    const { aoVoltar } = await abrir(f);
    await pergunta1();
    await fireEvent.press(screen.getByTestId("pse-5"));
    await fireEvent.press(await screen.findByTestId("sensacao-4"));
    await screen.findByText("Quer registrar mais alguma coisa?");
    await fireEvent.press(screen.getByLabelText("Voltar"));
    await screen.findByText("Como você se sentiu no treino?");
    expect(screen.getByTestId("sensacao-4").props.accessibilityState.checked).toBe(true);
    await fireEvent.press(screen.getByLabelText("Voltar"));
    await pergunta1();
    expect(screen.getByTestId("pse-5").props.accessibilityState.checked).toBe(true);
    expect(aoVoltar).not.toHaveBeenCalled();
    await fireEvent.press(screen.getByLabelText("Voltar"));
    expect(aoVoltar).toHaveBeenCalledTimes(1);
  });

  it("sair com atalho marcado pede 'Sair sem salvar?'; PSE e sensação sozinhas não pedem", async () => {
    const { aoVoltar } = await abrir(servidor({}));
    await pergunta1();
    await fireEvent.press(screen.getByTestId("pse-5"));
    await fireEvent.press(await screen.findByTestId("sensacao-4"));
    await fireEvent.press(await screen.findByTestId("atalho-dor"));
    await fireEvent.press(screen.getByLabelText("Voltar")); // pergunta 2
    await fireEvent.press(await screen.findByLabelText("Voltar")); // pergunta 1
    await pergunta1();
    await fireEvent.press(screen.getByLabelText("Voltar")); // sair
    expect(screen.getByText("Sair sem salvar?")).toBeTruthy();
    expect(aoVoltar).not.toHaveBeenCalled();
    await fireEvent.press(screen.getByText("Continuar"));
    expect(screen.queryByText("Sair sem salvar?")).toBeNull();
    await fireEvent.press(screen.getByLabelText("Voltar"));
    await fireEvent.press(screen.getByText("Sair"));
    expect(aoVoltar).toHaveBeenCalledTimes(1);
  });

  it("sem atalho nem texto, sair não pergunta nada", async () => {
    const { aoVoltar } = await abrir(servidor({}));
    await pergunta1();
    await fireEvent.press(screen.getByTestId("pse-5"));
    await screen.findByText("Como você se sentiu no treino?");
    await fireEvent.press(screen.getByLabelText("Voltar"));
    await pergunta1();
    await fireEvent.press(screen.getByLabelText("Voltar"));
    expect(screen.queryByText("Sair sem salvar?")).toBeNull();
    expect(aoVoltar).toHaveBeenCalledTimes(1);
  });

  it("PSE sugerida da parte anterior: aviso com âncora, 'Usar 5' escolhe e vai para a pergunta 2; não vem marcada", async () => {
    await abrir(servidor({ atividade: atividadesCheckin.comSugestao }));
    await pergunta1();
    expect(screen.getByText("Na parte anterior você marcou 5 (difícil).")).toBeTruthy();
    expect(screen.getByTestId("pse-5").props.accessibilityState.checked).toBe(false);
    await fireEvent.press(screen.getByLabelText("Usar 5"));
    await screen.findByText("Como você se sentiu no treino?");
  });

  it("PSE sugerida sem âncora (6) e sem sugestão (null)", async () => {
    const { unmount } = await render(
      <TelaCheckin apiUrl="http://api.teste" atletaId={1} atividadeId={101} fetchFn={servidor({ atividade: atividadesCheckin.comSugestaoSemAncora })} />,
    );
    await pergunta1();
    expect(screen.getByText("Na parte anterior você marcou 6.")).toBeTruthy();
    await unmount();
    await abrir(servidor({}));
    await pergunta1();
    expect(screen.queryByTestId("pse-sugerida")).toBeNull();
  });

  it("origem pendentes: o botão de salvo é 'Voltar aos pendentes'", async () => {
    const f = servidor({});
    const props = await abrir(f, { origem: "pendentes" });
    await pergunta1();
    await fireEvent.press(screen.getByTestId("pse-5"));
    await fireEvent.press(await screen.findByTestId("sensacao-4"));
    await fireEvent.press(await screen.findByTestId("nada-a-relatar"));
    await fireEvent.press(await screen.findByText("Voltar aos pendentes"));
    expect(props.aoConcluir).toHaveBeenCalled();
  });
});

describe("tela de check-in: erros", () => {
  async function ate3(f: typeof fetch) {
    await abrir(f);
    await pergunta1();
    await fireEvent.press(screen.getByTestId("pse-5"));
    await fireEvent.press(await screen.findByTestId("sensacao-4"));
    await fireEvent.press(await screen.findByTestId("atalho-dor"));
  }

  it("erro de rede ao salvar: aviso, respostas ficam e o botão volta a ligar", async () => {
    const f = servidor({ put: new Error("x") });
    await ate3(f);
    await fireEvent.press(screen.getByTestId("salvar-checkin"));
    const aviso = await screen.findByRole("alert");
    expect(within(aviso).getByText("Não foi possível falar com o servidor. Suas respostas continuam aqui. Tente salvar de novo.")).toBeTruthy();
    expect(screen.getByTestId("atalho-dor").props.accessibilityState.checked).toBe(true);
    expect(screen.getByTestId("salvar-checkin").props.accessibilityState.disabled).toBe(false);
  });

  it("422 genérico, 404 e 500 ao salvar mostram texto fixo, nunca o detail da API", async () => {
    const casos: [number, unknown, string][] = [
      [422, { detail: [{ loc: ["body", "texto"], msg: "DETALHE-TECNICO", type: "string_too_long" }] }, "Algum dado do check-in não foi aceito. Confira as respostas e tente de novo."],
      [404, { detail: "DETALHE-TECNICO" }, "Treino não encontrado."],
      [500, {}, "Não foi possível salvar. Tente de novo mais tarde."],
    ];
    for (const [status, corpo, texto] of casos) {
      const { unmount } = await render(
        <TelaCheckin apiUrl="http://api.teste" atletaId={1} atividadeId={101} fetchFn={servidor({ put: { status, corpo } })} />,
      );
      await pergunta1();
      await fireEvent.press(screen.getByTestId("pse-5"));
      await fireEvent.press(await screen.findByTestId("sensacao-4"));
      await fireEvent.press(await screen.findByTestId("atalho-dor"));
      await fireEvent.press(screen.getByTestId("salvar-checkin"));
      await screen.findByText(texto);
      expect(screen.queryByText(/DETALHE-TECNICO/)).toBeNull();
      await unmount();
    }
  });

  it("422 fora_do_prazo: tela de aviso sem 'Tentar de novo' e botão para o treino", async () => {
    const f = servidor({ put: { status: 422, corpo: { detail: [{ loc: [], msg: "m", type: "fora_do_prazo" }] } } });
    const props = await abrir(f);
    await pergunta1();
    await fireEvent.press(screen.getByTestId("pse-5"));
    await fireEvent.press(await screen.findByTestId("sensacao-4"));
    await fireEvent.press(await screen.findByTestId("nada-a-relatar"));
    const aviso = await screen.findByTestId("estado-aviso");
    expect(
      within(aviso).getByText(
        "O prazo para fazer o check-in deste treino acabou (7 dias depois do treino). Check-ins que já existem ainda podem ser editados.",
      ),
    ).toBeTruthy();
    expect(within(aviso).getByText("error-outline:40")).toBeTruthy();
    expect(screen.queryByText("Tentar de novo")).toBeNull();
    await fireEvent.press(within(aviso).getByText("Voltar ao treino"));
    expect(props.aoConcluir).toHaveBeenCalled();
  });

  it("422 atividade_sem_checkin: 'Este treino não pede check-in.'", async () => {
    const f = servidor({ put: { status: 422, corpo: { detail: [{ loc: [], msg: "m", type: "atividade_sem_checkin" }] } } });
    await abrir(f);
    await pergunta1();
    await fireEvent.press(screen.getByTestId("pse-5"));
    await fireEvent.press(await screen.findByTestId("sensacao-4"));
    await fireEvent.press(await screen.findByTestId("nada-a-relatar"));
    await screen.findByText("Este treino não pede check-in.");
  });

  it("abrir direto uma atividade com prazo vencido ou sem check-in elegível mostra o aviso, sem perguntas", async () => {
    const { unmount } = await render(
      <TelaCheckin apiUrl="http://api.teste" atletaId={1} atividadeId={101} fetchFn={servidor({ atividade: atividadesCheckin.foraDoPrazo })} />,
    );
    await screen.findByText(/O prazo para fazer o check-in deste treino acabou/);
    expect(screen.queryByText("Qual foi o esforço do treino?")).toBeNull();
    await unmount();
    await abrir(servidor({ atividade: atividadesCheckin.multiesportePai }));
    await screen.findByText("Este treino não pede check-in.");
  });

  it("erro ao carregar: rede tem 'Tentar de novo'; 404 e 500 não", async () => {
    const { unmount } = await render(
      <TelaCheckin apiUrl="http://api.teste" atletaId={1} atividadeId={101} fetchFn={servidor({ atividade: new Error("x") })} />,
    );
    const rede = await screen.findByTestId("estado-erro");
    expect(within(rede).getByText("wifi-off:40")).toBeTruthy();
    expect(within(rede).getByText("Não foi possível falar com o servidor")).toBeTruthy();
    expect(within(rede).getByText("Tentar de novo")).toBeTruthy();
    await unmount();
    await abrir(servidor({ atividade: 404 }));
    const nao = await screen.findByTestId("estado-erro");
    expect(within(nao).getByText("Treino não encontrado")).toBeTruthy();
    expect(within(nao).queryByText("Tentar de novo")).toBeNull();
  });

  it("'Tentar de novo' busca o treino outra vez", async () => {
    let falhar = true;
    const f = jest.fn(async () => {
      if (falhar) throw new Error("x");
      return { ok: true, status: 200, json: async () => atividadesCheckin.semCheckin } as Response;
    }) as unknown as typeof fetch;
    await abrir(f);
    await fireEvent.press(await screen.findByText("Tentar de novo"));
    falhar = false;
    // o primeiro toque ainda pode correr contra a falha; garantimos o segundo ciclo
    await waitFor(async () => {
      if (!screen.queryByText("Qual foi o esforço do treino?")) {
        const botao = screen.queryByText("Tentar de novo");
        if (botao) await fireEvent.press(botao);
        throw new Error("ainda carregando");
      }
    });
  });
});

describe("tela de check-in: editar", () => {
  const edicao = (extra: Servidor = {}) => servidor({ atividade: atividadesCheckin.comCheckin, ...extra });

  it("abre em tela única com o resumo e sem passo a passo", async () => {
    await abrir(edicao());
    await screen.findByText("Editar check-in");
    expect(screen.getByTestId("resumo-pse").props.children).toBe("5 · difícil");
    expect(screen.getByTestId("resumo-sensacao").props.children).toBe("Bem");
    expect(screen.getByTestId("atalho-cansaco").props.accessibilityState.checked).toBe(true);
    expect(screen.getByTestId("atalho-dor").props.accessibilityState.checked).toBe(false);
    expect(screen.getByTestId("campo-texto").props.value).toBe(MARCADOR);
    expect(screen.queryByText("Pergunta 1 de 3")).toBeNull();
    expect(screen.getByTestId("salvar-alteracoes").props.accessibilityState.disabled).toBe(true);
  });

  it("'Mudar' abre a folha com o valor atual marcado; tocar escolhe e fecha; salvar substitui o registro", async () => {
    const f = edicao();
    await abrir(f);
    await screen.findByText("Editar check-in");
    await fireEvent.press(screen.getByTestId("mudar-pse"));
    expect(screen.getByTestId("pse-5").props.accessibilityState.checked).toBe(true);
    await fireEvent.press(screen.getByTestId("pse-6"));
    expect(screen.queryByTestId("pse-5")).toBeNull();
    expect(screen.getByTestId("resumo-pse").props.children).toBe("6");
    await fireEvent.press(screen.getByTestId("mudar-sensacao"));
    expect(screen.getByTestId("sensacao-4").props.accessibilityState.checked).toBe(true);
    await fireEvent.press(screen.getByTestId("sensacao-5"));
    expect(screen.getByTestId("resumo-sensacao").props.children).toBe("Muito bem");
    await fireEvent.press(screen.getByTestId("salvar-alteracoes"));
    await screen.findByText("Check-in salvo");
    expect(JSON.parse(metodos(f, "PUT")[0][1].body)).toEqual({
      pse: 6,
      sensacao: 5,
      nada_a_relatar: false,
      atalhos: ["cansaco", "trabalho_estresse"],
      texto: MARCADOR,
    });
  });

  it("'Nada a relatar' é rádio que não salva sozinho e limpa atalhos e texto (com diálogo de descarte)", async () => {
    const f = edicao();
    await abrir(f);
    await screen.findByText("Editar check-in");
    await fireEvent.press(screen.getByTestId("nada-a-relatar"));
    expect(screen.getByText("Descartar o que você marcou?")).toBeTruthy();
    const dialogo = screen.getByText("Descartar o que você marcou?").parent!.parent!;
    await fireEvent.press(within(dialogo).getByText("Nada a relatar"));
    expect(metodos(f, "PUT")).toHaveLength(0);
    expect(screen.getByTestId("nada-a-relatar").props.accessibilityState.checked).toBe(true);
    expect(screen.getByTestId("atalho-cansaco").props.accessibilityState.checked).toBe(false);
    expect(screen.getByTestId("campo-texto").props.value).toBe("");
    expect(screen.getByTestId("salvar-alteracoes").props.accessibilityState.disabled).toBe(false);
    // marcar um atalho desmarca "Nada a relatar"
    await fireEvent.press(screen.getByTestId("atalho-dor"));
    expect(screen.getByTestId("nada-a-relatar").props.accessibilityState.checked).toBe(false);
  });

  it("apagar abre o diálogo; 'Cancelar' não apaga; 'Apagar' chama DELETE e avisa a rota", async () => {
    const f = edicao();
    const props = await abrir(f);
    await screen.findByText("Editar check-in");
    await fireEvent.press(screen.getByTestId("apagar-checkin"));
    expect(screen.getByText("Apagar este check-in?")).toBeTruthy();
    expect(screen.getByText("A PSE, a sensação e a observação deste treino serão apagadas. Isso não pode ser desfeito.")).toBeTruthy();
    await fireEvent.press(screen.getByText("Cancelar"));
    expect(metodos(f, "DELETE")).toHaveLength(0);
    await fireEvent.press(screen.getByTestId("apagar-checkin"));
    await fireEvent.press(screen.getByText("Apagar"));
    await waitFor(() => expect(props.aoApagado).toHaveBeenCalled());
    expect(String(metodos(f, "DELETE")[0][0])).toBe("http://api.teste/atletas/1/atividades/101/checkin");
  });

  it("erro ao apagar: aviso e o check-in continua na tela", async () => {
    const props = await abrir(edicao({ del: new Error("x") }));
    await screen.findByText("Editar check-in");
    await fireEvent.press(screen.getByTestId("apagar-checkin"));
    await fireEvent.press(screen.getByText("Apagar"));
    await screen.findByText("Não foi possível apagar. Tente de novo.");
    expect(props.aoApagado).not.toHaveBeenCalled();
    expect(screen.getByTestId("resumo-pse")).toBeTruthy();
  });

  it("editar não tem prazo: abre mesmo com checkin_aberto falso", async () => {
    await abrir(servidor({ atividade: { ...atividadesCheckin.comCheckin, checkin_aberto: false } as Atividade }));
    await screen.findByText("Editar check-in");
  });
});

describe("privacidade", () => {
  it("nenhum valor do check-in vai para console, e a URL só leva ids", async () => {
    const espioes = (["log", "info", "warn", "error", "debug"] as const).map((m) => jest.spyOn(console, m).mockImplementation(() => {}));
    const f = servidor({ put: { status: 500, corpo: {} } });
    await abrir(f);
    await pergunta1();
    await fireEvent.press(screen.getByTestId("pse-5"));
    await fireEvent.press(await screen.findByTestId("sensacao-4"));
    await fireEvent.changeText(await screen.findByTestId("campo-texto"), MARCADOR);
    await fireEvent.press(screen.getByTestId("salvar-checkin"));
    await screen.findByText("Não foi possível salvar. Tente de novo mais tarde.");
    const impresso = espioes.flatMap((e) => e.mock.calls).map((c) => JSON.stringify(c)).join("\n");
    expect(impresso).not.toContain(MARCADOR);
    for (const [url] of f.mock.calls) expect(String(url)).not.toContain(MARCADOR);
    espioes.forEach((e) => e.mockRestore());
  });
});
