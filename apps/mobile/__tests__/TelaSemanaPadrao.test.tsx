import { StyleSheet } from "react-native";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react-native";

import { TelaSemanaPadrao } from "../src/componentes/TelaSemanaPadrao";
import { semanaAntiga, semanaComPlano, semanaVazia } from "../__fixtures__/semanaPadrao";

// Ícone falso com nome (o real carrega a fonte e quebra no Jest).
jest.mock("@expo/vector-icons", () => {
  const { Text } = require("react-native");
  return { MaterialIcons: ({ name }: { name: string }) => <Text>{`[${name}]`}</Text> };
});

jest.setTimeout(20000);

// "Hoje" fixo: terça, 10/03/2026. A próxima segunda é 16/03/2026.
const hojeFn = () => new Date(2026, 2, 10);

const resposta = (status: number, corpo: unknown) =>
  ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;

type Roteiro = {
  get?: (url: string) => Response | Promise<Response>;
  put?: (corpo: any) => Response | Promise<Response>;
};
const fetchRoteiro = ({ get, put }: Roteiro) =>
  jest.fn(async (url: any, init?: any) => {
    if (init?.method === "PUT") return put!(JSON.parse(init.body));
    return get!(String(url));
  }) as unknown as typeof fetch & jest.Mock;

const gravada = (n: number, extra: object = {}) => ({
  vigente_desde: "2026-03-10",
  definido_por: "atleta",
  definido_em: "2026-03-10T10:00:00-03:00",
  itens: [{ dia_semana: 1, dia_semana_texto: "segunda", modalidade: "corrida", tipo_treino: null }],
  atividades_reaplicadas: n,
  ...extra,
});

const tela = (f: typeof fetch, extra = {}) => (
  <TelaSemanaPadrao apiUrl="http://api.teste" atletaId={1} fetchFn={f} hojeFn={hojeFn} {...extra} />
);
const comPlano = (extra: Roteiro = {}) => fetchRoteiro({ get: () => resposta(200, semanaComPlano), ...extra });
const vazio = (extra: Roteiro = {}) => fetchRoteiro({ get: () => resposta(200, semanaVazia), ...extra });

async function montarVazioComUmTreino(f: typeof fetch) {
  await render(tela(f));
  await fireEvent.press(await screen.findByText("Montar minha semana"));
  await fireEvent.press(screen.getByTestId("adicionar-1"));
  await fireEvent.press(screen.getByLabelText("Corrida"));
}

describe("tela da semana-padrão", () => {
  it("chama a API da semana-padrão do atleta, sem `em`", async () => {
    const f = comPlano();
    await render(tela(f));
    await screen.findByTestId("formulario");
    expect(f.mock.calls[0][0]).toBe("http://api.teste/atletas/1/semana-padrao");
  });

  describe("carregando", () => {
    it("mostra o texto, o esqueleto e nenhum botão Salvar", async () => {
      await render(tela(jest.fn(() => new Promise<Response>(() => {})) as unknown as typeof fetch));
      expect(screen.getByText("Carregando a semana\u2011padrão...")).toBeTruthy();
      expect(screen.getByTestId("esqueleto-semana-padrao", { includeHiddenElements: true })).toBeTruthy();
      expect(screen.queryByTestId("salvar")).toBeNull();
    });
  });

  describe("vazio", () => {
    it("sem plano nem histórico: convite e um só botão primário", async () => {
      await render(tela(vazio()));
      const estado = await screen.findByTestId("estado-vazio");
      expect(within(estado).getByText("[event-note]")).toBeTruthy();
      expect(within(estado).getByText("Você ainda não definiu sua semana\u2011padrão")).toBeTruthy();
      // hífen sem quebra só no texto visível; o leitor de tela recebe o hífen comum
      const titulo = within(estado).getByRole("header");
      expect(titulo.props.accessibilityLabel).toBe("Você ainda não definiu sua semana-padrão");
      expect(titulo.props.accessibilityLabel).not.toContain("\u2011");
      expect(screen.queryByTestId("salvar")).toBeNull();
    });

    it("'Montar minha semana' abre o formulário com sete dias vazios, 'Eu' marcada e a data de hoje", async () => {
      await render(tela(vazio()));
      await fireEvent.press(await screen.findByText("Montar minha semana"));
      expect(screen.getByTestId("campo-data").props.value).toBe("10/03/2026");
      expect(screen.getByRole("radio", { name: "Eu" }).props.accessibilityState.checked).toBe(true);
      expect(screen.getAllByText("Sem treino")).toHaveLength(7);
      expect(screen.getByText("Nada mudou ainda.")).toBeTruthy();
    });

    it("sem treino nenhum e sem plano, o botão fica desligado pedindo um treino", async () => {
      const f = vazio();
      await render(tela(f));
      await fireEvent.press(await screen.findByText("Montar minha semana"));
      await fireEvent.press(screen.getByTestId("adicionar-1"));
      await fireEvent.press(screen.getByLabelText("Corrida"));
      await fireEvent.press(screen.getByTestId("remover-1-corrida"));
      expect(screen.getByText("Nada mudou ainda.")).toBeTruthy();
    });

    it("histórico só com semana futura: mostra o formulário, não o vazio", async () => {
      const futura = { ...semanaVazia, vigencias: [{ vigente_desde: "2026-04-06", definido_por: "atleta", total_itens: 3 }] };
      await render(tela(fetchRoteiro({ get: () => resposta(200, futura) })));
      await screen.findByTestId("formulario");
      expect(screen.queryByTestId("estado-vazio")).toBeNull();
      expect(screen.getByText("Ainda não começou")).toBeTruthy();
    });
  });

  describe("editando", () => {
    it("mostra a semana vigente, o histórico e o Salvar desligado até mudar algo", async () => {
      await render(tela(comPlano()));
      await screen.findByTestId("formulario");
      expect(screen.getByTestId("campo-data").props.value).toBe("10/03/2026");
      expect(within(screen.getByTestId("dia-1")).getByText("Natação")).toBeTruthy();
      expect(within(screen.getByTestId("dia-1")).getByText("1 treino")).toBeTruthy();
      expect(within(screen.getByTestId("dia-2")).getByText("Fartlek")).toBeTruthy();
      expect(within(screen.getByTestId("dia-3")).getByText("Sem treino")).toBeTruthy();
      expect(screen.getByTestId("salvar").props.accessibilityState.disabled).toBe(true);
      expect(screen.getByText("Nada mudou ainda.")).toBeTruthy();
      expect(screen.getByText("Em vigor")).toBeTruthy();
      expect(screen.getByText("Treinador · 1 treino por semana")).toBeTruthy();
      expect(screen.getByText("Só registra de quem é o plano. O app ainda não tem login.")).toBeTruthy();
    });

    it("adicionar oferece só as modalidades que faltam e some com as três usadas", async () => {
      await render(tela(comPlano()));
      await screen.findByTestId("formulario");
      await fireEvent.press(screen.getByTestId("adicionar-1"));
      expect(screen.queryByLabelText("Natação")).toBeNull();
      expect(screen.getByLabelText("Corrida")).toBeTruthy();
      await fireEvent.press(screen.getByLabelText("Corrida"));
      await fireEvent.press(screen.getByTestId("adicionar-1"));
      await fireEvent.press(screen.getByLabelText("Ciclismo"));
      expect(screen.queryByTestId("adicionar-1")).toBeNull();
      expect(within(screen.getByTestId("dia-1")).getByText("3 treinos")).toBeTruthy();
      expect(screen.getByTestId("salvar").props.accessibilityState.disabled).toBe(false);
    });

    it("trocar o tipo pela lista de seis opções liga o Salvar; voltar ao original desliga", async () => {
      await render(tela(comPlano()));
      await screen.findByTestId("formulario");
      await fireEvent.press(screen.getByTestId("tipo-2-corrida"));
      for (const t of ["Sem tipo", "Leve", "Moderado", "Longo", "Intervalado", "Fartlek"]) {
        expect(screen.getByLabelText(t)).toBeTruthy();
      }
      await fireEvent.press(screen.getByLabelText("Intervalado"));
      expect(within(screen.getByTestId("dia-2")).getByText("Intervalado")).toBeTruthy();
      expect(screen.getByTestId("salvar").props.accessibilityState.disabled).toBe(false);
      await fireEvent.press(screen.getByTestId("tipo-2-corrida"));
      await fireEvent.press(screen.getByLabelText("Fartlek"));
      expect(screen.getByTestId("salvar").props.accessibilityState.disabled).toBe(true);
    });

    it("remover tira o item na hora, sem confirmação", async () => {
      await render(tela(comPlano()));
      await screen.findByTestId("formulario");
      await fireEvent.press(screen.getByTestId("remover-2-corrida"));
      expect(within(screen.getByTestId("dia-2")).getByText("Sem treino")).toBeTruthy();
      expect(screen.queryByText("Sair sem salvar?")).toBeNull();
    });

    it("rótulos de acessibilidade levam o dia e a modalidade", async () => {
      await render(tela(comPlano()));
      await screen.findByTestId("formulario");
      expect(screen.getByLabelText("Remover corrida de terça")).toBeTruthy();
      expect(screen.getByLabelText("Tipo do treino de corrida na terça, fartlek, botão")).toBeTruthy();
      expect(screen.getByLabelText("Adicionar treino na quarta")).toBeTruthy();
      expect(screen.getByLabelText("Adicionar treino no domingo")).toBeTruthy();
    });

    it("remover tudo com plano vigente avisa que o plano acaba, e o Salvar fica ligado", async () => {
      await render(tela(comPlano()));
      await screen.findByTestId("formulario");
      await fireEvent.press(screen.getByTestId("remover-1-natacao"));
      await fireEvent.press(screen.getByTestId("remover-2-corrida"));
      expect(screen.getByText(/Sem nenhum treino, o plano acaba em 10\/03\/26/)).toBeTruthy();
      expect(screen.getByTestId("salvar").props.accessibilityState.disabled).toBe(false);
    });

    it("'Treinador' troca a seleção (ícone e estado)", async () => {
      await render(tela(comPlano()));
      await screen.findByTestId("formulario");
      await fireEvent.press(screen.getByRole("radio", { name: "Treinador" }));
      expect(screen.getByRole("radio", { name: "Treinador" }).props.accessibilityState.checked).toBe(true);
      expect(screen.getByRole("radio", { name: "Eu" }).props.accessibilityState.checked).toBe(false);
      expect(screen.getByTestId("salvar").props.accessibilityState.disabled).toBe(false);
    });
  });

  describe("layout", () => {
    it("a folha de opções fecha com o ícone close", async () => {
      await render(tela(comPlano()));
      await screen.findByTestId("formulario");
      await fireEvent.press(screen.getByTestId("adicionar-1"));
      expect(screen.getByText("[close]")).toBeTruthy();
      await fireEvent.press(screen.getByRole("button", { name: "Fechar" }));
      expect(screen.queryByText("Qual modalidade?")).toBeNull();
    });

    it("o chip de cada modalidade tem a mesma largura mínima (seletores alinhados)", async () => {
      await render(tela(comPlano()));
      await screen.findByTestId("formulario");
      const larg = (id: string) => StyleSheet.flatten(screen.getByTestId(id).props.style).minWidth;
      expect(larg("chip-1-natacao")).toBe(larg("chip-2-corrida"));
      expect(larg("chip-2-corrida")).toBeGreaterThanOrEqual(96);
    });

    it("com fonte grande o seletor desce de linha: a linha do item quebra e o seletor tem largura mínima", async () => {
      await render(tela(comPlano()));
      await screen.findByTestId("formulario");
      const item = screen.getByTestId("tipo-2-corrida").parent!;
      expect(StyleSheet.flatten(item.props.style).flexWrap).toBe("wrap");
      const seletor = StyleSheet.flatten(screen.getByTestId("tipo-2-corrida").props.style) as { minWidth: number; flex: number };
      expect(seletor.minWidth).toBe(120);
      expect(seletor.flex).toBe(1);
    });

    it("a barra de salvar tem a largura da coluna do conteúdo, centralizada", async () => {
      await render(tela(comPlano()));
      await screen.findByTestId("formulario");
      const barra = StyleSheet.flatten(screen.getByTestId("barra-salvar").props.style);
      expect([720 + 2 * 16, 720 + 2 * 24]).toContain(barra.maxWidth);
      expect(barra.alignSelf).toBe("center");
    });
  });

  describe("campo de data", () => {
    it("aplica a máscara dd/mm/aaaa e ignora o que não é dígito", async () => {
      await render(tela(comPlano()));
      await screen.findByTestId("formulario");
      await fireEvent.changeText(screen.getByTestId("campo-data"), "1a5b0c42d0e26f9");
      expect(screen.getByTestId("campo-data").props.value).toBe("15/04/2026");
    });

    it("atalhos 'Hoje' e 'Próxima segunda'", async () => {
      await render(tela(comPlano()));
      await screen.findByTestId("formulario");
      await fireEvent.press(screen.getByText("Próxima segunda"));
      expect(screen.getByTestId("campo-data").props.value).toBe("16/03/2026");
      expect(screen.getByText("Esta semana começa a valer em 16/03/26. Até lá, nada muda.")).toBeTruthy();
      await fireEvent.press(screen.getByText("Hoje"));
      expect(screen.getByTestId("campo-data").props.value).toBe("10/03/2026");
      expect(screen.queryByTestId("aviso-data-futura")).toBeNull();
    });

    it("avisa quando a data coincide com uma vigência existente", async () => {
      await render(tela(comPlano()));
      await screen.findByTestId("formulario");
      expect(screen.queryByTestId("aviso-data-existe")).toBeNull();
      await fireEvent.changeText(screen.getByTestId("campo-data"), "02/03/2026");
      expect(screen.getByText("Já existe uma semana que vale desde esta data. Salvar vai substituí-la.")).toBeTruthy();
    });

    it("data vazia ou impossível não envia e mostra o erro em texto", async () => {
      const f = comPlano();
      await render(tela(f));
      await screen.findByTestId("formulario");
      await fireEvent.changeText(screen.getByTestId("campo-data"), "");
      await fireEvent.press(screen.getByTestId("salvar"));
      expect(screen.getByText("Digite a data em que a semana começa a valer.")).toBeTruthy();
      await fireEvent.changeText(screen.getByTestId("campo-data"), "31022026");
      await fireEvent.press(screen.getByTestId("salvar"));
      expect(screen.getByText("Digite uma data que exista, como 02/03/2026.")).toBeTruthy();
      expect(f.mock.calls.filter((c) => c[1]?.method === "PUT")).toHaveLength(0);
    });
  });

  describe("salvando e salvo", () => {
    it("envia o PUT com data, quem definiu e itens (tipo nulo para 'Sem tipo')", async () => {
      const f = vazio({ put: () => resposta(200, gravada(0)) });
      await montarVazioComUmTreino(f);
      await fireEvent.press(screen.getByRole("radio", { name: "Treinador" }));
      await fireEvent.press(screen.getByTestId("salvar"));
      await screen.findByTestId("aviso");
      const put = f.mock.calls.find((c) => c[1]?.method === "PUT")!;
      expect(put[0]).toBe("http://api.teste/atletas/1/semana-padrao");
      expect(JSON.parse(put[1].body)).toEqual({
        vigente_desde: "2026-03-10",
        definido_por: "professor",
        itens: [{ dia_semana: 1, modalidade: "corrida", tipo_treino: null }],
      });
    });

    it("salvando: botão 'Salvando...' desligado, campos desligados; clique duplo não duplica", async () => {
      let liberar!: (r: Response) => void;
      const f = vazio({ put: () => new Promise<Response>((r) => (liberar = r)) });
      await montarVazioComUmTreino(f);
      void fireEvent.press(screen.getByTestId("salvar")); // não espera: o PUT fica pendente de propósito
      expect(await screen.findByText("Salvando...")).toBeTruthy();
      await fireEvent.press(screen.getByTestId("salvar"));
      expect(screen.getByTestId("salvar").props.accessibilityState.disabled).toBe(true);
      expect(screen.getByTestId("campo-data").props.editable).toBe(false);
      expect(f.mock.calls.filter((c) => c[1]?.method === "PUT")).toHaveLength(1);
      liberar(resposta(200, gravada(0)));
      await screen.findByText("Semana salva. Nenhum treino mudou de tipo.");
    });

    it.each([
      [0, "Semana salva. Nenhum treino mudou de tipo."],
      [1, "Semana salva. 1 treino reclassificado."],
      [5, "Semana salva. 5 treinos reclassificados."],
    ])("salvo com %i treinos reclassificados: o número vem da API", async (n, texto) => {
      const f = vazio({ put: () => resposta(200, gravada(n)) });
      await montarVazioComUmTreino(f);
      await fireEvent.press(screen.getByTestId("salvar"));
      expect(await screen.findByText(texto)).toBeTruthy();
      expect(screen.getByText("Treinos anteriores a 10/03/26 não foram alterados.")).toBeTruthy();
      // volta a ficar desligado e o formulário mostra o que a API devolveu
      expect(screen.getByTestId("salvar").props.accessibilityState.disabled).toBe(true);
    });

    it("salvo: atualiza o histórico buscando a API de novo", async () => {
      let salvou = false;
      const f = fetchRoteiro({
        get: () => resposta(200, salvou ? semanaComPlano : semanaVazia),
        put: () => {
          salvou = true;
          return resposta(200, gravada(2));
        },
      });
      await montarVazioComUmTreino(f);
      await fireEvent.press(screen.getByTestId("salvar"));
      await screen.findByText("Semana salva. 2 treinos reclassificados.");
      await waitFor(() => expect(screen.getByTestId("historico")).toBeTruthy());
    });

    it("salvo com data futura e com plano encerrado têm textos próprios", async () => {
      const futuro = vazio({ put: () => resposta(200, gravada(0, { vigente_desde: "2026-03-16" })) });
      await montarVazioComUmTreino(futuro);
      await fireEvent.press(screen.getByText("Próxima segunda"));
      await fireEvent.press(screen.getByTestId("salvar"));
      await screen.findByText("Semana salva. Ela passa a valer em 16/03/26; nenhum treino muda até lá.");
    });

    it("plano encerrado: envia itens vazios e diz que o plano acabou", async () => {
      const f = comPlano({ put: () => resposta(200, gravada(3, { itens: [] })) });
      await render(tela(f));
      await screen.findByTestId("formulario");
      await fireEvent.press(screen.getByTestId("remover-1-natacao"));
      await fireEvent.press(screen.getByTestId("remover-2-corrida"));
      await fireEvent.press(screen.getByTestId("salvar"));
      await screen.findByText("Plano encerrado a partir de 10/03/26. 3 treinos reclassificados.");
      const put = f.mock.calls.find((c) => c[1]?.method === "PUT")!;
      expect(JSON.parse(put[1].body).itens).toEqual([]);
    });

    it("o aviso some na próxima mudança do formulário", async () => {
      const f = vazio({ put: () => resposta(200, gravada(0)) });
      await montarVazioComUmTreino(f);
      await fireEvent.press(screen.getByTestId("salvar"));
      await screen.findByTestId("aviso");
      await fireEvent.press(screen.getByRole("radio", { name: "Treinador" }));
      expect(screen.queryByTestId("aviso")).toBeNull();
    });
  });

  describe("erros ao carregar", () => {
    it("rede: wifi-off, alerta e 'Tentar de novo' que busca de novo", async () => {
      const f = jest
        .fn()
        .mockRejectedValueOnce(new Error("x"))
        .mockResolvedValue(resposta(200, semanaComPlano)) as unknown as typeof fetch & jest.Mock;
      await render(tela(f));
      const erro = await screen.findByTestId("estado-erro");
      expect(within(erro).getByText("[wifi-off]")).toBeTruthy();
      expect(within(erro).getByRole("alert")).toBeTruthy();
      expect(within(erro).getByText("Não foi possível falar com o servidor")).toBeTruthy();
      await fireEvent.press(within(erro).getByText("Tentar de novo"));
      await screen.findByTestId("formulario");
      expect(f).toHaveBeenCalledTimes(2);
    });

    it("404: 'Atleta não encontrado' sem botão de tentar de novo", async () => {
      await render(tela(fetchRoteiro({ get: () => resposta(404, { detail: "atleta não encontrado" }) })));
      const erro = await screen.findByTestId("estado-erro");
      expect(within(erro).getByText("[error-outline]")).toBeTruthy();
      expect(within(erro).getByText("Atleta não encontrado")).toBeTruthy();
      expect(within(erro).queryByText("Tentar de novo")).toBeNull();
    });

    it("500: frase genérica", async () => {
      await render(tela(fetchRoteiro({ get: () => resposta(500, {}) })));
      expect(await screen.findByText("Não foi possível carregar a semana\u2011padrão. Tente de novo mais tarde.")).toBeTruthy();
      expect(screen.getByRole("alert").props.accessibilityLabel).toBe("Não foi possível carregar a semana-padrão. Tente de novo mais tarde.");
    });
  });

  describe("erros ao salvar", () => {
    const alterar = async (f: typeof fetch) => {
      await render(tela(f));
      await screen.findByTestId("formulario");
      await fireEvent.press(screen.getByTestId("remover-2-corrida"));
      await fireEvent.press(screen.getByTestId("salvar"));
    };

    it("rede: as mudanças continuam na tela e o botão volta a ligar", async () => {
      await alterar(comPlano({ put: () => Promise.reject(new Error("x")) }));
      const aviso = await screen.findByTestId("aviso");
      expect(within(aviso).getByText("Não foi possível falar com o servidor. Suas mudanças continuam aqui. Tente salvar de novo.")).toBeTruthy();
      expect(aviso.props.accessibilityRole).toBe("alert");
      expect(within(screen.getByTestId("dia-2")).getByText("Sem treino")).toBeTruthy();
      expect(screen.getByTestId("salvar").props.accessibilityState.disabled).toBe(false);
    });

    it("422: texto da tela, nunca o detail técnico da API", async () => {
      await alterar(comPlano({ put: () => resposta(422, { detail: [{ loc: ["body", "itens"], msg: "tecnico", type: "x" }] }) }));
      expect(
        await screen.findByText("Algum dado da semana não foi aceito. Confira a data e os treinos de cada dia e tente de novo."),
      ).toBeTruthy();
      expect(screen.queryByText(/tecnico/)).toBeNull();
      expect(within(screen.getByTestId("dia-2")).getByText("Sem treino")).toBeTruthy();
    });

    it("404: 'Atleta não encontrado.'", async () => {
      await alterar(comPlano({ put: () => resposta(404, { detail: "atleta não encontrado" }) }));
      expect(await screen.findByText("Atleta não encontrado.")).toBeTruthy();
    });

    it("outro erro: frase genérica", async () => {
      await alterar(comPlano({ put: () => resposta(500, {}) }));
      expect(await screen.findByText("Não foi possível salvar. Tente de novo mais tarde.")).toBeTruthy();
    });
  });

  describe("histórico", () => {
    const antiga = () =>
      comPlano({
        get: (url) => resposta(200, url.includes("em=2026-02-02") ? semanaAntiga : semanaComPlano),
      });

    it("tocar numa semana antiga só copia para o formulário (GET ?em=) e não grava", async () => {
      const f = antiga();
      await render(tela(f));
      await screen.findByTestId("formulario");
      await fireEvent.press(screen.getByTestId("vigencia-2026-02-02"));
      await screen.findByText(
        "Semana de 02/02/26 copiada. Salvar cria uma semana nova a partir de 10/03/26.",
      );
      expect(f.mock.calls.some((c) => String(c[0]).endsWith("?em=2026-02-02"))).toBe(true);
      expect(f.mock.calls.some((c) => c[1]?.method === "PUT")).toBe(false);
      expect(within(screen.getByTestId("dia-3")).getByText("Longo")).toBeTruthy();
      expect(within(screen.getByTestId("dia-2")).getByText("Sem treino")).toBeTruthy();
      expect(screen.getByRole("radio", { name: "Treinador" }).props.accessibilityState.checked).toBe(true);
      expect(screen.getByTestId("campo-data").props.value).toBe("10/03/2026");
      expect(screen.getByTestId("salvar").props.accessibilityState.disabled).toBe(false);
    });

    it("com mudanças não salvas pede confirmação antes de copiar", async () => {
      const f = antiga();
      await render(tela(f));
      await screen.findByTestId("formulario");
      await fireEvent.press(screen.getByTestId("remover-2-corrida"));
      await fireEvent.press(screen.getByTestId("vigencia-2026-02-02"));
      expect(screen.getByText("Copiar esta semana?")).toBeTruthy();
      expect(screen.getByText("As mudanças que você fez serão trocadas pela semana de 02/02/26.")).toBeTruthy();
      await fireEvent.press(screen.getByText("Continuar editando"));
      expect(screen.queryByText("Copiar esta semana?")).toBeNull();
      expect(within(screen.getByTestId("dia-3")).getByText("Sem treino")).toBeTruthy();
      await fireEvent.press(screen.getByTestId("vigencia-2026-02-02"));
      await fireEvent.press(screen.getByText("Copiar"));
      await screen.findByText(/copiada/);
      expect(within(screen.getByTestId("dia-3")).getByText("Longo")).toBeTruthy();
    });
  });

  describe("voltar", () => {
    it("sem mudanças volta direto", async () => {
      const aoVoltar = jest.fn();
      await render(tela(comPlano(), { aoVoltar }));
      await screen.findByTestId("formulario");
      await fireEvent.press(screen.getByLabelText("Voltar"));
      expect(aoVoltar).toHaveBeenCalledTimes(1);
    });

    it("com mudanças pergunta; 'Continuar editando' fica e 'Sair sem salvar' sai", async () => {
      const aoVoltar = jest.fn();
      await render(tela(comPlano(), { aoVoltar }));
      await screen.findByTestId("formulario");
      await fireEvent.press(screen.getByTestId("remover-2-corrida"));
      await fireEvent.press(screen.getByLabelText("Voltar"));
      expect(screen.getByText("Sair sem salvar?")).toBeTruthy();
      expect(screen.getByText("As mudanças desta semana serão perdidas.")).toBeTruthy();
      expect(aoVoltar).not.toHaveBeenCalled();
      await fireEvent.press(screen.getByText("Continuar editando"));
      expect(aoVoltar).not.toHaveBeenCalled();
      await fireEvent.press(screen.getByLabelText("Voltar"));
      await fireEvent.press(screen.getByText("Sair sem salvar"));
      expect(aoVoltar).toHaveBeenCalledTimes(1);
    });
  });
});
