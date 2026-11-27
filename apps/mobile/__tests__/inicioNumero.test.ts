import type { Atividade } from "@treino/api-client";

import { atividades } from "../__fixtures__/atividades";
import { diaCurto, hojePorExtenso } from "../src/componentes/datasInicio";
import { estadoDoNormal, linhaDeApoio, numeroDoTreino, primeirasLinhas, seloDoNormal } from "../src/inicio/numero";

describe("número do treino", () => {
  it("corrida intervalada: o melhor tiro (menor pace entre os esforços), texto da API", () => {
    const a = {
      ...atividades.comEsforcos,
      tipo_treino: "intervalado",
      esforcos: {
        ...atividades.comEsforcos.esforcos!,
        blocos: atividades.comEsforcos.esforcos!.blocos.map((b, i) => (b.categoria === "esforco" ? { ...b, pace: `4:${10 + i} min/km`, pace_s_km: 250 - i * 3 } : b)),
      },
    } as Atividade;
    const n = numeroDoTreino(a);
    const esforcos = a.esforcos!.blocos.filter((b) => b.categoria === "esforco");
    const melhor = esforcos.reduce((x, y) => (y.pace_s_km! < x.pace_s_km! ? y : x));
    expect(n.rotulo).toBe("Melhor tiro");
    expect(n.valor).toBe(melhor.pace!.split(" ")[0]);
    expect(n.unidade).toBe("min/km");
  });

  it("outras corridas: pace médio; natação e ciclismo: duração", () => {
    expect(numeroDoTreino(atividades.ok)).toEqual({ valor: "5:12", unidade: null, rotulo: "Pace médio" });
    expect(numeroDoTreino({ ...atividades.ok, pace_medio: "5:12 min/km" })).toEqual({ valor: "5:12", unidade: "min/km", rotulo: "Pace médio" });
    expect(numeroDoTreino({ ...atividades.ok, modalidade: "natacao", pace_medio: null })).toEqual({ valor: "0:52:05", unidade: null, rotulo: "Duração" });
    expect(numeroDoTreino({ ...atividades.ok, modalidade: "ciclismo" }).rotulo).toBe("Duração");
  });

  it("intervalada sem blocos de esforço cai no pace médio", () => {
    expect(numeroDoTreino({ ...atividades.ok, tipo_treino: "intervalado" }).rotulo).toBe("Pace médio");
  });

  it("linha de apoio: só o que existe", () => {
    expect(linhaDeApoio(atividades.ok)).toBe("10,00 km · 0:52:05 · FC média 152 bpm");
    expect(linhaDeApoio({ ...atividades.ok, distancia: null, fc_media: null })).toBe("0:52:05");
  });
});

describe("selo do normal", () => {
  it("dentro, fora (com a diferença da API) e aprendendo", () => {
    expect(seloDoNormal(atividades.ok)).toEqual({ tipo: "dentro", texto: "Dentro do seu normal" });
    expect(seloDoNormal(atividades.normalFora)).toEqual({ tipo: "fora", texto: "Fora do seu normal: 25 s/km mais rápido" });
    expect(seloDoNormal(atividades.normalAprendendo)).toEqual({ tipo: "aprendendo", texto: "3 de 8 treinos do tipo leve nas últimas 12 semanas." });
  });

  it("pace dentro e FC fora: o treino está FORA (regra normal_treino@1), com a diferença da métrica que está fora", () => {
    const a = {
      ...atividades.ok,
      linha_base: {
        ...atividades.ok.linha_base!,
        metricas: [
          { ...atividades.ok.linha_base!.metricas[0], chave: "pace_medio", estado: "dentro" },
          { ...atividades.ok.linha_base!.metricas[1], chave: "fc_media", estado: "fora", diferenca_texto: "11 bpm acima" },
        ],
      },
    } as Atividade;
    expect(estadoDoNormal(a)).toBe("fora");
    expect(seloDoNormal(a)).toEqual({ tipo: "fora", texto: "Fora do seu normal: 11 bpm acima" });
  });

  it("alguma fora vence dentro e aprendendo; dentro vence aprendendo; sem_valor é ignorada", () => {
    const com = (estados: string[]) =>
      ({ ...atividades.ok, linha_base: { ...atividades.ok.linha_base!, metricas: estados.map((e, i) => ({ ...atividades.ok.linha_base!.metricas[0], chave: (["melhor_pace", "pace_medio", "fc_media", "fc_melhor_tiro"] as const)[i], estado: e })) } }) as Atividade;
    expect(estadoDoNormal(com(["aprendendo", "dentro", "fora"]))).toBe("fora");
    expect(estadoDoNormal(com(["aprendendo", "dentro"]))).toBe("dentro");
    expect(estadoDoNormal(com(["sem_valor", "aprendendo"]))).toBe("aprendendo");
    expect(estadoDoNormal(com(["sem_valor"]))).toBeNull();
  });

  it("em 'fora', o texto vem da primeira métrica fora na ordem de preferência", () => {
    const base = atividades.ok.linha_base!.metricas[0];
    const a = { ...atividades.ok, linha_base: { ...atividades.ok.linha_base!, metricas: [
      { ...base, chave: "fc_media", estado: "fora", diferenca_texto: "FC acima" },
      { ...base, chave: "pace_medio", estado: "fora", diferenca_texto: "pace mais rápido" },
    ] } } as Atividade;
    expect(seloDoNormal(a)?.texto).toBe("Fora do seu normal: pace mais rápido");
  });

  it("o normal_estado da lista manda no tipo (mesma conta nas duas telas); null da lista = sem selo", () => {
    expect(seloDoNormal(atividades.ok, "fora")?.tipo).toBe("fora");
    expect(seloDoNormal(atividades.normalFora, "dentro")).toEqual({ tipo: "dentro", texto: "Dentro do seu normal" });
    expect(seloDoNormal(atividades.ok, null)).toBeNull();
  });

  it("sem linha de base ou sem cálculo: sem selo", () => {
    expect(seloDoNormal(atividades.normalSemTipo)).toBeNull();
    expect(seloDoNormal({ ...atividades.ok, linha_base: null })).toBeNull();
  });
});

describe("textos", () => {
  it("três primeiras linhas do feedback, ignorando linhas vazias", () => {
    expect(primeirasLinhas("a\n\nb\nc\nd")).toBe("a\nb\nc");
  });
  it("datas curtas em português", () => {
    expect(diaCurto("2025-03-18")).toBe("ter 18/03");
    expect(diaCurto("2025-03-15")).toBe("sáb 15/03");
    expect(hojePorExtenso(new Date(2025, 2, 21))).toBe("sexta, 21/03");
  });
});
