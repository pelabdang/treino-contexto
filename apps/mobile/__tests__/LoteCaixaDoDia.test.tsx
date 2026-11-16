import { fireEvent, render, screen, waitFor, within } from "@testing-library/react-native";

import { confirmarTiposDeTreino, codigoDoErro, type CaixaDoDia } from "../src/caixa/api";
import { textoSalvo, TelaCaixaDoDia } from "../src/componentes/TelaCaixaDoDia";
import { caixa, OBSERVACAO_MARCADOR } from "../__fixtures__/caixaDoDia";

jest.mock("@expo/vector-icons", () => {
  const { Text } = require("react-native");
  return { MaterialIcons: ({ name, size }: { name: string; size: number }) => <Text>{`${name}:${size}`}</Text> };
});

jest.setTimeout(20000);

const resposta = (status: number, corpo: unknown) => ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const copia = (): CaixaDoDia => JSON.parse(JSON.stringify(caixa));
const erro404 = { detail: [{ loc: ["body"], msg: "x", type: "atividade_nao_encontrada" }] };
const erro422SemTipo = { detail: [{ loc: ["body"], msg: "x", type: "atividade_sem_tipo" }] };

/** GET devolve a caixa; PUT responde `put` (função para poder devolver promessa pendente ou rejeitar). */
function api(put: (corpo: unknown) => Promise<Response>, get: () => Promise<Response> = async () => resposta(200, caixa)) {
  return jest.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
    if (init?.method === "PUT") return put(JSON.parse(String(init.body)));
    return get();
  }) as unknown as typeof fetch & jest.Mock;
}
const puts = (f: jest.Mock) => f.mock.calls.filter((c) => c[1]?.method === "PUT");
const gets = (f: jest.Mock) => f.mock.calls.filter((c) => c[1]?.method !== "PUT");
const tela = (f: typeof fetch) => <TelaCaixaDoDia apiUrl="http://api.teste" professorId={7} fetchFn={f} />;
const aberta = async (f: typeof fetch) => {
  await render(tela(f));
  await screen.findByTestId("resumo");
};
const ok = (corpo: unknown) => async () => resposta(200, corpo);

describe("lote: seleção", () => {
  it("nenhum selecionado ao abrir, sem barra, com 'Selecionar todos (N)'", async () => {
    await aberta(api(ok({ confirmados: 1, corrigidos: 0 })));
    expect(screen.getByText("Selecionar todos (2)")).toBeTruthy();
    expect(screen.queryByTestId("barra-lote")).toBeNull();
    expect(screen.getByTestId("selecionar-511").props.accessibilityState.checked).toBe(false);
  });

  it("marcar uma linha mostra a barra com o que vai acontecer; desmarcar tira a barra", async () => {
    await aberta(api(ok({})));
    await fireEvent.press(screen.getByTestId("selecionar-511"));
    expect(screen.getByTestId("selecionar-511").props.accessibilityState.checked).toBe(true);
    expect(screen.getByTestId("resumo-lote").props.children).toBe("1 selecionado · 0 corrigidos");
    expect(screen.getByText("Salvar 1 tipo")).toBeTruthy();
    expect(screen.getByText("Depois de salvar, para mudar de novo é só corrigir o tipo outra vez.")).toBeTruthy();
    expect(within(screen.getByTestId("barra-lote")).getByText("Limpar seleção")).toBeTruthy();
    await fireEvent.press(screen.getByTestId("selecionar-511"));
    expect(screen.queryByTestId("barra-lote")).toBeNull();
  });

  it("rótulo da caixa de seleção: nome, modalidade, data e tipo sugerido", async () => {
    await aberta(api(ok({})));
    expect(screen.getByTestId("selecionar-511").props.accessibilityLabel).toBe(
      "Selecionar o treino de Atleta Fixture Ana, corrida de 11 de novembro, tipo sugerido intervalado",
    );
    expect(screen.getByTestId("selecionar-511").props.accessibilityRole).toBe("checkbox");
  });

  it("selecionar todos marca todos; de novo, desmarca todos", async () => {
    await aberta(api(ok({})));
    await fireEvent.press(screen.getByTestId("selecionar-todos"));
    expect(screen.getByTestId("resumo-lote").props.children).toBe("2 selecionados · 0 corrigidos");
    expect(screen.getByText("Salvar 2 tipos")).toBeTruthy();
    expect(screen.getByTestId("selecionar-todos").props.accessibilityState.checked).toBe(true);
    await fireEvent.press(screen.getByTestId("selecionar-todos"));
    expect(screen.queryByTestId("barra-lote")).toBeNull();
  });

  it("com mais de 200 novos, marca os 200 primeiros e avisa", async () => {
    const c = copia();
    c.novos = Array.from({ length: 201 }, (_, i) => ({ ...c.novos[0], atividade_id: 1000 + i }));
    await aberta(api(ok({}), async () => resposta(200, c)));
    await fireEvent.press(screen.getByTestId("selecionar-todos"));
    expect(screen.getByTestId("resumo-lote").props.children).toBe("200 selecionados · 0 corrigidos");
    expect(screen.getByText("Foram selecionados os 200 primeiros. Salve e selecione os próximos.")).toBeTruthy();
    expect(screen.getByTestId("selecionar-1199").props.accessibilityState.checked).toBe(true);
    expect(screen.getByTestId("selecionar-1200").props.accessibilityState.checked).toBe(false);
  });

  it("Limpar seleção zera a seleção e as correções", async () => {
    await aberta(api(ok({})));
    await fireEvent.press(screen.getByTestId("mudar-tipo-512"));
    await fireEvent.press(screen.getByTestId("tipo-longo"));
    await fireEvent.press(screen.getByTestId("limpar-lote"));
    expect(screen.queryByTestId("barra-lote")).toBeNull();
    expect(screen.queryByTestId("corrigido-512")).toBeNull();
  });
});

describe("lote: folha de tipo", () => {
  it("abre com cinco opções em grupo de rádio e a etiqueta 'Sugerido' só na sugerida", async () => {
    await aberta(api(ok({})));
    await fireEvent.press(screen.getByTestId("mudar-tipo-511"));
    expect(screen.getByText("Tipo do treino")).toBeTruthy();
    expect(screen.getByText("Atleta Fixture Ana · Corrida de 11 de novembro")).toBeTruthy();
    for (const t of ["leve", "moderado", "longo", "intervalado", "fartlek"]) expect(screen.getByTestId(`tipo-${t}`).props.accessibilityRole).toBe("radio");
    expect(screen.getAllByText("Sugerido")).toHaveLength(1);
    expect(screen.getByTestId("tipo-intervalado").props.accessibilityLabel).toBe("Intervalado, sugerido");
    expect(screen.getByTestId("tipo-intervalado").props.accessibilityState.checked).toBe(true);
  });

  it("escolher outro tipo fecha na hora, seleciona a linha e mostra 'Corrigido para Longo'", async () => {
    await aberta(api(ok({})));
    await fireEvent.press(screen.getByTestId("mudar-tipo-511"));
    await fireEvent.press(screen.getByTestId("tipo-longo"));
    expect(screen.queryByText("Tipo do treino")).toBeNull();
    expect(screen.getByTestId("selecionar-511").props.accessibilityState.checked).toBe(true);
    expect(within(screen.getByTestId("corrigido-511")).getByText("Corrigido para Longo")).toBeTruthy();
    expect(screen.getByTestId("resumo-lote").props.children).toBe("1 selecionado · 1 corrigido");
  });

  it("escolher o sugerido equivale a confirmar sem mudar; 'Voltar à sugestão' mantém a linha selecionada", async () => {
    await aberta(api(ok({})));
    await fireEvent.press(screen.getByTestId("mudar-tipo-511"));
    await fireEvent.press(screen.getByTestId("tipo-intervalado"));
    expect(screen.queryByTestId("corrigido-511")).toBeNull();
    expect(screen.getByTestId("selecionar-511").props.accessibilityState.checked).toBe(true);
    await fireEvent.press(screen.getByTestId("mudar-tipo-511"));
    await fireEvent.press(screen.getByTestId("tipo-fartlek"));
    expect(screen.getByTestId("corrigido-511")).toBeTruthy();
    await fireEvent.press(screen.getByTestId("voltar-511"));
    expect(screen.queryByTestId("corrigido-511")).toBeNull();
    expect(screen.getByTestId("selecionar-511").props.accessibilityState.checked).toBe(true);
  });

  it("'Fechar' fecha sem mudar nada", async () => {
    await aberta(api(ok({})));
    await fireEvent.press(screen.getByTestId("mudar-tipo-511"));
    await fireEvent.press(screen.getAllByLabelText("Fechar")[1]);
    expect(screen.queryByText("Tipo do treino")).toBeNull();
    expect(screen.queryByTestId("barra-lote")).toBeNull();
  });
});

describe("lote: salvar", () => {
  it("confirmar e corrigir: o PUT leva só atividade_id e tipo_treino, na ordem da API", async () => {
    const f = api(ok({ confirmados: 1, corrigidos: 1 }));
    await aberta(f);
    await fireEvent.press(screen.getByTestId("selecionar-512"));
    await fireEvent.press(screen.getByTestId("mudar-tipo-512"));
    await fireEvent.press(screen.getByTestId("tipo-longo"));
    await fireEvent.press(screen.getByTestId("selecionar-511"));
    await fireEvent.press(screen.getByText("Salvar 2 tipos"));
    await screen.findByTestId("sucesso-lote");
    expect(puts(f)).toHaveLength(1);
    expect(puts(f)[0][0]).toBe("http://api.teste/professores/7/tipos-de-treino");
    const corpo = JSON.parse(puts(f)[0][1].body);
    expect(corpo).toEqual([
      { atividade_id: 511, tipo_treino: "intervalado" },
      { atividade_id: 512, tipo_treino: "longo" },
    ]);
    const json = JSON.stringify(corpo);
    expect(json).not.toContain("Fixture");
    expect(json).not.toContain(OBSERVACAO_MARCADOR);
  });

  it("depois de salvar: aviso de sucesso, anúncio, seleção limpa e a caixa é buscada de novo", async () => {
    const c2 = copia();
    c2.novos = [];
    let leituras = 0;
    const f = api(ok({ confirmados: 2, corrigidos: 1 }), async () => resposta(200, leituras++ === 0 ? caixa : c2));
    await aberta(f);
    await fireEvent.press(screen.getByTestId("selecionar-todos"));
    await fireEvent.press(screen.getByText("Salvar 2 tipos"));
    await waitFor(() => expect(screen.getByText("Nenhum treino novo para confirmar.")).toBeTruthy());
    expect(within(screen.getByTestId("sucesso-lote")).getByText("3 treinos salvos: 2 confirmados e 1 corrigido.")).toBeTruthy();
    expect(screen.getByTestId("anuncio").props.children).toBe("3 treinos salvos: 2 confirmados e 1 corrigido.");
    expect(screen.queryByTestId("barra-lote")).toBeNull();
    expect(gets(f)).toHaveLength(2);
    expect(screen.getByTestId("resumo").props.children).toBe("3 alunos para olhar · 0 treinos novos");
  });

  it("o anúncio é uma região viva sempre montada (Android) e só tem texto sem dado de saúde", async () => {
    await aberta(api(ok({ confirmados: 1, corrigidos: 0 })));
    const regiao = screen.getByTestId("anuncio", { includeHiddenElements: true });
    expect(regiao.props.accessibilityLiveRegion).toBe("polite");
    await fireEvent.press(screen.getByTestId("selecionar-511"));
    await fireEvent.press(screen.getByText("Salvar 1 tipo"));
    await screen.findByTestId("sucesso-lote");
    expect(screen.getByTestId("anuncio", { includeHiddenElements: true }).props.children).toBe("1 treino salvo: 1 confirmado e 0 corrigidos.");
    expect(JSON.stringify(screen.getByTestId("anuncio", { includeHiddenElements: true }).props.children)).not.toContain("MARCADOR");
  });

  it("salvando: 'Salvando...', botões e linhas desligados e nada some da tela", async () => {
    let soltar: (r: Response) => void = () => {};
    const f = api(() => new Promise<Response>((r) => (soltar = r)));
    await aberta(f);
    await fireEvent.press(screen.getByTestId("selecionar-511"));
    await fireEvent.press(screen.getByText("Salvar 1 tipo"));
    expect(screen.getByText("Salvando...")).toBeTruthy();
    expect(screen.queryByText("Salvar 1 tipo")).toBeNull();
    expect(screen.getByTestId("selecionar-511").props.accessibilityState.disabled).toBe(true);
    expect(screen.getByTestId("atualizar").props.accessibilityState.disabled).toBe(true);
    expect(screen.getByTestId("novo-512")).toBeTruthy();
    await fireEvent.press(screen.getByTestId("selecionar-todos"));
    expect(screen.getByTestId("selecionar-512").props.accessibilityState.checked).toBe(false);
    soltar(resposta(200, { confirmados: 1, corrigidos: 0 }));
    await screen.findByTestId("sucesso-lote");
  });

  it("se a nova busca falhar depois de salvar, diz que o salvo está salvo", async () => {
    let leituras = 0;
    const f = api(ok({ confirmados: 1, corrigidos: 0 }), async () => {
      if (leituras++ === 0) return resposta(200, caixa);
      throw new Error("x");
    });
    await aberta(f);
    await fireEvent.press(screen.getByTestId("selecionar-511"));
    await fireEvent.press(screen.getByText("Salvar 1 tipo"));
    await screen.findByText("Não foi possível atualizar a lista. O que você salvou está salvo.");
    expect(screen.getByTestId("sucesso-lote")).toBeTruthy();
  });
});

describe("lote: recusado (nada salvo, a seleção e as correções ficam)", () => {
  const selecionarECorrigir = async () => {
    await fireEvent.press(screen.getByTestId("selecionar-511"));
    await fireEvent.press(screen.getByTestId("mudar-tipo-512"));
    await fireEvent.press(screen.getByTestId("tipo-longo"));
    await fireEvent.press(screen.getByText("Salvar 2 tipos"));
  };

  it("404 atividade_nao_encontrada: aviso com 'Atualizar', que limpa a seleção e busca de novo", async () => {
    const f = api(async () => resposta(404, erro404));
    await aberta(f);
    await selecionarECorrigir();
    const erro = await screen.findByTestId("erro-lote");
    expect(erro.props.accessibilityRole).toBe("alert");
    expect(within(erro).getByText("Algum treino não está mais disponível para você. Nada foi salvo. Atualize a lista e escolha de novo.")).toBeTruthy();
    expect(screen.getByTestId("selecionar-511").props.accessibilityState.checked).toBe(true);
    expect(screen.getByTestId("corrigido-512")).toBeTruthy();
    expect(screen.queryByTestId("sucesso-lote")).toBeNull();
    expect(screen.getByText("Salvar 2 tipos")).toBeTruthy();
    expect(screen.getByTestId("anuncio", { includeHiddenElements: true }).props.children).toContain("Nada foi salvo");
    await fireEvent.press(within(erro).getByText("Atualizar"));
    await waitFor(() => expect(gets(f)).toHaveLength(2));
    await waitFor(() => expect(screen.queryByTestId("barra-lote")).toBeNull());
    expect(screen.queryByTestId("corrigido-512")).toBeNull();
  });

  it("422 atividade_sem_tipo: aviso com 'Atualizar'", async () => {
    await aberta(api(async () => resposta(422, erro422SemTipo)));
    await selecionarECorrigir();
    const erro = await screen.findByTestId("erro-lote");
    expect(within(erro).getByText("Algum treino não aceita tipo. Nada foi salvo. Atualize a lista.")).toBeTruthy();
    expect(within(erro).getByText("Atualizar")).toBeTruthy();
  });

  it("422 de validação: aviso genérico sem 'Atualizar'", async () => {
    await aberta(api(async () => resposta(422, { detail: [{ type: "value_error" }] })));
    await selecionarECorrigir();
    const erro = await screen.findByTestId("erro-lote");
    expect(within(erro).getByText("Algum dado do lote não foi aceito. Nada foi salvo. Tente de novo mais tarde.")).toBeTruthy();
    expect(within(erro).queryByText("Atualizar")).toBeNull();
  });

  it("rede e 5xx: 'Não foi possível falar com o servidor', e salvar de novo funciona", async () => {
    let n = 0;
    const f = api(async () => {
      if (n++ === 0) throw new Error("x");
      if (n === 2) return resposta(500, {});
      return resposta(200, { confirmados: 1, corrigidos: 1 });
    });
    await aberta(f);
    await selecionarECorrigir();
    const frase = "Não foi possível falar com o servidor. Nada foi salvo. Tente de novo.";
    expect(within(await screen.findByTestId("erro-lote")).getByText(frase)).toBeTruthy();
    await fireEvent.press(screen.getByText("Salvar 2 tipos"));
    await waitFor(() => expect(puts(f)).toHaveLength(2));
    expect(within(await screen.findByTestId("erro-lote")).getByText(frase)).toBeTruthy();
    await fireEvent.press(screen.getByText("Salvar 2 tipos"));
    await screen.findByTestId("sucesso-lote");
    expect(puts(f)).toHaveLength(3);
  });

  it("escolher de novo depois do erro tira o aviso", async () => {
    await aberta(api(async () => resposta(404, erro404)));
    await selecionarECorrigir();
    await screen.findByTestId("erro-lote");
    await fireEvent.press(screen.getByTestId("selecionar-511"));
    expect(screen.queryByTestId("erro-lote")).toBeNull();
  });
});

describe("lote: cliente e textos", () => {
  it("textoSalvo concorda no singular e no plural", () => {
    expect(textoSalvo({ confirmados: 2, corrigidos: 1 })).toBe("3 treinos salvos: 2 confirmados e 1 corrigido.");
    expect(textoSalvo({ confirmados: 1, corrigidos: 0 })).toBe("1 treino salvo: 1 confirmado e 0 corrigidos.");
  });

  it("codigoDoErro lê o type do primeiro item de detail", async () => {
    const r = await confirmarTiposDeTreino(7, [{ atividade_id: 1, tipo_treino: "leve" }], { baseUrl: "http://api.teste", fetch: (async () => resposta(404, erro404)) as unknown as typeof fetch });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(codigoDoErro(r.erro)).toBe("atividade_nao_encontrada");
    expect(codigoDoErro({ tipo: "rede", mensagem: "x" })).toBeNull();
  });

  it("422 sem corpo JSON cai no erro de validação sem código", async () => {
    const f = (async () => ({ ok: false, status: 422, json: async () => { throw new Error("x"); } }) as unknown as Response) as typeof fetch;
    const r = await confirmarTiposDeTreino(7, [{ atividade_id: 1, tipo_treino: "leve" }], { fetch: f });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.erro.tipo).toBe("http");
  });
});
