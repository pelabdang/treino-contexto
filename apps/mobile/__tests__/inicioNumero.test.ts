import type { Atividade } from "@treino/api-client";

import { atividades } from "../__fixtures__/atividades";
import { diaCurto, hojePorExtenso } from "../src/componentes/datasInicio";
import { linhaDeApoio, numeroDoTreino, primeirasLinhas, seloDoNormal } from "../src/inicio/numero";

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
