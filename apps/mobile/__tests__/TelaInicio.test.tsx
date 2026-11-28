import { StyleSheet } from "react-native";
import { coresClaro } from "../src/tema/tokens";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react-native";

import { limparPerguntasProntas } from "../src/chat/prontas";
import { cartoes as cartoesApi } from "../__fixtures__/cartoes";
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
const dia = (i: number, ctl: number, atl: number) => ({ data: `2025-03-${7 + i}`, ctl, atl, tsb: 0, carga: 0, atividades: 0, calculadas: 0, sem_carga: 0, aprendendo: false, ctl_texto: `${ctl}`, atl_texto: `${atl}` });
const quinzena = { atleta_id: 1, aviso: null, dias: [dia(0, 40, 50), dia(1, 44, 58)], frase_forma: { tipo: "acima", tendencia: "subiu", texto: "Frase da quinzena.", versao: "frase_forma@1" }, periodo: null, totais: {}, versao: "serie_carga@2", versao_carga: "carga@2" };

type Rotas = { cartoes?: unknown; lista?: unknown; pendentes?: unknown; quinzena?: unknown; falhar?: string[] };
function servidor(r: Rotas = {}) {
  return jest.fn(async (input: RequestInfo | URL) => {
    const url = String(input).replace("http://api.teste", "");
    const quebra = (nome: string) => r.falhar?.includes(nome);
    if (url.includes("/checkins/pendentes")) return quebra("pendentes") ? resposta(500, {}) : resposta(200, r.pendentes ?? { dias: 7, pendentes: [], total: 0 });
    if (url.includes("/inicio/cartoes")) return quebra("cartoes") ? resposta(500, {}) : resposta(200, r.cartoes ?? { atleta_id: 1, data: "2025-03-21", cartoes: [] });
    if (url.includes("/carga")) return quebra("quinzena") ? resposta(500, {}) : resposta(200, r.quinzena ?? quinzena);
    return quebra("lista") ? resposta(500, {}) : resposta(200, r.lista ?? lista([item(1)]));
  }) as unknown as jest.Mock & typeof fetch;
}
const urls = (f: jest.Mock) => f.mock.calls.map((c) => String(c[0]).replace("http://api.teste", ""));


const pend = (id: number, modalidade = "natacao") => ({ atividade_id: id, data_local: "2025-03-20", hora_local: "07:00", duracao: "0:45:12", modalidade, titulo: `Treino ${id}`, pergunta_texto: modalidade === "natacao" ? "Como foi a natação de ontem?" : "Como foi o treino de terça?" });
const comPendentes = (...p: ReturnType<typeof pend>[]) => ({ dias: 7, pendentes: p, total: p.length });
const props = () => ({ aoAbrirTreino: jest.fn(), aoResponderCheckin: jest.fn(), aoVerTodos: jest.fn() });
const chat = () => ({ aoAbrirChat: jest.fn(), aoPerguntar: jest.fn(), aoAbrirConversas: jest.fn() });
const tela = (f: typeof fetch, extra = {}) => <TelaInicio apiUrl="http://api.teste" atletaId={1} fetchFn={f} nome="Ana Souza" agora={() => new Date(2025, 2, 21)} {...props()} {...extra} />;

describe("início v5: com check-in pendente", () => {
  it("o cartão grande abre o check-in do treino, mostra o treino e '+ N treinos sem check-in'", async () => {
    const p = props();
    const f = servidor({ pendentes: comPendentes(pend(7), pend(8, "ciclismo"), pend(9, "corrida")), cartoes: cartoesApi });
    await render(tela(f, { ...p, aoVerPendentes: jest.fn(), aoAbrirDestino: jest.fn() }));
    const cartao = await screen.findByTestId("checkin-grande");
    expect(within(cartao).getByText("Como foi a natação de ontem?")).toBeTruthy();
    expect(within(cartao).getByText("Natação · qui 20/03 · 07:00 · 0:45:12")).toBeTruthy();
    expect(within(cartao).getByText("3 perguntas, uns 30 segundos. Você recebe o feedback deste treino.")).toBeTruthy();
    expect(within(cartao).getByText("+ 2 treinos sem check-in ›")).toBeTruthy();
    await fireEvent.press(within(cartao).getByTestId("responder-checkin"));
    expect(p.aoResponderCheckin).toHaveBeenCalledWith(7);
  });

  it("'+ N' abre a lista de pendentes", async () => {
    const aoVerPendentes = jest.fn();
    await render(tela(servidor({ pendentes: comPendentes(pend(7), pend(8)) }), { aoVerPendentes }));
    await fireEvent.press(await screen.findByTestId("outros-sem-checkin"));
    expect(aoVerPendentes).toHaveBeenCalled();
  });

  it("a pergunta do cartão é a da API (pergunta_texto), sem montar frase no app", async () => {
    await render(tela(servidor({ pendentes: comPendentes({ ...pend(7), pergunta_texto: "Como foi a corrida de terça?" }) })));
    const cartao = await screen.findByTestId("checkin-grande");
    expect(within(cartao).getByText("Como foi a corrida de terça?")).toBeTruthy();
  });

  it("'Esta semana' encolhe para uma linha, e 'hoje e último treino' e 'Check-ins em dia' não aparecem", async () => {
    await render(tela(servidor({ pendentes: comPendentes(pend(7)), cartoes: cartoesApi }), { aoAbrirDestino: jest.fn() }));
    await screen.findByTestId("checkin-grande");
    expect(await screen.findByTestId("semana-linha")).toBeTruthy();
    expect(screen.getByText("3 treinos · 2 h 37 min")).toBeTruthy();
    expect(screen.queryByTestId("semana-valor")).toBeNull();
    expect(screen.queryByTestId("hoje-e-ultimo")).toBeNull();
    expect(screen.queryByTestId("checkins-em-dia")).toBeNull();
  });
});

describe("início v5: atleta sem treinos", () => {
  it("não mostra cartão de check-in nem '+ N treinos', mesmo que os pendentes venham", async () => {
    await render(tela(servidor({ lista: lista([]), pendentes: comPendentes(pend(7), pend(8)) })));
    await screen.findByTestId("estado-vazio");
    expect(screen.queryByTestId("checkin-grande")).toBeNull();
    expect(screen.queryByText(/sem check-in/)).toBeNull();
  });
});

describe("início v5: os 7 dias da semana (dias[] da API)", () => {
  const semana = (extra = {}) => tela(servidor({ cartoes: cartoesApi }), { aoAbrirDestino: jest.fn(), ...extra });

  it("desenha os 7 dias na ordem da API, com o rótulo falado de cada um", async () => {
    await render(semana());
    const dias = await screen.findByTestId("semana-dias");
    expect(within(dias).getAllByTestId(/^dia-[^-]+$/).map((d) => d.props.testID)).toEqual(["dia-seg", "dia-ter", "dia-qua", "dia-qui", "dia-sex", "dia-sáb", "dia-dom"]);
    expect(within(dias).getByTestId("dia-qui").props.accessibilityLabel).toBe("Quinta, natação");
    expect(within(dias).getByTestId("dia-sex").props.accessibilityLabel).toBe("Sexta, hoje, sem treino ainda");
  });

  it("✓ nos dias feitos, na cor da modalidade (corrida, ciclismo, natação); hoje, vazio e futuro sem ✓ (círculo cinza)", async () => {
    await render(semana());
    const dias = await screen.findByTestId("semana-dias");
    const cor = (id: string) => StyleSheet.flatten(within(dias).getByTestId(id).props.style).backgroundColor;
    expect(cor("dia-ter-feito")).toBe(coresClaro.corrida);
    expect(cor("dia-qua-feito")).toBe(coresClaro.ciclismo);
    expect(cor("dia-qui-feito")).toBe(coresClaro.natacao);
    expect(within(dias).queryByTestId("dia-seg-feito")).toBeNull();
    expect(within(dias).queryByTestId("dia-sex-feito")).toBeNull();
    expect(within(dias).getByTestId("dia-seg-vazio")).toBeTruthy();
    expect(within(dias).getByTestId("dia-sex-hoje")).toBeTruthy();
    expect(within(dias).getByTestId("dia-sáb-futuro")).toBeTruthy();
    expect(StyleSheet.flatten(within(dias).getByTestId("dia-seg-vazio").props.style)).toMatchObject({ width: 26, height: 26, backgroundColor: coresClaro.borda });
    expect(StyleSheet.flatten(within(dias).getByTestId("dia-ter-feito").props.style)).toMatchObject({ width: 26, height: 26 });
    // os rótulos dos 7 dias são todos da mesma cor (texto-2), inclusive os futuros
    const rotulo = (r: string) => StyleSheet.flatten(within(within(dias).getByTestId(`dia-${r}`)).getByText(r).props.style).color;
    expect(new Set(["seg", "ter", "qua", "qui", "sex", "sáb", "dom"].map(rotulo))).toEqual(new Set([coresClaro["texto-2"]]));
  });

  it("os dias aparecem com pendência (linha) e sem pendência (herói)", async () => {
    await render(tela(servidor({ pendentes: comPendentes(pend(7)), cartoes: cartoesApi }), { aoAbrirDestino: jest.fn() }));
    expect(await screen.findByTestId("semana-dias")).toBeTruthy();
    expect(screen.getByTestId("semana-linha")).toBeTruthy();
  });

  it("sem dias[] (API antiga): o bloco segue sem a fileira", async () => {
    const semDias = { ...cartoesApi, cartoes: cartoesApi.cartoes.map((c) => ({ ...c, dias: [] })) };
    await render(tela(servidor({ cartoes: semDias }), { aoAbrirDestino: jest.fn() }));
    await screen.findByTestId("bloco-semana");
    expect(screen.queryByTestId("semana-dias")).toBeNull();
  });

  it("o herói mostra apoio_curto e comparacao_texto da API", async () => {
    await render(semana());
    expect(await screen.findByText("2 h 37 min · semana passada: 4")).toBeTruthy();
  });
});

describe("início v5: sem pendência (check-ins em dia)", () => {
  const emDia = (extra = {}) => tela(servidor({ cartoes: cartoesApi, lista: lista([item(1), item(2)]) }), { aoAbrirDestino: jest.fn(), ...chat(), ...extra });

  it("sem cartão de check-in; 'Esta semana' é o herói com os textos da API", async () => {
    await render(emDia());
    expect(await screen.findByTestId("semana-valor")).toBeTruthy();
    expect(screen.getByText("3 treinos")).toBeTruthy();
    expect(screen.getByText("2 h 37 min · semana passada: 4")).toBeTruthy();
    expect(screen.queryByTestId("checkin-grande")).toBeNull();
  });

  it("mostra '✓ Check-ins em dia' com 'Ver feedback ›', que abre o último treino", async () => {
    const p = props();
    await render(emDia(p));
    expect(await screen.findByText("✓ Check-ins em dia")).toBeTruthy();
    await fireEvent.press(screen.getByTestId("ver-feedback"));
    expect(p.aoAbrirTreino).toHaveBeenCalledWith(1);
  });

  it("hoje e último treino em par; o último treino mostra a duração e 'Natação · data' prontas da lista", async () => {
    const p = props();
    await render(emDia(p));
    const par = await screen.findByTestId("hoje-e-ultimo");
    expect(within(par).getByText("Corrida leve")).toBeTruthy();
    expect(within(par).getByText("da sua rotina")).toBeTruthy();
    expect(within(par).getByTestId("numero-treino").props.children).toBe("0:52:05");
    expect(within(par).getByText("Corrida · ter 18/03")).toBeTruthy();
    await fireEvent.press(within(par).getByTestId("abrir-ultimo-treino"));
    expect(p.aoAbrirTreino).toHaveBeenCalledWith(1);
  });

  it("'Seus números' fica abaixo e não repete 'Esta semana' nem 'Hoje'", async () => {
    await render(emDia());
    const secao = await screen.findByTestId("secao-numeros");
    expect(within(secao).queryByTestId("cartao-esta_semana")).toBeNull();
    expect(within(secao).queryByTestId("cartao-hoje_na_semana")).toBeNull();
    expect(within(secao).getAllByTestId(/^cartao-/).map((c) => c.props.testID)).toEqual(["cartao-volume_4_semanas", "cartao-em_movimento", "cartao-melhor_marca"]);
    const ids = JSON.stringify(screen.toJSON());
    expect(ids.indexOf('"semana-valor"')).toBeLessThan(ids.indexOf('"chat-no-inicio"'));
    expect(ids.indexOf('"hoje-e-ultimo"')).toBeLessThan(ids.indexOf('"quinzena"'));
    expect(ids.indexOf('"quinzena"')).toBeLessThan(ids.indexOf('"secao-numeros"'));
    expect(ids.indexOf('"secao-numeros"')).toBeLessThan(ids.indexOf('"recentes"'));
  });

  it("'Esta semana' abre o destino do cartão", async () => {
    const aoAbrirDestino = jest.fn();
    await render(emDia({ aoAbrirDestino }));
    await fireEvent.press(await screen.findByTestId("bloco-semana"));
    expect(aoAbrirDestino).toHaveBeenCalledWith(cartoesApi.cartoes[0].destino);
  });

  it("falha nos pendentes: nem o cartão de check-in nem 'Check-ins em dia' (não se afirma o que não se sabe)", async () => {
    await render(tela(servidor({ falhar: ["pendentes"] })));
    await screen.findByTestId("tela-inicio");
    await waitFor(() => expect(screen.queryByText("Carregando")).toBeNull());
    expect(screen.queryByTestId("checkin-grande")).toBeNull();
    expect(screen.queryByTestId("checkins-em-dia")).toBeNull();
  });
});

describe("início v5: o chat", () => {
  it("título, 'Conversas ›', caixa, ↑ e as 3 primeiras perguntas prontas", async () => {
    const c = chat();
    await render(tela(servidor(), c));
    const bloco = await screen.findByTestId("chat-no-inicio");
    expect(within(bloco).getByText("Pergunte ao seu treino")).toBeTruthy();
    expect(within(bloco).getByText("Ex.: como foi minha semana?")).toBeTruthy();
    expect(within(bloco).getAllByTestId(/^inicio-pronta-/)).toHaveLength(3);
    expect(within(bloco).getByText("Quanto corri neste mês?")).toBeTruthy();
    expect(within(bloco).queryByText("Como estão minha carga e minha forma?")).toBeNull();
    await fireEvent.press(within(bloco).getByTestId("inicio-conversas"));
    expect(c.aoAbrirConversas).toHaveBeenCalled();
    await fireEvent.press(within(bloco).getByTestId("inicio-caixa"));
    await fireEvent.press(within(bloco).getByTestId("inicio-enviar"));
    expect(c.aoAbrirChat).toHaveBeenCalledTimes(2);
  });

  it("tocar numa pergunta pronta manda o índice dela", async () => {
    const c = chat();
    await render(tela(servidor(), c));
    await fireEvent.press(await screen.findByTestId("inicio-pronta-1"));
    expect(c.aoPerguntar).toHaveBeenCalledWith(1);
  });

  it("sem os callbacks do chat o bloco não aparece; sem treinos some a fileira, mas a caixa fica", async () => {
    const { unmount } = await render(tela(servidor()));
    await screen.findByTestId("tela-inicio");
    expect(screen.queryByTestId("chat-no-inicio")).toBeNull();
    await unmount();
    await render(tela(servidor({ lista: lista([]) }), chat()));
    await screen.findByTestId("estado-vazio");
    expect(screen.getByTestId("inicio-caixa")).toBeTruthy();
    expect(screen.queryByTestId("inicio-prontas")).toBeNull();
  });
});

describe("início v5: perguntas prontas da API", () => {
  beforeEach(() => limparPerguntasProntas());
  const comProntas = (perguntas: string[] | "erro" | "pendurada") => {
    const base = servidor();
    return jest.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes("/chat/perguntas-prontas")) {
        if (perguntas === "pendurada") return new Promise<Response>(() => {});
        return perguntas === "erro" ? resposta(500, {}) : resposta(200, { atleta_id: 1, versao: "v1", perguntas });
      }
      return (base as unknown as (i: RequestInfo | URL) => Promise<Response>)(input);
    }) as unknown as typeof fetch;
  };

  it("mostra as 3 primeiras da API", async () => {
    await render(tela(comProntas(["A?", "B?", "C?", "D?", "E?"]), chat()));
    const bloco = await screen.findByTestId("chat-no-inicio");
    await within(bloco).findByText("A?");
    expect(within(bloco).getAllByTestId(/^inicio-pronta-/)).toHaveLength(3);
    expect(within(bloco).queryByText("D?")).toBeNull();
  });

  it("carregando: 3 esqueletos e o texto para o leitor de tela; a caixa já funciona", async () => {
    const c = chat();
    await render(tela(comProntas("pendurada"), c));
    const bloco = await screen.findByTestId("chat-no-inicio");
    expect(within(bloco).getByText("Carregando perguntas sugeridas")).toBeTruthy();
    expect(within(bloco).queryByTestId("inicio-pronta-0")).toBeNull();
    await fireEvent.press(within(bloco).getByTestId("inicio-caixa"));
    expect(c.aoAbrirChat).toHaveBeenCalled();
  });

  it("erro na rota: as fixas, sem aviso", async () => {
    await render(tela(comProntas("erro"), chat()));
    expect(await screen.findByText("Como foi minha semana?")).toBeTruthy();
    expect(screen.queryByText(/perguntas sugeridas/)).toBeNull();
  });
});

describe("início v5: professor (Meta 15)", () => {
  it("fica fora enquanto a API não manda o dado (constante desligada)", async () => {
    await render(tela(servidor(), { professor: { texto: "Carlos vê seus treinos e check-ins", aoAbrir: jest.fn() } }));
    await screen.findByTestId("tela-inicio");
    expect(screen.queryByTestId("linha-professor")).toBeNull();
  });
});

describe("início v5: o que já valia", () => {
  it("saudação com o primeiro nome e a data de hoje", async () => {
    await render(tela(servidor()));
    expect(await screen.findByText("Olá, Ana")).toBeTruthy();
    expect(screen.getByTestId("data-hoje").props.children).toBe("sexta, 21/03");
  });

  it("busca a lista (5), os pendentes (7 dias), a quinzena (ultimos=14) e os cartões", async () => {
    const f = servidor();
    await render(tela(f, { aoAbrirDestino: jest.fn() }));
    await screen.findByTestId("tela-inicio");
    await waitFor(() => expect(urls(f).length).toBeGreaterThanOrEqual(4));
    expect(urls(f)).toEqual(expect.arrayContaining(["/atletas/1/atividades?limite=5", "/atletas/1/checkins/pendentes?dias=7", "/atletas/1/carga?ultimos=14", "/atletas/1/inicio/cartoes"]));
  });

  it("quinzena com a frase da API e treinos recentes (do 2º ao 5º) com 'Ver todos'", async () => {
    const p = props();
    await render(tela(servidor({ lista: lista([item(1), item(2), item(3), item(4), item(5)]) }), p));
    expect(await screen.findByText("Frase da quinzena.")).toBeTruthy();
    expect(within(screen.getByTestId("recentes")).getAllByTestId(/^treino-/)).toHaveLength(4);
    await fireEvent.press(screen.getByTestId("ver-todos"));
    expect(p.aoVerTodos).toHaveBeenCalled();
  });

  it("um treino só: sem 'Treinos recentes'", async () => {
    await render(tela(servidor()));
    await screen.findByTestId("tela-inicio");
    expect(screen.queryByTestId("recentes")).toBeNull();
  });

  it("sem treinos: frase e botão de enviar o arquivo", async () => {
    await render(tela(servidor({ lista: lista([]) })));
    expect(await screen.findByText("Nenhum treino ainda. Envie o arquivo do seu relógio e a análise aparece aqui.")).toBeTruthy();
    expect(screen.getByText("Enviar arquivo FIT")).toBeTruthy();
  });

  it("carregando: texto para leitor de tela", async () => {
    const f = jest.fn(() => new Promise<Response>(() => {})) as unknown as typeof fetch;
    await render(tela(f));
    expect(screen.getAllByText("Carregando").length).toBeGreaterThan(0);
  });

  it("cada bloco falha sozinho e 'Tentar de novo' busca de novo", async () => {
    const f = servidor({ falhar: ["lista", "quinzena"] });
    await render(tela(f));
    expect(await screen.findByTestId("erro-ultimo")).toBeTruthy();
    expect(screen.getByTestId("erro-quinzena")).toBeTruthy();
    await fireEvent.press(screen.getByTestId("erro-quinzena-tentar"));
    await waitFor(() => expect(urls(f).filter((u) => u.includes("/carga")).length).toBe(2));
  });

  it("erro na busca dos cartões: 'Esta semana' e 'Seus números' somem em silêncio", async () => {
    await render(tela(servidor({ falhar: ["cartoes"] }), { aoAbrirDestino: jest.fn() }));
    await screen.findByTestId("tela-inicio");
    await waitFor(() => expect(screen.queryByTestId("carregando-numeros")).toBeNull());
    expect(screen.queryByTestId("bloco-semana")).toBeNull();
    expect(screen.queryByTestId("secao-numeros")).toBeNull();
  });

  it("sem aoAbrirDestino não há 'Esta semana' nem 'Seus números'", async () => {
    const f = servidor({ cartoes: cartoesApi });
    await render(tela(f));
    await screen.findByTestId("tela-inicio");
    expect(screen.queryByTestId("bloco-semana")).toBeNull();
    expect(screen.queryByTestId("secao-numeros")).toBeNull();
    expect(urls(f)).toContain("/atletas/1/inicio/cartoes");
  });
});
