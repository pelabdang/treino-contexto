import type { Atividade } from "@treino/api-client";
import { StyleSheet } from "react-native";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react-native";

import { atividades } from "../__fixtures__/atividades";
import { cartoes as cartoesApi, emMovimento, estaSemana, hojeNaSemana, melhorMarca, volume4 } from "../__fixtures__/cartoes";
import { ORIGEM_AUTOMATICO } from "../src/componentes/CartaoFeedback";
import { TelaInicio } from "../src/componentes/TelaInicio";
import type { ItemTreino } from "../src/treinos/api";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));

const resposta = (status: number, corpo?: unknown) => ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const item = (id: number, extra: Partial<ItemTreino> = {}): ItemTreino => ({
  atividade_id: id,
  inicio: "2025-03-18T09:30:00Z",
  data_local: "2025-03-18",
  hora_local: "06:30",
  modalidade: "corrida",
  subtipo: "rua",
  tipo_treino: "leve",
  duracao_s: 3125,
  duracao: "0:52:05",
  distancia_m: 10000,
  distancia: "10,00 km",
  destaque: null,
  checkin_estado: "feito",
  feedback_estado: "pronto",
  normal_estado: "dentro", // a lista e o detalhe do mesmo treino concordam (normal_treino@1)
  ...extra,
});
const lista = (itens: ItemTreino[]) => ({ atleta_id: 1, limite: 5, itens, proximo: null });
const pend = (id: number, modalidade = "ciclismo") => ({ atividade_id: id, data_local: "2025-03-19", hora_local: "06:30", duracao: "0:52:10", modalidade, titulo: `Treino ${id}` });
const dia = (i: number, ctl: number, atl: number) => ({ data: `2025-03-${7 + i}`, ctl, atl, tsb: 0, carga: 0, atividades: 0, calculadas: 0, sem_carga: 0, aprendendo: false, ctl_texto: `${ctl}`, atl_texto: `${atl}` });
const quinzena = { atleta_id: 1, aviso: null, dias: [dia(0, 40, 50), dia(1, 44, 58)], frase_forma: { tipo: "acima", tendencia: "subiu", texto: "Frase da quinzena.", versao: "frase_forma@1" }, periodo: null, totais: {}, versao: "serie_carga@2", versao_carga: "carga@2" };
const comFeedback = (fb: unknown, extra: Partial<Atividade> = {}) => ({ ...atividades.ok, feedback: fb, ...extra }) as Atividade;
const feedbackPronto = { estado: "pronto", texto: "Linha 1\nLinha 2\nLinha 3\nLinha 4", origem: "automatico", checkin_aberto: false };

type Rotas = { cartoes?: unknown; lista?: unknown; atividade?: unknown; pendentes?: unknown; quinzena?: unknown; falhar?: string[] };
function servidor(r: Rotas = {}) {
  return jest.fn(async (input: RequestInfo | URL) => {
    const url = String(input).replace("http://api.teste", "");
    const quebra = (nome: string) => r.falhar?.includes(nome);
    if (url.includes("/checkins/pendentes")) return quebra("pendentes") ? resposta(500, {}) : resposta(200, r.pendentes ?? { dias: 7, pendentes: [], total: 0 });
    if (url.includes("/inicio/cartoes")) return quebra("cartoes") ? resposta(500, {}) : resposta(200, r.cartoes ?? { atleta_id: 1, data: "2025-03-21", cartoes: [] });
    if (url.includes("/carga")) return quebra("quinzena") ? resposta(500, {}) : resposta(200, r.quinzena ?? quinzena);
    if (/\/atividades\/\d+$/.test(url)) return quebra("atividade") ? resposta(500, {}) : resposta(200, r.atividade ?? comFeedback(feedbackPronto));
    return quebra("lista") ? resposta(500, {}) : resposta(200, r.lista ?? lista([item(1)]));
  }) as unknown as jest.Mock & typeof fetch;
}
const urls = (f: jest.Mock) => f.mock.calls.map((c) => String(c[0]).replace("http://api.teste", ""));

const props = () => ({ aoAbrirTreino: jest.fn(), aoResponderCheckin: jest.fn(), aoVerTodos: jest.fn() });
const tela = (f: typeof fetch, extra = {}) => <TelaInicio apiUrl="http://api.teste" atletaId={1} fetchFn={f} nome="Ana Souza" agora={() => new Date(2025, 2, 21)} {...props()} {...extra} />;

describe("início v3", () => {
  it("saudação com o primeiro nome e a data de hoje", async () => {
    await render(tela(servidor()));
    expect(screen.getByText("Olá, Ana")).toBeTruthy();
    expect(screen.getByTestId("data-hoje").props.children).toBe("sexta, 21/03");
    await screen.findByTestId("ultimo-treino");
  });

  it("busca a lista (5), o treino, os pendentes (7 dias) e a quinzena (ultimos=14)", async () => {
    const f = servidor();
    await render(tela(f));
    await screen.findByTestId("quinzena");
    await screen.findByTestId("numero-treino");
    const u = urls(f);
    expect(u).toContain("/atletas/1/atividades?limite=5");
    expect(u).toContain("/atletas/1/atividades/1");
    expect(u).toContain("/atletas/1/checkins/pendentes?dias=7");
    expect(u).toContain("/atletas/1/carga?ultimos=14");
  });

  it("cenário 2: número, apoio, selo de normal e as três primeiras linhas do feedback", async () => {
    const p = props();
    await render(tela(servidor(), p));
    await screen.findByTestId("feedback-resumo");
    expect(screen.getByTestId("numero-treino").props.children).toBe("5:12");
    expect(screen.getByText("10,00 km · 0:52:05 · FC média 152 bpm")).toBeTruthy();
    expect(screen.getByTestId("selo-normal-dentro")).toBeTruthy();
    expect(screen.getByText("Linha 1\nLinha 2\nLinha 3")).toBeTruthy();
    expect(screen.getByText(ORIGEM_AUTOMATICO)).toBeTruthy();
    expect(screen.queryByTestId("convite-checkin")).toBeNull();
    await fireEvent.press(screen.getByTestId("ler-feedback"));
    expect(p.aoAbrirTreino).toHaveBeenCalledWith(1);
  });

  it("o selo do normal segue o normal_estado da lista: o mesmo treino não muda de selo entre as telas", async () => {
    const base = atividades.ok.linha_base!;
    const detalhe = comFeedback(feedbackPronto, {
      linha_base: { ...base, metricas: [{ ...base.metricas[0], chave: "pace_medio", estado: "dentro" }, { ...base.metricas[1], chave: "fc_media", estado: "fora", diferenca_texto: "11 bpm acima" }] },
    } as Partial<Atividade>);
    await render(tela(servidor({ lista: lista([item(1, { normal_estado: "fora" })]), atividade: detalhe })));
    const selo = await screen.findByTestId("selo-normal-fora");
    expect(within(selo).getByText("Fora do seu normal: 11 bpm acima")).toBeTruthy();
    expect(screen.queryByTestId("selo-normal-dentro")).toBeNull();
  });

  it("cenário 1: sem check-in, o convite fica dentro do cartão e abre o check-in; mostra '+ N treinos'", async () => {
    const p = props();
    const f = servidor({
      lista: lista([item(1, { checkin_estado: "pendente", feedback_estado: "sem_checkin" })]),
      atividade: comFeedback({ estado: "sem_checkin", checkin_aberto: true, mensagem: "Faça o check-in para ver o feedback." }),
      pendentes: { dias: 7, pendentes: [pend(1, "corrida"), pend(2), pend(3)], total: 3 },
    });
    await render(tela(f, p));
    const convite = await screen.findByTestId("convite-checkin");
    expect(within(screen.getByTestId("ultimo-treino")).getByTestId("convite-checkin")).toBe(convite);
    expect(within(convite).getByText("Responda o check-in e receba o feedback deste treino.")).toBeTruthy();
    expect(screen.getByTestId("outros-sem-checkin").props.children).toBe("+ 2 treinos sem check-in");
    expect(screen.queryByTestId("faixa-outro-checkin")).toBeNull();
    await fireEvent.press(screen.getByTestId("responder-checkin"));
    expect(p.aoResponderCheckin).toHaveBeenCalledWith(1);
  });

  it("cenário 2 com outro treino sem check-in: faixa abaixo do cartão 'Como foi o ciclismo?'", async () => {
    const p = props();
    const f = servidor({ pendentes: { dias: 7, pendentes: [pend(2)], total: 1 } });
    await render(tela(f, p));
    const faixa = await screen.findByTestId("faixa-outro-checkin");
    expect(within(faixa).getByText("Como foi o ciclismo?")).toBeTruthy();
    expect(within(faixa).getByText("qua 19/03")).toBeTruthy();
    expect(screen.queryByTestId("convite-checkin")).toBeNull();
    await fireEvent.press(screen.getByTestId("responder-outro"));
    expect(p.aoResponderCheckin).toHaveBeenCalledWith(2);
  });

  it("feedback pendente: mostra a mensagem da API no lugar das linhas", async () => {
    const f = servidor({ atividade: comFeedback({ estado: "pendente", mensagem: "Ainda estamos preparando o feedback." }) });
    await render(tela(f));
    expect((await screen.findByTestId("feedback-estado")).props.children.props.children).toBe("Ainda estamos preparando o feedback.");
    expect(screen.queryByTestId("feedback-resumo")).toBeNull();
  });

  it("quinzena com a frase da API e treinos recentes (do 2º ao 5º) com 'Ver todos'", async () => {
    const p = props();
    const f = servidor({ lista: lista([item(1), item(2), item(3), item(4), item(5)]) });
    await render(tela(f, p));
    await screen.findByTestId("quinzena");
    expect(screen.getByTestId("frase-quinzena").props.children).toBe("Frase da quinzena.");
    const recentes = screen.getByTestId("recentes");
    for (const id of [2, 3, 4, 5]) expect(within(recentes).getByTestId(`treino-${id}`)).toBeTruthy();
    expect(within(recentes).queryByTestId("treino-1")).toBeNull();
    await fireEvent.press(within(recentes).getByTestId("treino-3"));
    expect(p.aoAbrirTreino).toHaveBeenCalledWith(3);
    await fireEvent.press(screen.getByTestId("ver-todos"));
    expect(p.aoVerTodos).toHaveBeenCalled();
  });

  it("um treino só: sem 'Treinos recentes'", async () => {
    await render(tela(servidor()));
    await screen.findByTestId("ultimo-treino");
    expect(screen.queryByTestId("recentes")).toBeNull();
  });

  it("sem treinos: frase e botão de enviar o arquivo", async () => {
    await render(tela(servidor({ lista: lista([]) })));
    await screen.findByTestId("estado-vazio");
    expect(screen.getByText("Nenhum treino ainda. Envie o arquivo do seu relógio e a análise aparece aqui.")).toBeTruthy();
    expect(screen.getByText("Enviar arquivo FIT")).toBeTruthy();
    expect(screen.queryByTestId("ultimo-treino")).toBeNull();
  });

  it("carregando: texto para leitor de tela", async () => {
    const f = jest.fn(() => new Promise<Response>(() => {})) as unknown as typeof fetch;
    await render(tela(f));
    expect(screen.getAllByText("Carregando").length).toBeGreaterThan(0);
  });

  it("cada cartão falha sozinho e 'Tentar de novo' busca de novo", async () => {
    let quinzenaFalha = true;
    const base = servidor();
    const f = jest.fn(async (input: RequestInfo | URL) => (String(input).includes("/carga") && quinzenaFalha ? resposta(500, {}) : base(input))) as unknown as typeof fetch;
    await render(tela(f));
    await screen.findByTestId("erro-quinzena");
    expect(screen.getByTestId("ultimo-treino")).toBeTruthy(); // o resto da tela segue
    quinzenaFalha = false;
    await fireEvent.press(screen.getByTestId("erro-quinzena-tentar"));
    await screen.findByTestId("quinzena");
    expect(screen.queryByTestId("erro-quinzena")).toBeNull();
  });

  it("erro na lista: mensagem do cartão", async () => {
    await render(tela(servidor({ falhar: ["lista"] })));
    expect(await screen.findByTestId("erro-ultimo")).toBeTruthy();
    expect(screen.queryByTestId("ultimo-treino")).toBeNull();
  });

  it("erro no detalhe: o cartão fica com o que a lista traz e avisa", async () => {
    await render(tela(servidor({ falhar: ["atividade"] })));
    expect(await screen.findByTestId("erro-detalhe")).toBeTruthy();
    expect(screen.getByTestId("numero-treino").props.children).toBe("0:52:05");
  });

  it("tocar no cartão do último treino abre o treino; o rótulo falado traz o número e o selo", async () => {
    const p = props();
    await render(tela(servidor(), p));
    const botao = await screen.findByTestId("abrir-ultimo-treino");
    await waitFor(() => expect(screen.getByTestId("abrir-ultimo-treino").props.accessibilityLabel).toContain("Dentro do seu normal"));
    expect(botao.props.accessibilityLabel).toContain("Pace médio, 5:12");
    await fireEvent.press(screen.getByTestId("abrir-ultimo-treino"));
    expect(p.aoAbrirTreino).toHaveBeenCalledWith(1);
  });
});

describe("início v4: Seus números", () => {
  const comNumeros = (extra = {}) => tela(servidor({ cartoes: cartoesApi }), { aoAbrirDestino: jest.fn(), ...extra });

  it("busca os cartões e mostra a seção entre a quinzena e os treinos recentes, na ordem da API", async () => {
    const f = servidor({ cartoes: cartoesApi, lista: lista([item(1), item(2)]) });
    await render(tela(f, { aoAbrirDestino: jest.fn() }));
    const secao = await screen.findByTestId("secao-numeros");
    expect(urls(f)).toContain("/atletas/1/inicio/cartoes");
    expect(within(secao).getByText("Seus números")).toBeTruthy();
    const ordem = within(secao).getAllByTestId(/^cartao-/).map((c) => c.props.testID);
    expect(ordem).toEqual(["cartao-esta_semana", "cartao-hoje_na_semana", "cartao-volume_4_semanas", "cartao-em_movimento", "cartao-melhor_marca"]);
    // celular: quinzena, depois "Seus números", depois os recentes
    const ids = JSON.stringify(screen.toJSON());
    expect(ids.indexOf('"quinzena"')).toBeLessThan(ids.indexOf('"secao-numeros"'));
    expect(ids.indexOf('"secao-numeros"')).toBeLessThan(ids.indexOf('"recentes"'));
  });

  it("os textos são os da API, sem recalcular", async () => {
    await render(comNumeros());
    const secao = await screen.findByTestId("secao-numeros");
    for (const t of ["3 treinos", "2 h 37 min · semana passada: 4", "Corrida leve", "da sua rotina", "21:10 · 5 km", "novo recorde · 12/03", "30 km por semana", emMovimento.texto as string]) {
      expect(within(secao).getByText(t)).toBeTruthy();
    }
  });

  it("pequenos em pares, o largo na linha toda e o pequeno sozinho ocupa a linha", async () => {
    await render(comNumeros());
    const linhas = await screen.findAllByTestId("linha-cartoes");
    expect(linhas.map((l) => within(l).getAllByTestId(/^cartao-/).length)).toEqual([2, 1, 1, 1]);
  });

  it("o cartão do volume tem 4 barras com valor e data, a mais recente em destaque", async () => {
    await render(comNumeros());
    const barras = within(await screen.findByTestId("barras-volume_4_semanas"));
    for (const t of ["40 km", "03/02", "25 km", "24/02"]) expect(barras.getByText(t)).toBeTruthy();
    expect(barras.getAllByText(/ km$/)).toHaveLength(4);
  });

  it("a altura de cada barra segue o altura_pct da API (o app só desenha)", async () => {
    await render(comNumeros());
    const barras = within(await screen.findByTestId("barras-volume_4_semanas"));
    const alturas = [0, 1, 2, 3].map((i) => StyleSheet.flatten(barras.getByTestId(`barra-altura-${i}`).props.style).height);
    expect(alturas).toEqual(["100%", "88%", "75%", "63%"]);
    expect(new Set(alturas).size).toBe(4); // não são mais todas iguais
  });

  it("cada cartão é um botão com o rótulo falado da API, e o toque abre o destino dele", async () => {
    const abrir = jest.fn();
    await render(comNumeros({ aoAbrirDestino: abrir }));
    await screen.findByTestId("secao-numeros");
    const c = screen.getByTestId("cartao-esta_semana");
    expect(c.props.accessibilityRole).toBe("button");
    expect(c.props.accessibilityLabel).toBe(estaSemana.rotulo_acessivel);
    await fireEvent.press(c);
    expect(abrir).toHaveBeenLastCalledWith(estaSemana.destino);
    await fireEvent.press(screen.getByTestId("cartao-hoje_na_semana"));
    expect(abrir).toHaveBeenLastCalledWith(hojeNaSemana.destino);
    await fireEvent.press(screen.getByTestId("cartao-volume_4_semanas"));
    expect(abrir).toHaveBeenLastCalledWith(volume4.destino);
    await fireEvent.press(screen.getByTestId("cartao-melhor_marca"));
    expect(abrir).toHaveBeenLastCalledWith(melhorMarca.destino);
  });

  it("só aparecem os cartões que a API mandou", async () => {
    await render(tela(servidor({ cartoes: { ...cartoesApi, cartoes: [melhorMarca] } }), { aoAbrirDestino: jest.fn() }));
    const secao = await screen.findByTestId("secao-numeros");
    expect(within(secao).getAllByTestId(/^cartao-/)).toHaveLength(1);
    expect(screen.queryByTestId("cartao-esta_semana")).toBeNull();
  });

  it("sem nenhum cartão, a seção e o título somem", async () => {
    await render(tela(servidor({ cartoes: { ...cartoesApi, cartoes: [] } }), { aoAbrirDestino: jest.fn() }));
    await screen.findByTestId("quinzena");
    await waitFor(() => expect(screen.queryByTestId("carregando-numeros")).toBeNull());
    expect(screen.queryByTestId("secao-numeros")).toBeNull();
    expect(screen.queryByText("Seus números")).toBeNull();
  });

  it("erro na busca dos cartões: a seção some em silêncio e o resto do início segue", async () => {
    await render(tela(servidor({ falhar: ["cartoes"] }), { aoAbrirDestino: jest.fn() }));
    await screen.findByTestId("quinzena");
    await waitFor(() => expect(screen.queryByTestId("carregando-numeros")).toBeNull());
    expect(screen.queryByTestId("secao-numeros")).toBeNull();
    expect(screen.queryByTestId("erro-ultimo")).toBeNull();
    expect(screen.queryByText("Não foi possível carregar.")).toBeNull();
  });

  it("carregando: esqueleto dos cartões, com o texto para o leitor de tela", async () => {
    const f = jest.fn((input: RequestInfo | URL) => (String(input).includes("/inicio/cartoes") ? new Promise<Response>(() => {}) : servidor()(input))) as unknown as typeof fetch;
    await render(tela(f, { aoAbrirDestino: jest.fn() }));
    expect(screen.getByText("Carregando seus números")).toBeTruthy();
    expect(screen.getByTestId("esqueleto-cartoes", { includeHiddenElements: true })).toBeTruthy();
  });

  it("sem treinos no app: o início vazio, sem cartões", async () => {
    await render(tela(servidor({ lista: lista([]) }), { aoAbrirDestino: jest.fn() }));
    await screen.findByTestId("estado-vazio");
    expect(screen.queryByTestId("secao-numeros")).toBeNull();
  });

  it("sem aoAbrirDestino a seção não aparece nem busca", async () => {
    const f = servidor({ cartoes: cartoesApi });
    await render(tela(f));
    await screen.findByTestId("quinzena");
    expect(screen.queryByTestId("secao-numeros")).toBeNull();
  });

  it("computador: 'Seus números' fica na coluna do último treino", async () => {
    jest.spyOn(require("react-native"), "useWindowDimensions").mockReturnValue({ width: 1280, height: 800, scale: 2, fontScale: 1 });
    try {
      await render(comNumeros());
      await screen.findByTestId("secao-numeros");
      const json = JSON.stringify(screen.toJSON());
      // coluna 1 = último treino e "Seus números"; coluna 2 = quinzena
      expect(json.indexOf('"ultimo-treino"')).toBeLessThan(json.indexOf('"secao-numeros"'));
      expect(json.indexOf('"secao-numeros"')).toBeLessThan(json.indexOf('"quinzena"'));
    } finally {
      jest.restoreAllMocks();
    }
  });
});
