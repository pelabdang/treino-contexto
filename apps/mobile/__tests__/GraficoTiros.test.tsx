import type { EvolucaoTiros1km } from "@treino/api-client";
import { fireEvent, render, screen, within } from "@testing-library/react-native";

import exemplo from "../../../packages/api-client/exemplos/evolucao-tiros-1km.json";
import { GraficoTiros } from "../src/componentes/GraficoTiros";

const base = exemplo as unknown as EvolucaoTiros1km;
const copia = (): EvolucaoTiros1km => JSON.parse(JSON.stringify(base));
const cy = (id: string) => Number(screen.getByTestId(id).props.cy);

describe("GraficoTiros", () => {
  it("desenha um ponto por sessão em cada painel", async () => {
    await render(<GraficoTiros dados={base} />);
    for (const s of base.sessoes) {
      expect(screen.getByTestId(`ponto-pace-${s.atividade_id}`)).toBeTruthy();
      expect(screen.getByTestId(`ponto-fc-${s.atividade_id}`)).toBeTruthy();
    }
    expect(screen.getByText("Pace médio dos tiros (min/km)")).toBeTruthy();
    expect(screen.getByText("FC média dos tiros (bpm)")).toBeTruthy();
    expect(screen.getByText("04/03/25")).toBeTruthy();
    expect(screen.getByText("11/03/25")).toBeTruthy();
  });

  it("mostra os rótulos das marcas como vieram da API", async () => {
    await render(<GraficoTiros dados={base} />);
    for (const r of ["4:00", "4:15", "169", "170", "171", "172", "173"]) {
      expect(screen.getByText(r)).toBeTruthy();
    }
  });

  it("mostra exatamente o rótulo trocado de propósito (o app não formata pace)", async () => {
    const d = copia();
    d.eixos!.pace!.marcas[0].rotulo = "9:99";
    await render(<GraficoTiros dados={d} />);
    expect(screen.getByText("9:99")).toBeTruthy();
    expect(screen.queryByText("4:00")).toBeNull();
  });

  it("inverte o pace: a sessão mais rápida fica mais alta (cy menor)", async () => {
    await render(<GraficoTiros dados={base} />);
    // atividade 4 (3:57) é mais rápida que a 1 (4:11)
    expect(cy("ponto-pace-4")).toBeLessThan(cy("ponto-pace-1"));
    // FC não é invertida: 171,8 fica mais alto que 170,3
    expect(cy("ponto-fc-4")).toBeLessThan(cy("ponto-fc-1"));
  });

  it("deixa sessão sem FC fora do painel de FC, mas no de pace", async () => {
    const d = copia();
    d.sessoes[0].fc_media = null;
    await render(<GraficoTiros dados={d} />);
    expect(screen.getByTestId("ponto-pace-1")).toBeTruthy();
    expect(screen.queryByTestId("ponto-fc-1")).toBeNull();
    expect(screen.getByTestId("ponto-fc-4")).toBeTruthy();
  });

  it("mostra aviso, sem quebrar, quando eixos.fc é null", async () => {
    const d = copia();
    d.eixos!.fc = null;
    for (const s of d.sessoes) s.fc_media = null;
    await render(<GraficoTiros dados={d} />);
    expect(screen.getByTestId("aviso-sem-fc")).toBeTruthy();
    expect(screen.queryByTestId("painel-fc")).toBeNull();
    expect(screen.getByTestId("painel-pace")).toBeTruthy();
  });

  it("com faixa de 5 bpm, FC 170 e 171 ficam perto e não ocupam o painel todo", async () => {
    const d = copia();
    d.eixos!.fc = {
      min_bpm: 167.5,
      max_bpm: 172.5,
      marcas: [{ valor_bpm: 170, rotulo: "170" }],
    };
    d.sessoes[0].fc_media = 170;
    d.sessoes[1].fc_media = 171;
    await render(<GraficoTiros dados={d} />);
    const dist = Math.abs(cy("ponto-fc-1") - cy("ponto-fc-4"));
    // painel útil = 160 - 12 - 12 = 136; 1 bpm de 5 = 20% = ~27 px
    expect(dist).toBeGreaterThan(0);
    expect(dist).toBeLessThan(136 * 0.3);
  });

  it("toque no ponto mostra data, pace e FC como vieram da API", async () => {
    const d = copia();
    d.sessoes[0].pace_medio = "9:99";
    await render(<GraficoTiros dados={d} />);
    expect(screen.queryByTestId("detalhe-sessao")).toBeNull();
    await fireEvent.press(screen.getByTestId("toque-pace-1"));
    expect(within(screen.getByTestId("detalhe-sessao")).getByText("04/03/25")).toBeTruthy();
    expect(screen.getByText("Pace médio: 9:99 min/km")).toBeTruthy();
    expect(screen.getByText("FC média: 170.3 bpm")).toBeTruthy();
  });

  it("mostra aviso quando eixos.pace é null, e o painel de FC continua", async () => {
    const d = copia();
    d.eixos!.pace = null;
    await render(<GraficoTiros dados={d} />);
    expect(screen.getByText("Sem pace para mostrar.")).toBeTruthy();
    expect(screen.queryByTestId("painel-pace")).toBeNull();
    expect(screen.getByTestId("painel-fc")).toBeTruthy();
  });

  it("toque em sessão sem FC mostra 'sem FC'", async () => {
    const d = copia();
    d.sessoes[0].fc_media = null;
    await render(<GraficoTiros dados={d} />);
    await fireEvent.press(screen.getByTestId("toque-pace-1"));
    expect(screen.getByText("FC média: sem FC")).toBeTruthy();
  });

  it("o círculo do SVG não leva props de toque (causa do aviso onResponderTerminate na web)", async () => {
    await render(<GraficoTiros dados={base} />);
    const props = screen.getByTestId("ponto-pace-1").props;
    expect(props.onPress).toBeUndefined();
    expect(props.onResponderTerminate).toBeUndefined();
    expect(props.onResponderGrant).toBeUndefined();
  });

  it("toque no ponto do painel de FC também mostra o detalhe", async () => {
    await render(<GraficoTiros dados={base} />);
    await fireEvent.press(screen.getByTestId("toque-fc-4"));
    expect(screen.getByText("Pace médio: 3:57 min/km")).toBeTruthy();
    expect(screen.getByText("FC média: 171.8 bpm")).toBeTruthy();
  });

  it("sem eixos ou sem sessões, mostra mensagem", async () => {
    const d = copia();
    d.eixos = null;
    d.sessoes = [];
    await render(<GraficoTiros dados={d} />);
    expect(screen.getByText("Sem sessões de tiros no período.")).toBeTruthy();
  });
});
