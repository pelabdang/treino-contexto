import { ComSessao } from "../__fixtures__/sessaoFalsa";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react-native";

import { catalogo, fetchEvolucao, paceLeve, serieAprendendo, serieCatalogo, serieVazia, volumeSemana } from "../__fixtures__/evolucao";
import Inicio from "../src/app/(app)/(abas)/evolucao"; // a Evolução mora na aba Evolução (o início é a TelaInicio)
import { TelaEvolucao } from "../src/componentes/TelaEvolucao";

// Os ícones carregam a fonte de forma assíncrona (não existe no Jest): vira um texto com o nome e o tamanho.
jest.mock("@expo/vector-icons", () => {
  const { Text } = require("react-native");
  return { MaterialIcons: ({ name, size }: { name: string; size: number }) => <Text testID={`icone-${name}`}>{`${name}:${size}`}</Text> };
});

const mockPush = jest.fn();
jest.mock("expo-router", () => ({
  useFocusEffect: (cb: () => void) => require("react").useEffect(cb, [cb]),
  useLocalSearchParams: () => ({}),
  router: { push: (...a: unknown[]) => mockPush(...a) },
}));

// A última série escolhida fica no aparelho: aqui, uma memória por teste.
const mockMemoria = new Map<string, string>();
jest.mock("../src/sessao/armazenamento", () => ({
  lerUltimaSerie: async (id: number) => mockMemoria.get(String(id)) ?? null,
  gravarUltimaSerie: async (id: number, serie: string) => void mockMemoria.set(String(id), serie),
}));

const resposta = (status: number, corpo: unknown) => ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const tela = (f: typeof fetch, extra = {}) => <TelaEvolucao apiUrl="http://api.teste" atletaId={1} fetchFn={f} {...extra} />;
// O texto desenhado dentro do SVG (rótulos do eixo, da faixa e das datas) não é um `Text` do RN: procura na árvore.
const noGrafico = (texto: string) => JSON.stringify(screen.toJSON()).includes(`"${texto}"`);
const urls = (f: jest.Mock) => f.mock.calls.map((c) => String(c[0]));

const larguraTela = (width: number) =>
  jest.spyOn(require("react-native"), "useWindowDimensions").mockReturnValue({ width, height: 800, scale: 2, fontScale: 1 });

beforeEach(() => {
  mockMemoria.clear();
  mockPush.mockReset();
  larguraTela(360); // celular por padrão
});
afterEach(() => jest.restoreAllMocks());

describe("Evolução v1: abertura e série padrão", () => {
  it("título, catálogo e a série_padrao no 12 semanas (rota da aba)", async () => {
    const original = globalThis.fetch;
    const f = fetchEvolucao();
    globalThis.fetch = f;
    try {
      await render(<ComSessao><Inicio /></ComSessao>);
      expect(screen.getByText("Evolução")).toBeTruthy();
      await screen.findByTestId("frase-evolucao");
    } finally {
      globalThis.fetch = original;
    }
    expect(urls(f)).toContain("http://api.teste/atletas/1/evolucao/series");
    expect(urls(f)).toContain("http://api.teste/atletas/1/evolucao/series/corrida.pace.leve?periodo=12s");
  });

  it("carregando: esqueleto e o texto para o leitor de tela", async () => {
    await render(tela(jest.fn(() => new Promise<Response>(() => {})) as unknown as typeof fetch));
    expect(screen.getByText("Carregando...")).toBeTruthy();
    expect(screen.getByTestId("esqueleto-evolucao", { includeHiddenElements: true })).toBeTruthy();
  });

  it("mostra a frase, o valor do último treino e o rodapé, tudo como a API mandou", async () => {
    await render(tela(fetchEvolucao()));
    const frase = await screen.findByTestId("frase-evolucao");
    expect(within(frase).getByText("EM UMA FRASE")).toBeTruthy();
    expect(within(frase).getByText(paceLeve.frase.texto)).toBeTruthy();
    expect(screen.getByText("5:43")).toBeTruthy();
    expect(screen.getByText("último treino, qui 14/03")).toBeTruthy();
    expect(screen.getByText("cálculo: evolucao_serie@1")).toBeTruthy();
    // o gráfico é um item só, com a frase como rótulo
    expect(screen.getByLabelText(paceLeve.frase.texto).props.accessible).toBe(true);
  });

  it("abre na última série escolhida (guardada no aparelho), não na padrão", async () => {
    mockMemoria.set("1", "corrida.volume_km");
    const f = fetchEvolucao();
    await render(tela(f));
    await screen.findByTestId("frase-evolucao");
    expect(urls(f)).toContain("http://api.teste/atletas/1/evolucao/series/corrida.volume_km?periodo=12s");
    expect(urls(f).some((u) => u.includes("pace.leve"))).toBe(false);
  });

  it("a série guardada que sumiu do catálogo, ou ficou indisponível, cai na padrão", async () => {
    mockMemoria.set("1", "corrida.tiros"); // indisponível
    const f = fetchEvolucao();
    await render(tela(f));
    await screen.findByTestId("frase-evolucao");
    expect(urls(f)).toContain("http://api.teste/atletas/1/evolucao/series/corrida.pace.leve?periodo=12s");
  });

  it("sem série_padrao, abre na primeira disponível", async () => {
    const f = fetchEvolucao({ catalogo: { ...catalogo, serie_padrao: null } });
    await render(tela(f));
    await screen.findByTestId("frase-evolucao");
    expect(urls(f)).toContain("http://api.teste/atletas/1/evolucao/series/corrida.pace.leve?periodo=12s");
  });
});

describe("Evolução v1: seletor em dois passos", () => {
  it("a modalidade vem primeiro; só aparecem as que têm série", async () => {
    await render(tela(fetchEvolucao()));
    await screen.findByTestId("frase-evolucao");
    expect(screen.getByTestId("modalidade-corrida").props.accessibilityState.selected).toBe(true);
    expect(screen.getByTestId("modalidade-natacao")).toBeTruthy();
    expect(screen.queryByTestId("modalidade-ciclismo")).toBeNull();
  });

  it("a folha lista as séries em grupos; a indisponível vem com o motivo escrito", async () => {
    await render(tela(fetchEvolucao()));
    await screen.findByTestId("frase-evolucao");
    await fireEvent.press(screen.getByTestId("abrir-seletor"));
    const folha = within(screen.getByTestId("folha-series"));
    expect(folha.getByText("Corrida: o que acompanhar")).toBeTruthy();
    for (const g of ["Ritmo", "Coração", "Esforço e volume"]) expect(folha.getByText(g)).toBeTruthy();
    expect(folha.getByText("Poucos treinos de tiros nas últimas 12 semanas")).toBeTruthy();
    const marcada = folha.getByTestId("serie-corrida.pace.leve");
    expect(marcada.props.accessibilityState.selected).toBe(true);
    expect(folha.getByTestId("serie-corrida.tiros").props.accessibilityLabel).toContain("Indisponível");
  });

  it("escolher uma série fecha a folha, busca a série e lembra a escolha", async () => {
    const f = fetchEvolucao();
    await render(tela(f));
    await screen.findByTestId("frase-evolucao");
    await fireEvent.press(screen.getByTestId("abrir-seletor"));
    await fireEvent.press(screen.getByTestId("serie-corrida.volume_km"));
    await waitFor(() => expect(screen.getByText(volumeSemana.frase.texto)).toBeTruthy());
    expect(screen.queryByTestId("folha-series")).toBeNull();
    expect(urls(f)).toContain("http://api.teste/atletas/1/evolucao/series/corrida.volume_km?periodo=12s");
    expect(mockMemoria.get("1")).toBe("corrida.volume_km");
  });

  it("trocar de modalidade vai para a primeira série disponível dela e mantém o período", async () => {
    const f = fetchEvolucao({ series: { "corrida.pace.leve": paceLeve, "natacao.ritmo": { ...paceLeve, id: "natacao.ritmo", titulo: "Ritmo na piscina" } } });
    await render(tela(f));
    await screen.findByTestId("frase-evolucao");
    await fireEvent.press(screen.getByTestId("periodo-6m"));
    await fireEvent.press(screen.getByTestId("modalidade-natacao"));
    await waitFor(() => expect(urls(f)).toContain("http://api.teste/atletas/1/evolucao/series/natacao.ritmo?periodo=6m"));
  });

  it("série indisponível escolhida: mostra o motivo e 'Escolher outra série', sem buscar a série", async () => {
    const f = fetchEvolucao();
    await render(tela(f));
    await screen.findByTestId("frase-evolucao");
    await fireEvent.press(screen.getByTestId("abrir-seletor"));
    await fireEvent.press(screen.getByTestId("serie-corrida.tiros"));
    const vazio = await screen.findByTestId("serie-indisponivel");
    expect(within(vazio).getByText("Poucos treinos de tiros nas últimas 12 semanas")).toBeTruthy();
    expect(urls(f).some((u) => u.includes("corrida.tiros"))).toBe(false);
    await fireEvent.press(within(vazio).getByTestId("escolher-outra"));
    expect(screen.getByTestId("folha-series")).toBeTruthy();
  });

  it("computador (≥ 900): as séries ficam numa coluna fixa, sem folha", async () => {
    larguraTela(1280);
    await render(tela(fetchEvolucao()));
    await screen.findByTestId("frase-evolucao");
    expect(screen.getByTestId("coluna-series")).toBeTruthy();
    expect(screen.queryByTestId("abrir-seletor")).toBeNull();
    await fireEvent.press(screen.getByTestId("serie-corrida.volume_km"));
    await waitFor(() => expect(screen.getByText(volumeSemana.frase.texto)).toBeTruthy());
  });
});

describe("Evolução v1: série pedida pelo cartão do início", () => {
  it("com a tela aberta, um novo pedido troca de série uma vez e não grava como escolha do atleta", async () => {
    const f = fetchEvolucao();
    const { rerender } = await render(tela(f));
    await screen.findByTestId("frase-evolucao");
    await rerender(tela(f, { serieInicial: "corrida.volume_km" }));
    await waitFor(() => expect(screen.getByText(volumeSemana.frase.texto)).toBeTruthy());
    expect(urls(f)).toContain("http://api.teste/atletas/1/evolucao/series/corrida.volume_km?periodo=12s");
    expect(mockMemoria.has("1")).toBe(false);
    // o atleta escolhe outra série: o mesmo pedido não volta a valer
    await fireEvent.press(screen.getByTestId("abrir-seletor"));
    await fireEvent.press(screen.getByTestId("serie-corrida.pace.leve"));
    await waitFor(() => expect(screen.getByText(paceLeve.frase.texto)).toBeTruthy());
  });

  it("série pedida indisponível: mostra o motivo, sem buscar a série", async () => {
    const f = fetchEvolucao();
    await render(tela(f, { serieInicial: "corrida.tiros" }));
    const vazio = await screen.findByTestId("serie-indisponivel");
    expect(within(vazio).getByText("Poucos treinos de tiros nas últimas 12 semanas")).toBeTruthy();
    expect(urls(f).some((u) => u.includes("corrida.tiros"))).toBe(false);
  });
});

describe("Evolução v1: período", () => {
  it("12 semanas, 6 meses e 1 ano buscam a série de novo; o mesmo período não busca", async () => {
    const f = fetchEvolucao();
    await render(tela(f));
    await screen.findByTestId("frase-evolucao");
    expect(screen.getByTestId("periodo-12s").props.accessibilityState.selected).toBe(true);
    const antes = f.mock.calls.length;
    await fireEvent.press(screen.getByTestId("periodo-12s"));
    expect(f.mock.calls.length).toBe(antes);
    await fireEvent.press(screen.getByTestId("periodo-6m"));
    await waitFor(() => expect(urls(f)).toContain("http://api.teste/atletas/1/evolucao/series/corrida.pace.leve?periodo=6m"));
    await fireEvent.press(screen.getByTestId("periodo-1a"));
    await waitFor(() => expect(urls(f)).toContain("http://api.teste/atletas/1/evolucao/series/corrida.pace.leve?periodo=1a"));
    await screen.findByTestId("frase-evolucao");
  });
});

describe("Evolução v1: o gráfico", () => {
  it("desenha a faixa do normal, o losango do melhor e o triângulo do fora do normal", async () => {
    await render(tela(fetchEvolucao()));
    await screen.findByTestId("grafico-serie");
    expect(screen.getByTestId("faixa-normal")).toBeTruthy();
    expect(noGrafico("Seu normal 5:35 a 5:50")).toBe(true);
    expect(screen.getByTestId("marca-melhor")).toBeTruthy();
    expect(screen.getByTestId("marca-fora")).toBeTruthy();
    expect(screen.getByTestId("linha-serie")).toBeTruthy();
    // legenda sempre visível
    for (const t of ["treino", "fora do normal", "melhor", "normal"]) expect(screen.getByText(t, { includeHiddenElements: true })).toBeTruthy();
  });

  it("pace (eixo invertido) diz 'mais rápido ↑'; volume não", async () => {
    const { unmount } = await render(tela(fetchEvolucao()));
    expect(await screen.findByTestId("mais-rapido")).toHaveTextContent("mais rápido ↑");
    await unmount();
    mockMemoria.set("1", "corrida.volume_km");
    await render(tela(fetchEvolucao()));
    await screen.findByTestId("grafico-serie");
    expect(screen.queryByTestId("mais-rapido")).toBeNull();
  });

  it("legenda da série de barras: só 'semana'", async () => {
    mockMemoria.set("1", "corrida.volume_km");
    await render(tela(fetchEvolucao()));
    await screen.findByTestId("grafico-serie");
    expect(screen.getByText("semana", { includeHiddenElements: true })).toBeTruthy();
    for (const t of ["treino", "fora do normal", "melhor"]) expect(screen.queryByText(t, { includeHiddenElements: true })).toBeNull();
  });

  it("os marcos do eixo são os textos da API", async () => {
    await render(tela(fetchEvolucao()));
    await screen.findByTestId("grafico-serie");
    for (const t of ["5:30", "5:42", "5:55"]) expect(noGrafico(t)).toBe(true);
  });

  it("o app não recalcula: valor_texto trocado aparece como veio", async () => {
    const serie = { ...paceLeve, ultimo_valor_texto: "9:99", pontos: paceLeve.pontos.map((p, i) => (i === 3 ? { ...p, valor_texto: "9:99" } : p)) };
    await render(tela(fetchEvolucao({ series: { "corrida.pace.leve": serie } })));
    await screen.findByTestId("grafico-serie");
    expect(screen.getByText("9:99")).toBeTruthy();
    await fireEvent.press(screen.getByTestId("ponto-3"));
    expect(within(screen.getByTestId("detalhe-ponto")).getByText("9:99")).toBeTruthy();
  });

  it("aprendendo: linha pontilhada, sem faixa, sem triângulo e com o texto da API", async () => {
    await render(tela(fetchEvolucao({ series: { "corrida.pace.leve": serieAprendendo } })));
    await screen.findByTestId("grafico-serie");
    expect(screen.getByTestId("linha-pontilhada")).toBeTruthy();
    expect(screen.queryByTestId("faixa-normal")).toBeNull();
    expect(screen.queryByTestId("marca-fora")).toBeNull();
    expect(screen.getByTestId("aprendendo")).toHaveTextContent(/faltam 3 treinos para mostrar a faixa/);
    expect(screen.queryByText("normal", { includeHiddenElements: true })).toBeNull(); // sem faixa, sem "normal" na legenda
  });

  it("volume por semana: barras, sem faixa e sem losango", async () => {
    mockMemoria.set("1", "corrida.volume_km");
    await render(tela(fetchEvolucao()));
    await screen.findByTestId("grafico-serie");
    expect(screen.queryByTestId("linha-serie")).toBeNull();
    expect(screen.queryByTestId("faixa-normal")).toBeNull();
  });
});

describe("Evolução v1: tocar num ponto", () => {
  it("o primeiro toque mostra o detalhe e 'Abrir treino'; o botão abre aquele treino", async () => {
    const abrir = jest.fn();
    await render(tela(fetchEvolucao(), { aoAbrirTreino: abrir }));
    await screen.findByTestId("grafico-serie");
    expect(screen.queryByTestId("detalhe-ponto")).toBeNull();
    expect(screen.getByText("4 pontos no período. Toque num ponto para ver os detalhes.")).toBeTruthy();
    expect(screen.queryByTestId("abrir-treino")).toBeNull();
    await fireEvent.press(screen.getByTestId("ponto-1"));
    const d = within(screen.getByTestId("detalhe-ponto"));
    expect(d.getByText("ter 06/03")).toBeTruthy();
    expect(d.getByText("5:55")).toBeTruthy();
    expect(d.getByText("fora do seu normal")).toBeTruthy();
    expect(screen.getByTestId("ponto-selecionado")).toBeTruthy();
    await fireEvent.press(screen.getByTestId("abrir-treino"));
    expect(abrir).toHaveBeenCalledWith(101);
  });

  it("sem aoAbrirTreino não há 'Abrir treino'", async () => {
    await render(tela(fetchEvolucao()));
    await screen.findByTestId("grafico-serie");
    await fireEvent.press(screen.getByTestId("ponto-0"));
    expect(screen.getByTestId("detalhe-ponto")).toBeTruthy();
    expect(screen.queryByTestId("abrir-treino")).toBeNull();
  });

  it("volume: o detalhe mostra o valor e a data, sem botão", async () => {
    mockMemoria.set("1", "corrida.volume_km");
    await render(tela(fetchEvolucao(), { aoAbrirTreino: jest.fn() }));
    await screen.findByTestId("grafico-serie");
    await fireEvent.press(screen.getByTestId("ponto-2"));
    const d = within(screen.getByTestId("detalhe-ponto"));
    expect(d.getByText("semana de 17/03")).toBeTruthy();
    expect(d.getByText("Semana de 17/03, 12 quilômetros, semana em curso")).toBeTruthy();
    expect(screen.queryByTestId("abrir-treino")).toBeNull();
    expect(screen.getByText("Semana anterior")).toBeTruthy();
  });

  it("as setas andam entre os treinos e travam nas pontas", async () => {
    await render(tela(fetchEvolucao()));
    await screen.findByTestId("grafico-serie");
    await fireEvent.press(screen.getByTestId("ponto-0"));
    expect(screen.getByTestId("treino-anterior").props.accessibilityState.disabled).toBe(true);
    await fireEvent.press(screen.getByTestId("treino-seguinte"));
    expect(within(screen.getByTestId("detalhe-ponto")).getByText("ter 06/03")).toBeTruthy();
    await fireEvent.press(screen.getByTestId("treino-anterior"));
    expect(within(screen.getByTestId("detalhe-ponto")).getByText("ter 02/03")).toBeTruthy();
  });

  it("'Ver os valores em lista' mostra todos os pontos, do mais recente ao mais antigo, e seleciona", async () => {
    await render(tela(fetchEvolucao()));
    await screen.findByTestId("grafico-serie");
    expect(screen.queryByTestId("lista-pontos")).toBeNull();
    await fireEvent.press(screen.getByTestId("ver-lista"));
    const lista = screen.getByTestId("lista-pontos");
    expect(within(lista).getByLabelText(paceLeve.pontos[1].rotulo)).toBeTruthy();
    await fireEvent.press(within(lista).getByTestId("linha-ponto-1"));
    expect(screen.getByTestId("detalhe-ponto")).toBeTruthy();
  });

  it("na rota da aba Evolução, 'Abrir treino' navega para /treino/<id>", async () => {
    const original = globalThis.fetch;
    globalThis.fetch = fetchEvolucao();
    try {
      await render(<ComSessao><Inicio /></ComSessao>);
      await screen.findByTestId("grafico-serie");
      await fireEvent.press(screen.getByTestId("ponto-2"));
      await fireEvent.press(screen.getByTestId("abrir-treino"));
    } finally {
      globalThis.fetch = original;
    }
    expect(mockPush).toHaveBeenCalledWith("/treino/102");
  });

  it("trocar de série limpa a seleção; o ponto selecionado continua ao voltar do treino (a tela segue montada)", async () => {
    await render(tela(fetchEvolucao(), { aoAbrirTreino: jest.fn() }));
    await screen.findByTestId("grafico-serie");
    await fireEvent.press(screen.getByTestId("ponto-1"));
    await fireEvent.press(screen.getByTestId("abrir-treino"));
    expect(screen.getByTestId("detalhe-ponto")).toBeTruthy(); // "Voltar" devolve com o mesmo ponto
    await fireEvent.press(screen.getByTestId("abrir-seletor"));
    await fireEvent.press(screen.getByTestId("serie-corrida.volume_km"));
    await waitFor(() => expect(screen.getByText(volumeSemana.frase.texto)).toBeTruthy());
    expect(screen.queryByTestId("detalhe-ponto")).toBeNull();
  });
});

describe("Evolução v1: estados", () => {
  it("série sem pontos: título, a frase da API e 'Escolher outra série'", async () => {
    await render(tela(fetchEvolucao({ series: { "corrida.pace.leve": serieVazia } })));
    const vazio = await screen.findByTestId("estado-vazio");
    expect(within(vazio).getByText(serieVazia.frase.texto)).toBeTruthy();
    expect(within(vazio).getByTestId("escolher-outra")).toBeTruthy();
    expect(screen.queryByTestId("grafico-serie")).toBeNull();
  });

  it("catálogo vazio: pede o arquivo do relógio e mantém o botão de enviar", async () => {
    await render(tela(fetchEvolucao({ catalogo: { ...catalogo, series: [], serie_padrao: null } }), { ocultarEnviarFit: true }));
    const vazio = await screen.findByTestId("estado-vazio");
    expect(within(vazio).getByText("Envie o arquivo do seu relógio pela aba Conta e a evolução aparece aqui.")).toBeTruthy();
    expect(screen.getByText("Enviar arquivo FIT")).toBeTruthy();
  });

  it("catálogo só com séries indisponíveis: também é vazio, sem seletor", async () => {
    const so = { ...catalogo, serie_padrao: null, series: [serieCatalogo.tiros] };
    await render(tela(fetchEvolucao({ catalogo: so })));
    await screen.findByTestId("estado-vazio");
    expect(screen.queryByTestId("seletor-serie")).toBeNull();
  });

  it("erro de rede no catálogo: wifi-off, mensagem e 'Tentar de novo' que busca de novo", async () => {
    const f = jest.fn().mockRejectedValueOnce(new Error("x")).mockImplementation(fetchEvolucao()) as unknown as typeof fetch & jest.Mock;
    await render(tela(f));
    const erro = await screen.findByTestId("estado-erro");
    expect(within(erro).getByText("wifi-off:40")).toBeTruthy();
    expect(within(erro).getByText("Não foi possível carregar esta série.")).toBeTruthy();
    expect(within(erro).getByText("Verifique a conexão e tente de novo.")).toBeTruthy();
    await fireEvent.press(within(erro).getByText("Tentar de novo"));
    await screen.findByTestId("frase-evolucao");
  });

  it("erro na série: o seletor continua e 'Tentar de novo' busca a série", async () => {
    const boa = fetchEvolucao();
    let falhou = false;
    const f = jest.fn(async (url: unknown) => {
      if (String(url).includes("/series/corrida.pace.leve") && !falhou) {
        falhou = true;
        return resposta(500, { detail: "x" });
      }
      return boa(url as string);
    }) as unknown as typeof fetch;
    await render(tela(f));
    const erro = await screen.findByTestId("estado-erro");
    expect(screen.getByTestId("seletor-serie")).toBeTruthy();
    await fireEvent.press(within(erro).getByText("Tentar de novo"));
    await screen.findByTestId("frase-evolucao");
  });

  it("404: 'Atleta não encontrado', sem botão", async () => {
    await render(tela(fetchEvolucao({ catalogo: 404 })));
    const erro = await screen.findByTestId("estado-erro");
    expect(within(erro).getByText("Atleta não encontrado")).toBeTruthy();
    expect(within(erro).queryByText("Tentar de novo")).toBeNull();
  });

  it("a frase 'poucos treinos' vem da API, sem o app comentar", async () => {
    const poucos = { ...paceLeve, frase: { ...paceLeve.frase, tipo: "poucos" as const, texto: "Poucos treinos para comparar: 2 nas últimas 4 semanas, 4 nas 4 anteriores." } };
    await render(tela(fetchEvolucao({ series: { "corrida.pace.leve": poucos } })));
    expect(await screen.findByText(poucos.frase.texto)).toBeTruthy();
  });
});

describe("botão de enviar e aviso de professor", () => {
  it("enviar: secundário com dados, primário quando não há nada para mostrar", async () => {
    await render(tela(fetchEvolucao()));
    await screen.findByTestId("frase-evolucao");
    expect(screen.getByText("Enviar arquivo FIT")).toBeTruthy();
  });

  describe("aviso de pedido de professor (#503)", () => {
    const base = fetchEvolucao();
    const comPedidos = (professores: unknown[]) =>
      jest.fn(async (input: RequestInfo | URL) =>
        String(input).endsWith("/professores") ? resposta(200, { atleta_id: 1, termo_vigente: "t", professores }) : base(input),
      ) as unknown as typeof fetch & jest.Mock;
    const telaComAviso = (f: typeof fetch, aoAbrirConsentimento = jest.fn()) => (
      <TelaEvolucao apiUrl="http://api.teste" atletaId={1} fetchFn={f} aoAbrirConsentimento={aoAbrirConsentimento} />
    );
    const v = (consentimento: boolean) => ({ professor_id: 1, nome: "Carlos Exemplo", consentimento });

    it("com pedido aguardando mostra a linha e 'Ver' abre o consentimento", async () => {
      const abrir = jest.fn();
      await render(telaComAviso(comPedidos([v(false)]), abrir));
      expect(await screen.findByText("Há um professor pedindo para ver seus treinos.")).toBeTruthy();
      await fireEvent.press(screen.getByTestId("ver-pedido"));
      expect(abrir).toHaveBeenCalled();
      // Não é erro: região viva educada, nunca "alert" (seria lido toda vez que a tela abre).
      expect(screen.getByTestId("aviso-consentimento").props.accessibilityRole).toBeUndefined();
      expect(screen.getByTestId("aviso-consentimento").props.accessibilityLiveRegion).toBe("polite");
    });

    it("sem pedido, ou se a busca falhar, não há aviso", async () => {
      await render(telaComAviso(comPedidos([v(true)])));
      await screen.findByTestId("frase-evolucao");
      expect(screen.queryByTestId("aviso-consentimento")).toBeNull();
    });
  });
});
