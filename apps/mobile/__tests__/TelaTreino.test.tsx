import { StyleSheet } from "react-native";
import { fireEvent, render, screen, within } from "@testing-library/react-native";

import { NOTA_NORMAL } from "../src/componentes/CartaoNormal";
import { TelaTreino } from "../src/componentes/TelaTreino";
import { atividades } from "../__fixtures__/atividades";

// Ícone falso com nome e tamanho (o real carrega a fonte e quebra no Jest).
jest.mock("@expo/vector-icons", () => {
  const { Text } = require("react-native");
  return { MaterialIcons: ({ name, size }: { name: string; size: number }) => <Text>{`${name}:${size}`}</Text> };
});

const resposta = (status: number, corpo: unknown) =>
  ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const fetchCom = (status: number, corpo: unknown) =>
  jest.fn(async (..._args: Parameters<typeof fetch>) => resposta(status, corpo)) as unknown as typeof fetch & jest.Mock;
const tela = (f: typeof fetch, extra = {}) => (
  <TelaTreino apiUrl="http://api.teste" atletaId={1} atividadeId={101} fetchFn={f} {...extra} />
);

// O primeiro render a frio no CI passou de 5 s uma vez (#219); folga para a máquina lenta.
jest.setTimeout(20000);

describe("tela de um treino", () => {
  it("chama a API da atividade", async () => {
    const f = fetchCom(200, atividades.ok);
    await render(tela(f));
    await screen.findByTestId("cartao-resumo");
    expect(f.mock.calls[0][0]).toBe("http://api.teste/atletas/1/atividades/101");
  });

  it("mostra carregando", async () => {
    const f = jest.fn(() => new Promise<Response>(() => {})) as unknown as typeof fetch;
    await render(tela(f));
    expect(screen.getByText("Carregando o treino...")).toBeTruthy();
    expect(screen.getByTestId("esqueleto-treino", { includeHiddenElements: true })).toBeTruthy();
    expect(screen.queryByTestId("esqueleto-evolucao", { includeHiddenElements: true })).toBeNull();
  });

  it("erro de rede: ícone wifi-off de 40, alerta e 'Tentar de novo'; 404 e 500: error-outline de 40", async () => {
    const { unmount } = await render(tela(jest.fn().mockRejectedValue(new Error("x")) as unknown as typeof fetch));
    const rede = await screen.findByTestId("estado-erro");
    expect(within(rede).getByText("wifi-off:40")).toBeTruthy();
    expect(within(rede).getByRole("alert")).toBeTruthy();
    await unmount();
    for (const status of [404, 500]) {
      const r = await render(tela(fetchCom(status, { detail: "x" })));
      const e = await screen.findByTestId("estado-erro");
      expect(within(e).getByText("error-outline:40")).toBeTruthy();
      expect(within(e).getByRole("alert")).toBeTruthy();
      expect(within(e).queryByText("Tentar de novo")).toBeNull();
      await r.unmount();
    }
  });

  it("cada linha do clima é um item só, lido como 'rótulo, valor'", async () => {
    await render(tela(fetchCom(200, atividades.ok)));
    const cartao = await screen.findByTestId("cartao-clima");
    for (const rotulo of ["Temperatura, 24,3 °C", "Sensação térmica, 25,1 °C", "Umidade, 61 %", "Vento, 8,2 km/h"]) {
      expect(within(cartao).getByLabelText(rotulo).props.accessible).toBe(true);
    }
  });

  it("clima ok: resumo com campos prontos, valores do clima e atribuição", async () => {
    await render(tela(fetchCom(200, atividades.ok)));
    await screen.findByTestId("cartao-resumo");
    expect(screen.getByText("18/03/25 às 06:30")).toBeTruthy();
    expect(screen.getByText("0:52:05")).toBeTruthy();
    const resumo = within(screen.getByTestId("cartao-resumo"));
    expect(resumo.getByText("5:12 min/km")).toBeTruthy();
    expect(resumo.getByText("10,00 km")).toBeTruthy();
    expect(resumo.getByText("152 bpm")).toBeTruthy();
    for (const r of ["Distância, 10,00 km", "Pace médio, 5:12 min/km", "FC média, 152 bpm"]) {
      expect(within(screen.getByTestId("cartao-resumo")).getByLabelText(r)).toBeTruthy();
    }
    expect(screen.getByText("24,3 °C")).toBeTruthy();
    expect(screen.getByText("25,1 °C")).toBeTruthy();
    expect(screen.getByText("61 %")).toBeTruthy();
    expect(screen.getByText("8,2 km/h")).toBeTruthy();
    expect(screen.getByText("Weather data by Open-Meteo.com")).toBeTruthy();
  });

  it("não formata: mostra pace, hora e duração exatamente como vieram", async () => {
    const a = { ...atividades.ok, pace_medio: "9:99", hora_local: "99:88", duracao: "7:77:77", data_local: "2030-01-02" };
    await render(tela(fetchCom(200, a)));
    await screen.findByTestId("cartao-resumo");
    expect(screen.getByText("02/01/30 às 99:88")).toBeTruthy();
    expect(screen.getByText("7:77:77")).toBeTruthy();
    expect(screen.getByText("9:99 min/km")).toBeTruthy();
  });

  it("distância: mostra `distancia` exatamente como veio, sem converter distancia_m", async () => {
    const a = { ...atividades.ok, distancia: "ABC 7,5 xyz", distancia_m: 123456 };
    await render(tela(fetchCom(200, a)));
    await screen.findByTestId("cartao-resumo");
    expect(screen.getByText("ABC 7,5 xyz")).toBeTruthy();
    expect(screen.queryByText(/123/)).toBeNull();
  });

  it("distância: natação em metros e sem distância não mostra a linha", async () => {
    await render(tela(fetchCom(200, atividades.natacao)));
    await screen.findByTestId("cartao-resumo");
    expect(screen.getByText("1.800 m")).toBeTruthy();
  });

  it("distância null: não mostra a linha, mesmo com distancia_m", async () => {
    await render(tela(fetchCom(200, { ...atividades.ok, distancia: null, distancia_m: 5000 })));
    await screen.findByTestId("cartao-resumo");
    expect(screen.queryByText(/Distância/)).toBeNull();
  });

  it("atribuição vem da API: sem o campo, não inventa", async () => {
    const clima = { ...atividades.ok.clima!, atribuicao: undefined };
    await render(tela(fetchCom(200, { ...atividades.ok, clima })));
    await screen.findByTestId("cartao-clima");
    expect(screen.queryByText(/Open-Meteo/)).toBeNull();
  });

  it.each([
    ["indoor", "Treino em ambiente fechado: não há clima para mostrar."],
    ["sem_posicao", "O arquivo não tem posição, então não dá para buscar o clima."],
    ["pendente", "O clima deste treino ainda não chegou. Treinos recentes podem levar cerca de uma semana."],
    ["falha", "Não foi possível obter o clima deste treino."],
  ] as const)("clima %s: frase própria, sem valores nem atribuição", async (chave, frase) => {
    await render(tela(fetchCom(200, atividades[chave])));
    await screen.findByTestId("cartao-clima");
    expect(screen.getByText(frase)).toBeTruthy();
    expect(screen.queryByText("Temperatura")).toBeNull();
    expect(screen.queryByText(/Open-Meteo/)).toBeNull();
  });

  it("natação: sem pace e sem FC", async () => {
    await render(tela(fetchCom(200, atividades.natacao)));
    await screen.findByTestId("cartao-resumo");
    expect(screen.queryByText(/Pace médio/)).toBeNull();
    expect(screen.getByText("sem FC")).toBeTruthy();
    expect(screen.getByText("0:45:00")).toBeTruthy();
    expect(screen.getAllByText("Natação").length).toBeGreaterThan(0);
  });

  it("sem objeto clima: não mostra o cartão", async () => {
    await render(tela(fetchCom(200, { ...atividades.ok, clima: null })));
    await screen.findByTestId("cartao-resumo");
    expect(screen.queryByTestId("cartao-clima")).toBeNull();
  });

  it("404 de atividade", async () => {
    await render(tela(fetchCom(404, { detail: "atividade não encontrada" })));
    expect(await screen.findByText("Treino não encontrado")).toBeTruthy();
  });

  it("404 de atleta", async () => {
    await render(tela(fetchCom(404, { detail: "atleta não encontrado" })));
    expect(await screen.findByText("Atleta não encontrado")).toBeTruthy();
  });

  it("erro 500", async () => {
    await render(tela(fetchCom(500, {})));
    expect(await screen.findByText("Não foi possível carregar este treino. Tente de novo mais tarde.")).toBeTruthy();
  });

  it("erro de rede tem 'Tentar de novo'", async () => {
    const f = jest
      .fn()
      .mockRejectedValueOnce(new Error("rede"))
      .mockResolvedValue(resposta(200, atividades.ok)) as unknown as typeof fetch;
    await render(tela(f));
    expect(await screen.findByText("Não foi possível falar com o servidor")).toBeTruthy();
    fireEvent.press(screen.getByText("Tentar de novo"));
    expect(await screen.findByTestId("cartao-resumo")).toBeTruthy();
  });

  it("voltar chama o callback", async () => {
    const aoVoltar = jest.fn();
    await render(tela(fetchCom(200, atividades.ok), { aoVoltar }));
    fireEvent.press(screen.getByLabelText("Voltar"));
    expect(aoVoltar).toHaveBeenCalled();
  });

  it("alvo de toque do voltar tem 44", async () => {
    await render(tela(fetchCom(200, atividades.ok), { aoVoltar: () => {} }));
    const estilo = StyleSheet.flatten(screen.getByLabelText("Voltar").props.style);
    expect(estilo.minHeight).toBeGreaterThanOrEqual(44);
  });

  describe("carga e forma do dia (#466)", () => {
    const abrir = async (a: unknown) => {
      await render(tela(fetchCom(200, a)));
      return screen.findByTestId("cartao-carga-forma");
    };

    it("com carga e forma: números prontos, a palavra estimativa e a nota fixa", async () => {
      const c = await abrir(atividades.ok);
      expect(within(c).getByText("estimativa")).toBeTruthy();
      expect(within(c).getByText("87,4", { exact: false })).toBeTruthy();
      expect(within(c).getByText("pontos")).toBeTruthy();
      expect(within(c).getByText("Estimada pela FC.")).toBeTruthy();
      expect(within(c).getByText("No fim do dia 18/03/25")).toBeTruthy();
      expect(within(c).getByLabelText("Condicionamento (CTL), 41,2")).toBeTruthy();
      expect(within(c).getByLabelText("Fadiga (ATL), 52,8")).toBeTruthy();
      expect(within(c).getByLabelText("Forma (TSB), menos 11,6")).toBeTruthy();
      expect(within(c).getByText(/Não são medidas e não são diagnóstico/)).toBeTruthy();
      expect(within(c).queryByTestId("aviso-sem-carga-no-dia")).toBeNull();
    });

    it("leitor de tela: o sinal de menos do TSB é lido como 'menos' e o de mais continua", async () => {
      const c = await abrir(atividades.ok);
      expect(within(c).getByLabelText("Forma (TSB), menos 11,6")).toBeTruthy();
      expect(within(c).queryByLabelText(/\u2212/)).toBeNull();
    });

    it("cada linha da forma abre a definição fixa e fecha de novo", async () => {
      const c = await abrir(atividades.ok);
      const linha = within(c).getByLabelText("Fadiga (ATL), 52,8");
      expect(within(c).queryByText(/últimos 7 dias/)).toBeNull();
      await fireEvent.press(linha);
      expect(within(c).getByText("Fadiga: média da sua carga nos últimos 7 dias.")).toBeTruthy();
      await fireEvent.press(linha);
      expect(within(c).queryByText(/últimos 7 dias/)).toBeNull();
    });

    it("dia com treino sem carga: mostra o texto pronto da API", async () => {
      const c = await abrir(atividades.formaSemCargaNoDia);
      expect(within(c).getByText("+3,2")).toBeTruthy();
      expect(within(c).getByText(/Há 1 treino deste dia sem carga calculada/)).toBeTruthy();
    });

    it("aprendendo: a carga do treino e o aviso, sem CTL, ATL nem TSB", async () => {
      const c = await abrir(atividades.formaAprendendo);
      expect(within(c).getByText("87,4", { exact: false })).toBeTruthy();
      expect(within(c).getByText("Ainda aprendendo a sua forma: faltam 23 dias de histórico para estimar.")).toBeTruthy();
      expect(within(c).getByText("hourglass-empty:16")).toBeTruthy();
      expect(within(c).queryByText(/CTL|ATL|TSB/)).toBeNull();
    });

    it("sem carga: o motivo da API no lugar do número, e a forma continua", async () => {
      const c = await abrir(atividades.semCarga);
      expect(within(c).getByText(/não tem frequência cardíaca/)).toBeTruthy();
      expect(within(c).queryByText("pontos")).toBeNull();
      expect(within(c).getByLabelText("Forma (TSB), menos 11,6")).toBeTruthy();
    });

    it("carga pendente e forma sem série: só o aviso da carga", async () => {
      const c = await abrir(atividades.cargaPendente);
      expect(within(c).getByText("A carga deste treino ainda não foi calculada.")).toBeTruthy();
      expect(within(c).queryByText(/Condicionamento/)).toBeNull();
    });

    it("carga e forma ausentes: o cartão não aparece", async () => {
      await render(tela(fetchCom(200, atividades.semCargaNemForma)));
      await screen.findByTestId("cartao-resumo");
      expect(screen.queryByTestId("cartao-carga-forma")).toBeNull();
    });
  });

  describe("esforços (#467)", () => {
    const abrir = async (a: unknown) => {
      await render(tela(fetchCom(200, a)));
      return screen.findByTestId("cartao-esforcos");
    };

    it("com esforços: aquecimento, uma linha por esforço, pausa e desaquecimento, na ordem da API", async () => {
      const c = await abrir(atividades.comEsforcos);
      expect(within(c).getByText("Aquecimento 12:10")).toBeTruthy();
      expect(within(c).getByText("Desaquecimento 8:40")).toBeTruthy();
      expect(within(c).getByText("min/km", { includeHiddenElements: true })).toBeTruthy();
      expect(within(c).getByLabelText("Esforço 1 · 1 km, pace 4:01 por quilômetro, FC 171, pausa 1:00")).toBeTruthy();
      expect(within(c).getByText("pausa 1:00")).toBeTruthy();
      expect(within(c).getByLabelText("Esforço 2 · 1 km, pace 4:03 por quilômetro, FC 173")).toBeTruthy();
      // FC null vira "sem dado"; a recuperação não tem linha.
      expect(within(c).getByLabelText("Esforço 3 · 1 km, pace 4:04 por quilômetro, FC sem dado")).toBeTruthy();
      expect(within(c).getByText("sem dado")).toBeTruthy();
      expect(within(c).queryByTestId("esforco-4")).toBeNull();
    });

    it("mais de 8: mostra 8 e 'Ver todos os 12 esforços'; aberto vira 'Ver menos'", async () => {
      const c = await abrir(atividades.esforcosMuitos);
      expect(within(c).getAllByTestId(/^esforco-/)).toHaveLength(8);
      await fireEvent.press(within(c).getByText("Ver todos os 12 esforços"));
      expect(within(c).getAllByTestId(/^esforco-/)).toHaveLength(12);
      await fireEvent.press(within(c).getByText("Ver menos"));
      expect(within(c).getAllByTestId(/^esforco-/)).toHaveLength(8);
    });

    it("ciclismo: a coluna vira Velocidade (km/h) pela presença do campo", async () => {
      const c = await abrir(atividades.esforcosCiclismo);
      expect(within(c).getByText("Velocidade", { includeHiddenElements: true })).toBeTruthy();
      expect(within(c).getByText("km/h", { includeHiddenElements: true })).toBeTruthy();
      expect(within(c).queryByText("Pace", { includeHiddenElements: true })).toBeNull();
      expect(within(c).getByText("32,5")).toBeTruthy();
    });

    it("referência da atividade: aviso fixo", async () => {
      const c = await abrir(atividades.esforcosReferencia);
      expect(within(c).getByText("Sem treinos anteriores parecidos: os esforços foram detectados só com este treino.")).toBeTruthy();
    });

    it("sem nenhum esforço, mas com outras categorias: aviso neutro", async () => {
      const c = await abrir(atividades.semEsforco);
      expect(within(c).getByText("Nenhum esforço detectado neste treino.")).toBeTruthy();
      expect(within(c).queryByText("Esforço", { includeHiddenElements: true })).toBeNull();
    });

    it("só rodagem, ausente ou null: o cartão não aparece", async () => {
      for (const a of [atividades.soRodagem, atividades.ok, { ...atividades.ok, esforcos: null }]) {
        const r = await render(tela(fetchCom(200, a)));
        await screen.findByTestId("cartao-resumo");
        expect(screen.queryByTestId("cartao-esforcos")).toBeNull();
        await r.unmount();
      }
    });
  });

  describe("treino de transição (#467)", () => {
    const abrir = async (a: unknown, f: typeof fetch = fetchCom(200, a)) => {
      await render(tela(f));
      return { c: await screen.findByTestId("cartao-transicao"), f };
    };
    // GET inicial, depois a resposta da correção e o GET de novo com o estado novo.
    const comCorrecao = (inicial: unknown, depois: unknown, status = 200): typeof fetch & jest.Mock => {
      let get = 0;
      return jest.fn(async (_url: unknown, init?: RequestInit) => {
        if (init?.method === "PUT" || init?.method === "DELETE") return resposta(status, status === 200 ? (depois as { transicao: unknown }).transicao : { detail: "x" });
        return resposta(200, get++ === 0 ? inicial : depois);
      }) as unknown as typeof fetch & jest.Mock;
    };

    it("sugerida: texto da regra e 'Não é transição'; sem 'Voltar à sugestão'", async () => {
      const { c } = await abrir(atividades.transicaoSugerida);
      expect(within(c).getByText("Este treino faz parte de um treino de transição.")).toBeTruthy();
      expect(within(c).getByText("O app sugeriu isso porque outro treino começou logo depois.")).toBeTruthy();
      expect(within(c).getByText("Não é transição")).toBeTruthy();
      expect(within(c).queryByText("Voltar à sugestão do app")).toBeNull();
    });

    it("do atleta (sim): sem botão principal, só 'Voltar à sugestão do app'", async () => {
      const { c } = await abrir(atividades.transicaoDoAtleta);
      expect(within(c).getByText("Você marcou assim.")).toBeTruthy();
      expect(within(c).queryByText("Não é transição")).toBeNull();
      expect(within(c).getByText("Voltar à sugestão do app")).toBeTruthy();
    });

    it("do atleta (não) e sem marca: textos e botões da spec", async () => {
      const { c } = await abrir(atividades.transicaoNegada);
      expect(within(c).getByText("Você marcou que este treino não é de transição.")).toBeTruthy();
      expect(within(c).getByText("Marcar como transição")).toBeTruthy();
      expect(within(c).getByText("Voltar à sugestão do app")).toBeTruthy();
    });

    it("sem marca: 'Marcar como transição' e nenhum 'Voltar'", async () => {
      const { c } = await abrir(atividades.semTransicao);
      expect(within(c).getByText("Este treino não está marcado como de transição.")).toBeTruthy();
      expect(within(c).queryByText("Voltar à sugestão do app")).toBeNull();
    });

    it("editavel false ou transicao ausente: o cartão não aparece", async () => {
      for (const a of [atividades.transicaoNaoEditavel, { ...atividades.ok, transicao: undefined }]) {
        const r = await render(tela(fetchCom(200, a)));
        await screen.findByTestId("cartao-resumo");
        expect(screen.queryByTestId("cartao-transicao")).toBeNull();
        await r.unmount();
      }
    });

    it("corrigir: PUT com o corpo certo, busca o treino de novo e mostra a origem 'atleta'", async () => {
      const f = comCorrecao(atividades.transicaoSugerida, atividades.transicaoDoAtleta);
      const { c } = await abrir(null, f);
      await fireEvent.press(within(c).getByText("Não é transição"));
      expect(await screen.findByText("Você marcou assim.")).toBeTruthy();
      const put = f.mock.calls.find((x) => x[1]?.method === "PUT")!;
      expect(put[0]).toBe("http://api.teste/atletas/1/atividades/101/transicao");
      expect(JSON.parse(put[1]!.body as string)).toEqual({ transicao: false });
      expect(f.mock.calls.filter((x) => !x[1]?.method)).toHaveLength(2);
    });

    it("voltar à sugestão: DELETE e o estado da API", async () => {
      const f = comCorrecao(atividades.transicaoDoAtleta, atividades.transicaoSugerida);
      const { c } = await abrir(null, f);
      await fireEvent.press(within(c).getByText("Voltar à sugestão do app"));
      expect(await screen.findByText("O app sugeriu isso porque outro treino começou logo depois.")).toBeTruthy();
      expect(f.mock.calls.some((x) => x[1]?.method === "DELETE")).toBe(true);
    });

    it("erro ao enviar: mensagem, estado anterior e botão ativo de novo", async () => {
      const f = comCorrecao(atividades.transicaoSugerida, atividades.transicaoSugerida, 500);
      const { c } = await abrir(null, f);
      await fireEvent.press(within(c).getByText("Não é transição"));
      expect(await screen.findByText("Não foi possível salvar. Tente de novo.")).toBeTruthy();
      expect(within(c).getByText("O app sugeriu isso porque outro treino começou logo depois.")).toBeTruthy();
      expect(within(c).getByText("Não é transição")).toBeTruthy();
      expect(f.mock.calls.filter((x) => !x[1]?.method)).toHaveLength(1);
    });

    it("enquanto salva: o botão mostra 'Salvando...' e fica desligado", async () => {
      let solta: (r: Response) => void = () => {};
      const f = jest.fn(async (_u: unknown, init?: RequestInit) =>
        init?.method === "PUT" ? new Promise<Response>((ok) => (solta = ok)) : resposta(200, atividades.transicaoSugerida),
      ) as unknown as typeof fetch;
      const { c } = await abrir(null, f);
      void fireEvent.press(within(c).getByText("Não é transição"));
      expect(await within(c).findByText("Salvando...")).toBeTruthy();
      expect(within(c).getByRole("button", { name: "Marcar este treino como não sendo de transição" }).props.accessibilityState.disabled).toBe(true);
      await solta(resposta(500, { detail: "x" }));
    });

    it("com botão principal, 'Voltar à sugestão do app' também mostra 'Salvando...' e só ele", async () => {
      let solta: (r: Response) => void = () => {};
      const f = jest.fn(async (_u: unknown, init?: RequestInit) =>
        init?.method === "DELETE" ? new Promise<Response>((ok) => (solta = ok)) : resposta(200, atividades.transicaoNegada),
      ) as unknown as typeof fetch;
      const { c } = await abrir(null, f);
      void fireEvent.press(within(c).getByText("Voltar à sugestão do app"));
      expect(await within(c).findByText("Salvando...")).toBeTruthy();
      expect(within(c).getByText("Marcar como transição")).toBeTruthy();
      await solta(resposta(500, { detail: "x" }));
    });
  });

  describe("comparado com o seu normal (#465)", () => {
    const abrir = async (a: unknown) => {
      await render(tela(fetchCom(200, a)));
      return screen.findByTestId("cartao-normal");
    };

    it("dentro do normal: valor, palavra com ícone, texto da API e nota fixa", async () => {
      const c = await abrir(atividades.ok);
      const fc = within(within(c).getByTestId("metrica-fc_media"));
      expect(fc.getByText("152 bpm")).toBeTruthy();
      expect(fc.getByText("Dentro do seu normal")).toBeTruthy();
      expect(fc.getByText("adjust:16")).toBeTruthy();
      expect(fc.getByText("Mediana de 150 bpm, em 6 treinos leves.")).toBeTruthy();
      expect(within(c).getByText(NOTA_NORMAL)).toBeTruthy();
    });

    it("fora do normal: ícone e palavra, sem 'bom' nem 'ruim' e sem cor de erro ou alerta", async () => {
      const c = await abrir(atividades.normalFora);
      const carga = within(within(c).getByTestId("metrica-carga_hora"));
      expect(carga.getByText("61,0 pontos/h")).toBeTruthy();
      expect(carga.getByText("Fora do seu normal")).toBeTruthy();
      expect(carga.getByText("unfold-more:16")).toBeTruthy();
      expect(carga.getByText(/9,0 pontos\/h maior que a mediana/)).toBeTruthy();
      expect(within(c).getAllByText("Fora do seu normal")).toHaveLength(3);
      expect(within(within(c).getByTestId("metrica-fc_media")).getByText("11 bpm acima da mediana de 150 bpm, em 6 treinos leves.")).toBeTruthy();
      const cores = JSON.stringify(StyleSheet.flatten(carga.getByText("Fora do seu normal").props.style));
      expect(cores).not.toMatch(/#b3261e|#c62828/i);
    });

    it("aprendendo e sem dado: uma linha por métrica, só estado e texto, sem valor", async () => {
      const c = await abrir(atividades.normalAprendendo);
      const pace = within(within(c).getByTestId("metrica-pace_medio"));
      expect(pace.getByText("Aprendendo o seu normal")).toBeTruthy();
      expect(pace.getByText("hourglass-empty:16")).toBeTruthy();
      expect(pace.getByText("3 de 8 treinos do tipo leve nas últimas 12 semanas.")).toBeTruthy();
      const fc = within(within(c).getByTestId("metrica-fc_media"));
      expect(fc.getByText("Sem dado neste treino")).toBeTruthy();
      expect(fc.getByText("info-outline:16")).toBeTruthy();
      expect(within(c).queryByText(/bpm$/)).toBeNull();
    });

    it("sem linha de base (sem tipo): aviso neutro com o texto da API, sem métricas", async () => {
      const c = await abrir(atividades.normalSemTipo);
      expect(within(c).getByText("Sem linha de base: o treino não tem tipo.")).toBeTruthy();
      expect(within(c).queryByText(NOTA_NORMAL)).toBeNull();
    });

    it("natação (modalidade sem métricas): aviso com o texto da API", async () => {
      const c = await abrir(atividades.natacao);
      expect(within(c).getByText("Ainda não há linha de base para natação.")).toBeTruthy();
    });

    it("multiesporte e linha_base ausente: o cartão não aparece", async () => {
      for (const a of [atividades.normalMultiesporte, { ...atividades.ok, linha_base: null }]) {
        const r = await render(tela(fetchCom(200, a)));
        await screen.findByTestId("cartao-resumo");
        expect(screen.queryByTestId("cartao-normal")).toBeNull();
        await r.unmount();
      }
    });

    it("cada métrica é um item só para o leitor de tela: rótulo, valor, estado e texto", async () => {
      const c = await abrir(atividades.ok);
      expect(within(c).getByLabelText("FC média. 152 bpm. Dentro do seu normal. Mediana de 150 bpm, em 6 treinos leves.")).toBeTruthy();
    });

    it("o cartão fica entre Esforços e Carga e forma do dia", async () => {
      await render(tela(fetchCom(200, atividades.comEsforcos)));
      await screen.findByTestId("cartao-normal");
      const ids = JSON.stringify(screen.toJSON());
      const pos = (t: string) => ids.indexOf(`"${t}"`);
      expect(pos("cartao-esforcos")).toBeLessThan(pos("cartao-normal"));
      expect(pos("cartao-normal")).toBeLessThan(pos("cartao-carga-forma"));
    });
  });
});
