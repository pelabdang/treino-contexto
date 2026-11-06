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
const atividade = (id) => ({
  atividade_id: id,
  modalidade: "corrida",
  subtipo: "rua",
  inicio: "2025-03-18T09:30:00Z",
  data_local: "2025-03-18",
  hora_local: "06:30",
  duracao_s: 3125,
  duracao: "0:52:05",
  distancia_m: 10000,
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

createServer((req, res) => {
  const cabecalhos = {
    "content-type": "application/json",
    "access-control-allow-origin": "*",
    "access-control-allow-headers": "*",
  };
  if (req.method === "OPTIONS") return res.writeHead(204, cabecalhos).end();
  const { pathname } = new URL(req.url, "http://x");
  let corpo = null;
  if (/^\/atletas\/\d+\/evolucao\/tiros-1km$/.test(pathname)) corpo = evolucao;
  const m = pathname.match(/^\/atletas\/\d+\/atividades\/(\d+)$/);
  if (m) corpo = atividade(Number(m[1]));
  res.writeHead(corpo ? 200 : 404, cabecalhos).end(JSON.stringify(corpo ?? { detail: "não encontrado" }));
}).listen(porta, () => console.log(`API falsa (dados sintéticos) em http://localhost:${porta}`));
