import type { EvolucaoTiros1km } from "@treino/api-client";
import { StyleSheet } from "react-native";
import { fireEvent, render, screen, within } from "@testing-library/react-native";

import exemplo from "../../../packages/api-client/exemplos/evolucao-tiros-1km.json";
import { faixasDeToque, GraficoTiros } from "../src/componentes/GraficoTiros";

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
    expect(screen.getByText("Melhor pace (min/km)")).toBeTruthy();
    expect(screen.getByText("mais rápido ↑")).toBeTruthy();
    expect(screen.getByText("FC do melhor tiro (bpm)")).toBeTruthy();
    expect(screen.getByText("04/03/25")).toBeTruthy();
    expect(screen.getByText("11/03/25")).toBeTruthy();
  });

  it("mostra os rótulos das marcas como vieram da API", async () => {
    await render(<GraficoTiros dados={base} />);
    const rotulos = [...base.eixos!.pace!.marcas, ...base.eixos!.fc!.marcas].map((m) => m.rotulo);
    expect(rotulos.length).toBeGreaterThan(0);
    for (const r of rotulos) {
      expect(screen.getByText(r)).toBeTruthy();
    }
  });

  it("mostra exatamente o rótulo trocado de propósito (o app não formata pace)", async () => {
    const d = copia();
    const original = d.eixos!.pace!.marcas[0].rotulo;
    d.eixos!.pace!.marcas[0].rotulo = "9:99";
    await render(<GraficoTiros dados={d} />);
    expect(screen.getByText("9:99")).toBeTruthy();
    expect(screen.queryByText(original)).toBeNull();
  });

  it("inverte o pace: a sessão mais rápida fica mais alta (cy menor)", async () => {
    await render(<GraficoTiros dados={base} />);
    // atividade 4 (3:57) é mais rápida que a 1 (4:11)
    expect(cy("ponto-pace-4")).toBeLessThan(cy("ponto-pace-1"));
    // FC não é invertida: 177 (melhor tiro da 4) fica mais alto que 175 (da 1)
    expect(cy("ponto-fc-4")).toBeLessThan(cy("ponto-fc-1"));
  });

  it("deixa sessão sem FC fora do painel de FC, mas no de pace", async () => {
    const d = copia();
    d.sessoes[0].fc_melhor_tiro = null;
    await render(<GraficoTiros dados={d} />);
    expect(screen.getByTestId("ponto-pace-1")).toBeTruthy();
    expect(screen.queryByTestId("ponto-fc-1")).toBeNull();
    expect(screen.getByTestId("ponto-fc-4")).toBeTruthy();
  });

  it("mostra aviso, sem quebrar, quando eixos.fc é null", async () => {
    const d = copia();
    d.eixos!.fc = null;
    for (const s of d.sessoes) s.fc_melhor_tiro = null;
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
    d.sessoes[0].fc_melhor_tiro = 170;
    d.sessoes[1].fc_melhor_tiro = 171;
    await render(<GraficoTiros dados={d} />);
    const dist = Math.abs(cy("ponto-fc-1") - cy("ponto-fc-4"));
    // painel útil = 160 - 12 - 12 = 136; 1 bpm de 5 = 20% = ~27 px
    expect(dist).toBeGreaterThan(0);
    expect(dist).toBeLessThan(136 * 0.3);
  });

  it("toque no ponto mostra o melhor tiro e a média, com rótulos claros e textos da API", async () => {
    const d = copia();
    d.sessoes[0].pace_melhor = "9:99";
    d.sessoes[0].pace_medio = "8:88";
    await render(<GraficoTiros dados={d} />);
    expect(screen.queryByTestId("detalhe-sessao")).toBeNull();
    await fireEvent.press(screen.getByTestId("toque-pace-1"));
    expect(within(screen.getByTestId("detalhe-sessao")).getByText("04/03/25 · 6 tiros")).toBeTruthy();
    expect(screen.getByText("Melhor tiro: 9:99 min/km")).toBeTruthy();
    expect(screen.getByText("FC do melhor tiro: 175 bpm")).toBeTruthy();
    expect(screen.getByText("Média dos tiros: 8:88 min/km")).toBeTruthy();
    expect(screen.getByText("FC média: 170.3 bpm")).toBeTruthy();
  });

  it("não desenha a série da média: o ponto do pace usa pace_melhor_s_km", async () => {
    const d = copia();
    d.sessoes[0].pace_medio_s_km = 999;
    const { rerender } = await render(<GraficoTiros dados={base} />);
    const antes = cy("ponto-pace-1");
    await rerender(<GraficoTiros dados={d} />);
    expect(cy("ponto-pace-1")).toBe(antes);
  });

  it("o ponto selecionado tem raio 7 e anel de 2 em cor.texto; os outros não têm anel", async () => {
    await render(<GraficoTiros dados={base} />);
    expect(screen.getByTestId("ponto-pace-1").props.stroke).toBeUndefined();
    await fireEvent.press(screen.getByTestId("toque-pace-1"));
    const sel = screen.getByTestId("ponto-pace-1").props;
    expect(Number(sel.r)).toBe(7);
    expect(sel.strokeWidth).toBe(2);
    expect(sel.stroke).toEqual({ type: 0, payload: 0xff1a1d1f }); // #1A1D1F (cor.texto)
    expect(screen.getByTestId("ponto-pace-4").props.stroke).toBeUndefined();
    expect(screen.getByTestId("ponto-fc-1").props.stroke).toEqual({ type: 0, payload: 0xff1a1d1f });
  });

  it("alvos de toque têm 44 de altura e nunca se sobrepõem, mesmo com datas coladas", async () => {
    const d = copia();
    d.sessoes[1].data = "2025-03-05";
    await render(<GraficoTiros dados={d} />);
    const faixa = (id: number) => {
      const st = StyleSheet.flatten(screen.getByTestId(`toque-pace-${id}`).props.style);
      return { esq: st.left as number, dir: (st.left as number) + (st.width as number), altura: st.height as number };
    };
    const a = faixa(1);
    const b = faixa(4);
    expect(a.altura).toBe(44);
    expect(a.dir).toBeLessThanOrEqual(b.esq + 0.001);
  });

  it("duas sessões na mesma data: as duas continuam tocáveis (24 ou mais) e a mais recente fica por cima", async () => {
    const d = copia();
    d.sessoes[1].data = d.sessoes[0].data;
    await render(<GraficoTiros dados={d} />);
    const st = (id: number) => StyleSheet.flatten(screen.getByTestId(`toque-pace-${id}`).props.style);
    expect(st(1).width).toBeGreaterThanOrEqual(24);
    expect(st(4).width).toBeGreaterThanOrEqual(24);
    expect(st(4).zIndex).toBeGreaterThan(st(1).zIndex);
    await fireEvent.press(screen.getByTestId("toque-pace-4"));
    expect(screen.getByText("Melhor tiro: 3:54 min/km")).toBeTruthy();
  });

  it("rótulo de acessibilidade do ponto traz data e o texto da API", async () => {
    await render(<GraficoTiros dados={base} />);
    expect(screen.getByLabelText("Sessão de 11/03/25, melhor tiro 3:54 min/km")).toBeTruthy();
    expect(screen.getByLabelText("Sessão de 11/03/25, FC do melhor tiro 177 bpm")).toBeTruthy();
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
    d.sessoes[0].fc_melhor_tiro = null;
    await render(<GraficoTiros dados={d} />);
    await fireEvent.press(screen.getByTestId("toque-pace-1"));
    expect(screen.getByText("FC média: sem FC")).toBeTruthy();
    expect(screen.getByText("FC do melhor tiro: sem FC")).toBeTruthy();
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
    expect(screen.getByText("Melhor tiro: 3:54 min/km")).toBeTruthy();
    expect(screen.getByText("Média dos tiros: 3:57 min/km")).toBeTruthy();
  });

  it("sem eixos ou sem sessões, mostra mensagem", async () => {
    const d = copia();
    d.eixos = null;
    d.sessoes = [];
    await render(<GraficoTiros dados={d} />);
    expect(screen.getByText("Sem sessões de tiros no período.")).toBeTruthy();
  });
});

describe("faixasDeToque", () => {
  it("sem vizinho perto, mantém 44 centrado no ponto", () => {
    expect(faixasDeToque([100, 300])).toEqual([
      { esq: 78, largura: 44 },
      { esq: 278, largura: 44 },
    ]);
  });
  it("com vizinho a 40, corta no meio do caminho", () => {
    const [a, b] = faixasDeToque([100, 140]);
    expect(a.esq + a.largura).toBe(120);
    expect(b.esq).toBe(120);
  });
  it("largura mínima de 24, mesmo com x igual (nunca 0)", () => {
    for (const f of faixasDeToque([100, 100, 105])) expect(f.largura).toBeGreaterThanOrEqual(24);
  });
});
