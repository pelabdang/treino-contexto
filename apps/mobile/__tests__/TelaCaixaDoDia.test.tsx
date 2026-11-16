import { fireEvent, render, screen, waitFor, within } from "@testing-library/react-native";
import { AccessibilityInfo } from "react-native";

import { buscarCaixaDoDia, type CaixaDoDia } from "../src/caixa/api";
import { dataDeHoje, TelaCaixaDoDia } from "../src/componentes/TelaCaixaDoDia";
import { caixa, OBSERVACAO_MARCADOR } from "../__fixtures__/caixaDoDia";

jest.mock("@expo/vector-icons", () => {
  const { Text } = require("react-native");
  return { MaterialIcons: ({ name, size }: { name: string; size: number }) => <Text>{`${name}:${size}`}</Text> };
});

jest.setTimeout(20000);

const resposta = (status: number, corpo: unknown) => ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const fetchCom = (status: number, corpo: unknown) =>
  jest.fn(async (..._a: Parameters<typeof fetch>) => resposta(status, corpo)) as unknown as typeof fetch & jest.Mock;
const copia = (): CaixaDoDia => JSON.parse(JSON.stringify(caixa));
const tela = (f: typeof fetch, professorId: number | null = 7) => <TelaCaixaDoDia apiUrl="http://api.teste" professorId={professorId} fetchFn={f} />;

describe("caixa do dia: lista de atenção", () => {
  it("chama a API do professor configurado", async () => {
    const f = fetchCom(200, caixa);
    await render(tela(f));
    await screen.findByTestId("resumo");
    expect(f.mock.calls[0][0]).toBe("http://api.teste/professores/7/caixa-do-dia");
  });

  it("carregando: esqueleto e texto, com o título já na tela", async () => {
    await render(tela(jest.fn(() => new Promise<Response>(() => {})) as unknown as typeof fetch));
    expect(screen.getByText("Carregando a caixa do dia...")).toBeTruthy();
    expect(screen.getByTestId("esqueleto-caixa", { includeHiddenElements: true })).toBeTruthy();
    expect(screen.getByText("Caixa do dia")).toBeTruthy();
  });

  it("cabeçalho, resumo e seções com os textos da spec", async () => {
    await render(tela(fetchCom(200, caixa)));
    await screen.findByTestId("resumo");
    expect(screen.getByText("Quinta, 13/11/25")).toBeTruthy();
    expect(screen.getByTestId("resumo").props.children).toBe("3 alunos para olhar · 2 treinos novos");
    expect(screen.getByText("Para olhar hoje")).toBeTruthy();
    expect(screen.getByText("Treinos novos")).toBeTruthy();
    expect(screen.getByText(/^Últimos 7 dias\. Primeiro quem tem dor marcada/)).toBeTruthy();
    expect(screen.getByText("Últimos 14 dias, com tipo sugerido.")).toBeTruthy();
  });

  it("resumo no singular", async () => {
    const c = copia();
    c.alunos = [c.alunos[0]];
    c.novos = [c.novos[0]];
    await render(tela(fetchCom(200, c)));
    expect((await screen.findByTestId("resumo")).props.children).toBe("1 aluno para olhar · 1 treino novo");
  });

  it("alunos na ordem que a API mandou (o app não reordena)", async () => {
    const c = copia();
    c.alunos = [c.alunos[2], c.alunos[0], c.alunos[1], c.alunos[3]];
    await render(tela(fetchCom(200, c)));
    await screen.findByTestId("resumo");
    const ids = screen.getAllByTestId(/^aluno-\d+$/).map((n) => n.props.testID);
    expect(ids).toEqual(["aluno-3", "aluno-1", "aluno-2", "aluno-4"]);
  });

  it("treinos novos na ordem da API", async () => {
    const c = copia();
    c.novos = [c.novos[1], c.novos[0]];
    await render(tela(fetchCom(200, c)));
    await screen.findByTestId("resumo");
    const ids = screen.getAllByTestId(/^novo-\d+$/).map((n) => n.props.testID);
    expect(ids).toEqual(["novo-512", "novo-511"]);
  });

  it("um motivo por linha, com o texto da API e o ícone do código", async () => {
    await render(tela(fetchCom(200, caixa)));
    await screen.findByTestId("resumo");
    const ana = screen.getByTestId("aluno-1");
    expect(within(ana).getByText("Treino de terça com dor marcada no check-in.")).toBeTruthy();
    expect(within(ana).getByText("Treino de terça fora do normal: FC média acima do habitual.")).toBeTruthy();
    expect(within(ana).getByText("healing:20")).toBeTruthy();
    expect(within(ana).getByText("show-chart:20")).toBeTruthy();
    expect(within(screen.getByTestId("aluno-2")).getByText("event:20")).toBeTruthy();
    expect(within(screen.getByTestId("aluno-3")).getByText("schedule:20")).toBeTruthy();
    expect(within(ana).getByText("Corrida · 45 min · 11/11/25")).toBeTruthy();
  });

  it("aluno sem motivo: linha compacta com a frase da API e sem seta", async () => {
    await render(tela(fetchCom(200, caixa)));
    await screen.findByTestId("resumo");
    const diego = screen.getByTestId("aluno-4");
    expect(within(diego).getByText("Nada a destacar nos últimos 7 dias.")).toBeTruthy();
    expect(within(diego).queryByRole("button")).toBeNull();
  });

  it("lista fechada nunca mostra PSE, sensação, atalho nem observação", async () => {
    await render(tela(fetchCom(200, caixa)));
    await screen.findByTestId("resumo");
    expect(screen.queryByText(OBSERVACAO_MARCADOR)).toBeNull();
    expect(screen.queryByText("Observação do aluno")).toBeNull();
    expect(screen.queryByText("Esforço")).toBeNull();
    expect(screen.queryByText("Dor, Cansaço")).toBeNull();
  });
});

describe("caixa do dia: detalhe em acordeão", () => {
  it("a linha é um botão fechado, com rótulo de motivo, modalidade, duração e data", async () => {
    await render(tela(fetchCom(200, caixa)));
    const linha = await screen.findByTestId("treino-501");
    expect(linha.props.accessibilityRole).toBe("button");
    expect(linha.props.accessibilityState).toEqual({ expanded: false });
    expect(linha.props.accessibilityLabel).toBe(
      "Treino de terça com dor marcada no check-in. Treino de terça fora do normal: FC média acima do habitual. Corrida, 45 min, 11 de novembro.",
    );
  });

  it("tocar abre o detalhe no mesmo lugar e tocar de novo fecha", async () => {
    await render(tela(fetchCom(200, caixa)));
    const linha = await screen.findByTestId("treino-501");
    await fireEvent.press(linha);
    const d = screen.getByTestId("detalhe-501");
    expect(screen.getByTestId("treino-501").props.accessibilityState).toEqual({ expanded: true });
    expect(within(d).getByText("Intervalado")).toBeTruthy();
    expect(within(d).getByText("sugerido pela regra")).toBeTruthy();
    expect(within(d).getByText("8")).toBeTruthy();
    expect(within(d).getByText("Mal")).toBeTruthy();
    expect(within(d).getByText("sentiment-dissatisfied:20")).toBeTruthy();
    expect(within(d).getByText("Dor, Cansaço")).toBeTruthy();
    expect(within(d).getByText("Texto de exemplo do feedback.")).toBeTruthy();
    await fireEvent.press(screen.getByTestId("treino-501"));
    expect(screen.queryByTestId("detalhe-501")).toBeNull();
  });

  it("mais de um aberto ao mesmo tempo; não vira rota nem navega", async () => {
    await render(tela(fetchCom(200, caixa)));
    await fireEvent.press(await screen.findByTestId("treino-501"));
    await fireEvent.press(screen.getByTestId("treino-502"));
    expect(screen.getByTestId("detalhe-501")).toBeTruthy();
    expect(screen.getByTestId("detalhe-502")).toBeTruthy();
  });

  it("observação só no detalhe, com a frase de privacidade, e nunca em rótulo de acessibilidade", async () => {
    await render(tela(fetchCom(200, caixa)));
    await fireEvent.press(await screen.findByTestId("treino-501"));
    const obs = screen.getByTestId("observacao");
    expect(within(obs).getByText("Observação do aluno")).toBeTruthy();
    expect(within(obs).getByText("Só você vê. Não vai ao provedor de IA.")).toBeTruthy();
    expect(within(obs).getByText(OBSERVACAO_MARCADOR)).toBeTruthy();
    expect(screen.getAllByText(new RegExp("MARCADOR-OBS-123"))).toHaveLength(1);
    const rotulos = screen.getAllByRole("button").map((b) => String(b.props.accessibilityLabel));
    expect(rotulos.join(" ")).not.toContain("MARCADOR-OBS-123");
  });

  it("sem check-in: 'Sem check-in ainda.' e sem observação nem esforço", async () => {
    await render(tela(fetchCom(200, caixa)));
    await fireEvent.press(await screen.findByTestId("treino-503"));
    const d = screen.getByTestId("detalhe-503");
    expect(within(d).getByText("Sem check-in ainda.")).toBeTruthy();
    expect(within(d).getByText("Sem tipo")).toBeTruthy();
    expect(within(d).queryByText("Esforço")).toBeNull();
    expect(within(d).queryByText("Observação do aluno")).toBeNull();
    expect(within(d).getByText("O prazo do check-in deste treino acabou.")).toBeTruthy();
  });

  it("atalhos: 'Nada a relatar' e 'Nenhum'", async () => {
    const c = copia();
    c.alunos[0].treinos[0].detalhe.checkin = { pse_texto: "3", sensacao: 4, sensacao_texto: "Bem", atalhos: [], nada_a_relatar: true, observacao: null };
    c.alunos[1].treinos[0].detalhe.checkin = { pse_texto: "3", sensacao: 4, sensacao_texto: "Bem", atalhos: [], nada_a_relatar: false, observacao: null };
    await render(tela(fetchCom(200, c)));
    await fireEvent.press(await screen.findByTestId("treino-501"));
    await fireEvent.press(screen.getByTestId("treino-502"));
    expect(within(screen.getByTestId("detalhe-501")).getByText("Nada a relatar")).toBeTruthy();
    expect(within(screen.getByTestId("detalhe-502")).getByText("Nenhum")).toBeTruthy();
    expect(screen.queryByTestId("observacao")).toBeNull();
  });

  it("feedback nulo: linha omitida", async () => {
    const c = copia();
    c.alunos[0].treinos[0].detalhe.feedback = null;
    await render(tela(fetchCom(200, c)));
    await fireEvent.press(await screen.findByTestId("treino-501"));
    expect(within(screen.getByTestId("detalhe-501")).queryByText("Feedback")).toBeNull();
  });

  it("treino novo: chip do tipo, origem, nome do aluno e detalhe", async () => {
    await render(tela(fetchCom(200, caixa)));
    const novo = await screen.findByTestId("novo-512");
    expect(within(novo).getByText("Atleta Fixture Diego")).toBeTruthy();
    expect(within(novo).getByText("Leve")).toBeTruthy();
    expect(within(novo).getByText("(sugerido pela semana-padrão)")).toBeTruthy();
    await fireEvent.press(screen.getByTestId("treino-novo-512"));
    expect(screen.getByTestId("detalhe-novo-512")).toBeTruthy();
    expect(screen.getByTestId("treino-novo-512").props.accessibilityLabel).toContain("Tipo sugerido Leve, sugerido pela semana-padrão.");
  });

  it("atualizar fecha tudo (o estado aberto não é guardado)", async () => {
    await render(tela(fetchCom(200, caixa)));
    await fireEvent.press(await screen.findByTestId("treino-501"));
    await fireEvent.press(screen.getByTestId("atualizar"));
    await waitFor(() => expect(screen.queryByTestId("detalhe-501")).toBeNull());
  });
});

describe("caixa do dia: estados", () => {
  it("sem alunos nem novos: estado vazio sem botão primário", async () => {
    const c = copia();
    c.alunos = [];
    c.novos = [];
    await render(tela(fetchCom(200, c)));
    await screen.findByTestId("estado-sem-alunos");
    expect(screen.getByText("Nenhum aluno na caixa do dia")).toBeTruthy();
    expect(screen.getByText("Aparecem aqui os alunos com vínculo e consentimento registrados.")).toBeTruthy();
    expect(screen.queryByText("Tentar de novo")).toBeNull();
  });

  it("alunos sem nenhum motivo e sem novos", async () => {
    const c = copia();
    c.alunos = [c.alunos[3]];
    c.novos = [];
    await render(tela(fetchCom(200, c)));
    await screen.findByTestId("resumo");
    expect(screen.getByTestId("resumo").props.children).toBe("0 alunos para olhar · 0 treinos novos");
    expect(screen.getByText("Nenhum aluno com algo a destacar nos últimos 7 dias.")).toBeTruthy();
    expect(screen.getByText("Nada a destacar nos últimos 7 dias.")).toBeTruthy();
    expect(screen.getByText("Nenhum treino novo para confirmar.")).toBeTruthy();
  });

  it("erro de rede: mensagem e 'Tentar de novo', que busca de novo", async () => {
    const f = jest.fn().mockRejectedValueOnce(new Error("x")).mockResolvedValue(resposta(200, caixa)) as unknown as typeof fetch & jest.Mock;
    await render(tela(f));
    await screen.findByText("Não foi possível falar com o servidor");
    expect(screen.getByText("Sua caixa do dia continua como estava. Tente de novo.")).toBeTruthy();
    await fireEvent.press(screen.getByText("Tentar de novo"));
    await screen.findByTestId("resumo");
    expect(f).toHaveBeenCalledTimes(2);
  });

  it("5xx: mensagem genérica e 'Tentar de novo'", async () => {
    await render(tela(fetchCom(500, { detail: "x" })));
    await screen.findByText("Não foi possível carregar a caixa do dia. Tente de novo mais tarde.");
    expect(screen.getByText("Tentar de novo")).toBeTruthy();
  });

  it("404 uniforme: 'Caixa do dia não encontrada', sem tentar de novo e sem atualizar", async () => {
    const f = fetchCom(404, { type: "professor_inexistente", detail: "x" });
    await render(tela(f));
    await screen.findByText("Caixa do dia não encontrada");
    expect(screen.getByText("Confira o professor configurado neste computador.")).toBeTruthy();
    expect(screen.queryByText("Tentar de novo")).toBeNull();
    expect(f).toHaveBeenCalledTimes(1);
  });

  it("sem professor configurado: mesmo texto do 404, sem chamar a API", async () => {
    const f = fetchCom(200, caixa);
    await render(tela(f, null));
    await screen.findByText("Caixa do dia não encontrada");
    expect(screen.queryByText("Tentar de novo")).toBeNull();
    expect(screen.queryByTestId("atualizar")).toBeNull();
    expect(f).not.toHaveBeenCalled();
  });

  it("atualizar mantém o conteúdo e anuncia; erro ao atualizar mostra aviso e não apaga a lista", async () => {
    const anuncio = jest.spyOn(AccessibilityInfo, "announceForAccessibility").mockImplementation(() => {});
    const f = jest.fn().mockResolvedValueOnce(resposta(200, caixa)).mockResolvedValueOnce(resposta(200, caixa)).mockRejectedValueOnce(new Error("x")) as unknown as typeof fetch & jest.Mock;
    await render(tela(f));
    await screen.findByTestId("resumo");
    await fireEvent.press(screen.getByTestId("atualizar"));
    await waitFor(() => expect(anuncio).toHaveBeenCalledWith("Caixa do dia atualizada."));
    expect(anuncio).toHaveBeenCalledWith("Atualizando...");
    await fireEvent.press(screen.getByTestId("atualizar"));
    await screen.findByText("Não foi possível atualizar. Você está vendo a caixa de antes.");
    expect(screen.getByTestId("resumo")).toBeTruthy();
    expect(screen.getByTestId("aluno-1")).toBeTruthy();
    anuncio.mockRestore();
  });

  it("o botão de atualizar tem rótulo e alvo de 44", async () => {
    await render(tela(fetchCom(200, caixa)));
    const b = await screen.findByTestId("atualizar");
    expect(b.props.accessibilityLabel).toBe("Atualizar a caixa do dia");
  });
});

describe("privacidade", () => {
  it("nada do corpo vai para o console", async () => {
    const espioes = (["log", "info", "warn", "error", "debug"] as const).map((m) => jest.spyOn(console, m).mockImplementation(() => {}));
    await render(tela(fetchCom(200, caixa)));
    await fireEvent.press(await screen.findByTestId("treino-501"));
    for (const e of espioes) {
      expect(JSON.stringify(e.mock.calls)).not.toContain("MARCADOR-OBS-123");
      expect(JSON.stringify(e.mock.calls)).not.toContain("Atleta Fixture");
      e.mockRestore();
    }
  });

  it("a mensagem de erro do cliente não carrega o corpo", async () => {
    const r = await buscarCaixaDoDia(7, { baseUrl: "http://api.teste", fetch: (async () => { throw new Error("MARCADOR-OBS-123"); }) as unknown as typeof fetch });
    expect(JSON.stringify(r)).not.toContain("MARCADOR-OBS-123");
  });
});

describe("dataDeHoje", () => {
  it("nome do dia e data curta", () => {
    expect(dataDeHoje("2025-11-13")).toBe("Quinta, 13/11/25");
    expect(dataDeHoje("2025-11-16")).toBe("Domingo, 16/11/25");
  });
});
