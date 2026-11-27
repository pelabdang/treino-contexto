import type { CatalogoSeries, PontoSerie, SerieCatalogo, SerieEvolucao } from "@treino/api-client";

// Séries sintéticas da Evolução v1 (ADR 0004, adendo 15): textos prontos, como a API manda. Atleta e datas inventados.

const ponto = (i: number, extra: Partial<PontoSerie> = {}): PontoSerie => ({
  atividade_id: 100 + i,
  data: `2025-03-${String(2 + i * 4).padStart(2, "0")}`,
  data_texto: `ter ${String(2 + i * 4).padStart(2, "0")}/03`,
  valor: 340 + i,
  valor_texto: `5:${40 + i}`,
  melhor: false,
  fora_do_normal: false,
  normal_estado: "dentro",
  aprendendo: false,
  parcial: false,
  rotulo: `Treino de ${String(2 + i * 4).padStart(2, "0")}/03, 5:${40 + i} por quilômetro, dentro do seu normal`,
  ...extra,
});

export const serieCatalogo: Record<string, SerieCatalogo> = {
  pace: { id: "corrida.pace.leve", titulo: "Pace dos treinos leves", descricao: "Quanto tempo você leva por quilômetro nos treinos leves", modalidade: "corrida", grupo: "Ritmo", n_pontos: 4, disponivel: true, motivo: null },
  tiros: { id: "corrida.tiros", titulo: "Melhor tiro de 1 km", descricao: "O seu tiro mais rápido de cada sessão", modalidade: "corrida", grupo: "Ritmo", n_pontos: 2, disponivel: false, motivo: "Poucos treinos de tiros nas últimas 12 semanas" },
  fc: { id: "corrida.fc.moderado", titulo: "FC dos treinos moderados", descricao: "A frequência cardíaca média nos treinos moderados", modalidade: "corrida", grupo: "Coração", n_pontos: 9, disponivel: true, motivo: null },
  volume: { id: "corrida.volume_km", titulo: "Volume por semana", descricao: "Quantos quilômetros você correu em cada semana", modalidade: "corrida", grupo: "Esforço e volume", n_pontos: 12, disponivel: true, motivo: null },
  natacao: { id: "natacao.ritmo", titulo: "Ritmo na piscina", descricao: "Tempo por 100 m, com pausas", modalidade: "natacao", grupo: "Ritmo", n_pontos: 9, disponivel: true, motivo: null },
};

export const catalogo: CatalogoSeries = {
  atleta_id: 1,
  serie_padrao: "corrida.pace.leve",
  series: [serieCatalogo.pace, serieCatalogo.tiros, serieCatalogo.fc, serieCatalogo.volume, serieCatalogo.natacao],
};

export const paceLeve: SerieEvolucao = {
  atleta_id: 1,
  id: "corrida.pace.leve",
  titulo: "Pace dos treinos leves",
  descricao: serieCatalogo.pace.descricao,
  modalidade: "corrida",
  grupo: "Ritmo",
  periodo: "12s",
  inicio: "2024-12-26",
  fim: "2025-03-20",
  unidade: "/km",
  versao_calculo: "evolucao_serie@1",
  pontos: [
    ponto(0),
    ponto(1, { valor: 355, valor_texto: "5:55", fora_do_normal: true, normal_estado: "fora", rotulo: "Treino de 06/03, 5:55 por quilômetro, fora do seu normal" }),
    ponto(2, { melhor: true, valor: 332, valor_texto: "5:32", rotulo: "Treino de 10/03, 5:32 por quilômetro, o melhor do período, dentro do seu normal" }),
    ponto(3),
  ],
  ultimo_valor_texto: "5:43",
  ultimo_rotulo: "último treino, qui 14/03",
  referencia: { minimo: 335, maximo: 350, mediana: 342, n: 9, texto: "Seu normal 5:35 a 5:50" },
  aprendendo_texto: null,
  eixo: { minimo: 325, maximo: 360, invertido: true, marcas: [{ valor: 330, rotulo: "5:30" }, { valor: 342, rotulo: "5:42" }, { valor: 355, rotulo: "5:55" }] },
  frase: {
    versao: "frase_evolucao@1", tipo: "comparada", mudanca: "menor", a_favor: true, valor_atual: 342, valor_anterior: 354, n_atual: 3, n_anterior: 3,
    texto: "Pace dos seus treinos leves nas últimas 4 semanas: 5:42/km (mediana de 3 treinos), 12 s/km mais rápido que nas 4 semanas anteriores (5:54/km, 3 treinos).",
  },
};

export const volumeSemana: SerieEvolucao = {
  ...paceLeve,
  id: "corrida.volume_km",
  titulo: "Volume por semana",
  descricao: serieCatalogo.volume.descricao,
  grupo: "Esforço e volume",
  unidade: "km",
  pontos: [
    ponto(0, { atividade_id: null, data_texto: "semana de 03/03", valor: 30, valor_texto: "30,0", normal_estado: null, fora_do_normal: null, rotulo: "Semana de 03/03, 30 quilômetros" }),
    ponto(1, { atividade_id: null, data_texto: "semana de 10/03", valor: 40, valor_texto: "40,0", normal_estado: null, fora_do_normal: null, rotulo: "Semana de 10/03, 40 quilômetros" }),
    ponto(2, { atividade_id: null, data_texto: "semana de 17/03", valor: 12, valor_texto: "12,0", normal_estado: null, fora_do_normal: null, parcial: true, rotulo: "Semana de 17/03, 12 quilômetros, semana em curso" }),
  ],
  ultimo_valor_texto: "40,0",
  ultimo_rotulo: "última semana completa",
  referencia: null,
  eixo: { minimo: 0, maximo: 50, invertido: false, marcas: [{ valor: 0, rotulo: "0" }, { valor: 25, rotulo: "25" }, { valor: 50, rotulo: "50" }] },
  frase: { ...paceLeve.frase, texto: "Volume das últimas 4 semanas: 35 km por semana (mediana de 4 semanas), 5 km a mais que nas 4 semanas anteriores." },
};

export const serieAprendendo: SerieEvolucao = {
  ...paceLeve,
  referencia: null,
  aprendendo_texto: "Ainda estamos aprendendo o seu normal no treino leve: faltam 3 treinos para mostrar a faixa.",
  pontos: paceLeve.pontos.map((p) => ({ ...p, aprendendo: true, fora_do_normal: null, normal_estado: "aprendendo" })),
};

export const serieVazia: SerieEvolucao = {
  ...paceLeve,
  pontos: [],
  ultimo_valor_texto: null,
  ultimo_rotulo: null,
  referencia: null,
  frase: { ...paceLeve.frase, tipo: "sem_dado", texto: "Sem treinos de tiros ainda. Quando você fizer tiros de 1 km, a evolução aparece aqui." },
};

export const series: Record<string, SerieEvolucao> = {
  "corrida.pace.leve": paceLeve,
  "corrida.volume_km": volumeSemana,
};

const resposta = (status: number, corpo: unknown) => ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;

/** `fetch` falso que responde o catálogo e a série pelo id e período; o resto (`outras`) cai em 404. */
export function fetchEvolucao(opcoes: { catalogo?: CatalogoSeries | number; series?: Record<string, SerieEvolucao | number> } = {}) {
  const porId = opcoes.series ?? series;
  return jest.fn(async (url: Parameters<typeof fetch>[0]) => {
    const u = new URL(String(url));
    if (u.pathname.endsWith("/evolucao/series")) {
      const c = opcoes.catalogo ?? catalogo;
      return typeof c === "number" ? resposta(c, { detail: "x" }) : resposta(200, c);
    }
    const m = u.pathname.match(/\/evolucao\/series\/(.+)$/);
    if (m) {
      const s = porId[decodeURIComponent(m[1])];
      if (s === undefined) return resposta(404, { detail: "série não encontrada" });
      return typeof s === "number" ? resposta(s, { detail: "x" }) : resposta(200, { ...s, periodo: u.searchParams.get("periodo") ?? "12s" });
    }
    return resposta(404, { detail: "não encontrado" });
  }) as unknown as typeof fetch & jest.Mock;
}
