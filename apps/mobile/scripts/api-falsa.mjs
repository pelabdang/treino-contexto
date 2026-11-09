// API falsa com dados 100% sintéticos, só para abrir o app na web e tirar capturas
// sem backend e sem trocar config (#218). Uso: node scripts/api-falsa.mjs [porta]
// Depois: EXPO_PUBLIC_API_URL=http://localhost:8000 npx expo start --web
import { createServer } from "node:http";

const porta = Number(process.argv[2] ?? process.env.PORT ?? 8000);

const pace = (s) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`;
const datas = ["2025-02-04", "2025-02-18", "2025-03-04", "2025-03-18"];
const melhores = [262, 258, 255, 251];
const sessoes = datas.map((data, i) => {
  const tiros = [0, 1, 2, 3, 4].map((o) => {
    const s = melhores[i] + (o === 2 ? 0 : 3 + o * 2);
    return { ordem: o + 1, distancia_m: 1000, duracao_s: s, fc_media: 168 + o, pace: pace(s), pace_s_km: s };
  });
  const medio = Math.round(tiros.reduce((t, x) => t + x.pace_s_km, 0) / tiros.length);
  return {
    atividade_id: 101 + i,
    data,
    inicio: `${data}T09:30:00Z`,
    fc_media: 160,
    fc_melhor_tiro: 170,
    n_tiros: 5,
    ordem_melhor_tiro: 3,
    pace_melhor: pace(melhores[i]),
    pace_melhor_s_km: melhores[i],
    pace_medio: pace(medio),
    pace_medio_s_km: medio,
    tiros,
  };
});
const evolucao = {
  atleta_id: 1,
  metrica: "tiros_1km",
  periodo: null,
  reclassificacao_pendente: false,
  versao_calculo: "tiros_1km@sintetico",
  sessoes,
  unidades: { distancia: "m", duracao: "s", fc: "bpm", pace: "min/km" },
  eixos: {
    pace: {
      invertido: true,
      min_s_km: 240,
      max_s_km: 280,
      marcas: [
        { rotulo: "4:00", valor_s_km: 240 },
        { rotulo: "4:40", valor_s_km: 280 },
      ],
    },
    fc: {
      min_bpm: 150,
      max_bpm: 180,
      marcas: [
        { rotulo: "150", valor_bpm: 150 },
        { rotulo: "180", valor_bpm: 180 },
      ],
    },
  },
};
const corrida = (id) => ({
  atividade_id: id,
  modalidade: "corrida",
  subtipo: "rua",
  inicio: "2025-03-18T09:30:00Z",
  data_local: "2025-03-18",
  hora_local: "06:30",
  duracao_s: 3125,
  duracao: "0:52:05",
  distancia_m: 10000,
  distancia: "10,00 km",
  pace_medio: "5:12",
  fc_media: 152,
  clima: {
    estado: "ok",
    temperatura_c: 24.3,
    sensacao_c: 25.1,
    umidade_pct: 61,
    vento_kmh: 8.2,
    atribuicao: "Weather data by Open-Meteo.com",
  },
});

// Natação (id 106): sem pace, sem FC, distância em metros, como a API manda.
const natacao = (id) => ({
  ...corrida(id),
  modalidade: "natacao",
  subtipo: "piscina",
  inicio: "2025-03-20T10:00:00Z",
  data_local: "2025-03-20",
  hora_local: "07:00",
  duracao_s: 2700,
  duracao: "0:45:00",
  distancia_m: 1800,
  distancia: "1.800 m",
  pace_medio: null,
  fc_media: null,
  clima: { estado: "indoor" },
});
// Semana-padrão sintética (#268): segunda fartlek + natação, terça ciclismo intervalado, quarta corrida
// intervalado + natação; duas vigências. O PUT guarda em memória e devolve `atividades_reaplicadas: 0`.
const NOMES_DIA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"];
const comTexto = (itens) =>
  itens.map((i) => ({ dia_semana_texto: NOMES_DIA[i.dia_semana - 1], tipo_treino: null, ...i }));
const planoPadrao = () => [
  {
    vigente_desde: "2026-03-02",
    definido_por: "atleta",
    definido_em: "2026-03-01T21:10:00-03:00",
    itens: comTexto([
      { dia_semana: 1, modalidade: "corrida", tipo_treino: "fartlek" },
      { dia_semana: 1, modalidade: "natacao" },
      { dia_semana: 2, modalidade: "ciclismo", tipo_treino: "intervalado" },
      { dia_semana: 3, modalidade: "corrida", tipo_treino: "intervalado" },
      { dia_semana: 3, modalidade: "natacao" },
    ]),
  },
  {
    vigente_desde: "2026-02-02",
    definido_por: "professor",
    definido_em: "2026-02-01T10:00:00-03:00",
    itens: comTexto([
      { dia_semana: 2, modalidade: "corrida", tipo_treino: "leve" },
      { dia_semana: 4, modalidade: "ciclismo", tipo_treino: "longo" },
    ]),
  },
];
// Atleta de teste para forçar estados da tela da semana-padrão (EXPO_PUBLIC_ATLETA_ID=<id>); os demais ids usam o plano do atleta 1:
//   2 = sem plano (estado vazio)            3 = GET derruba a conexão (erro de rede ao carregar)
//   4 = PUT responde 422                    5 = GET responde 404 (atleta não encontrado)
//   6 = PUT derruba a conexão (erro de rede ao salvar)
const semanas = new Map();
const vigenciasDe = (id) => {
  if (!semanas.has(id)) semanas.set(id, id === 2 ? [] : planoPadrao());
  return semanas.get(id);
};
const dataLocal = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const semanaPadrao = (id, em) => {
  const dia = em ?? dataLocal(new Date());
  const ordenadas = [...vigenciasDe(id)].sort((a, b) => b.vigente_desde.localeCompare(a.vigente_desde));
  return {
    atleta_id: 1,
    em: dia,
    vigente: ordenadas.find((v) => v.vigente_desde <= dia) ?? null,
    vigencias: ordenadas.map((v) => ({ vigente_desde: v.vigente_desde, definido_por: v.definido_por, total_itens: v.itens.length })),
  };
};
const gravarSemana = (id, corpo) => {
  const nova = {
    vigente_desde: corpo.vigente_desde,
    definido_por: corpo.definido_por,
    definido_em: new Date().toISOString(),
    itens: comTexto([...corpo.itens].sort((a, b) => a.dia_semana - b.dia_semana || a.modalidade.localeCompare(b.modalidade))),
  };
  semanas.set(id, [...vigenciasDe(id).filter((v) => v.vigente_desde !== nova.vigente_desde), nova]);
  return { ...nova, atividades_reaplicadas: 0 };
};
const atividade = (id) => (id === 106 ? natacao(id) : corrida(id));

createServer((req, res) => {
  const cabecalhos = {
    "content-type": "application/json",
    "access-control-allow-origin": "*",
    "access-control-allow-headers": "*",
    "access-control-allow-methods": "*",
  };
  if (req.method === "OPTIONS") return res.writeHead(204, cabecalhos).end();
  const { pathname, searchParams } = new URL(req.url, "http://x");
  let corpo = null;
  const sp = pathname.match(/^\/atletas\/(\d+)\/semana-padrao$/);
  if (sp) {
    const id = Number(sp[1]);
    if (req.method === "PUT") {
      if (id === 6) return req.destroy();
      let texto = "";
      req.on("data", (c) => (texto += c));
      req.on("end", () => {
        if (id === 4) return res.writeHead(422, cabecalhos).end(JSON.stringify({ detail: [{ loc: ["body", "itens"], msg: "sintético", type: "value_error" }] }));
        res.writeHead(200, cabecalhos).end(JSON.stringify(gravarSemana(id, JSON.parse(texto))));
      });
      return;
    }
    if (id === 3) return req.destroy();
    if (id === 5) return res.writeHead(404, cabecalhos).end(JSON.stringify({ detail: "atleta não encontrado" }));
    return res.writeHead(200, cabecalhos).end(JSON.stringify(semanaPadrao(id, searchParams.get("em"))));
  }
  if (/^\/atletas\/\d+\/evolucao\/tiros-1km$/.test(pathname)) corpo = evolucao;
  const m = pathname.match(/^\/atletas\/\d+\/atividades\/(\d+)$/);
  if (m) corpo = atividade(Number(m[1]));
  res.writeHead(corpo ? 200 : 404, cabecalhos).end(JSON.stringify(corpo ?? { detail: "não encontrado" }));
}).listen(porta, () => console.log(`API falsa (dados sintéticos) em http://localhost:${porta}`));
