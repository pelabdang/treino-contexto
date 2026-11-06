// Atividades sintéticas (nada de dado real) para os testes e para o servidor falso das capturas.
import type { Atividade } from "@treino/api-client";

const corrida: Atividade = {
  atividade_id: 101,
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
};

export const atividades = {
  ok: corrida,
  indoor: {
    ...corrida,
    atividade_id: 102,
    subtipo: "esteira",
    distancia_m: 8000,
    distancia: "8,00 km",
    pace_medio: "5:30",
    clima: { estado: "indoor" },
  } as Atividade,
  sem_posicao: { ...corrida, atividade_id: 103, clima: { estado: "sem_posicao" } } as Atividade,
  pendente: { ...corrida, atividade_id: 104, clima: { estado: "pendente" } } as Atividade,
  falha: { ...corrida, atividade_id: 105, clima: { estado: "falha" } } as Atividade,
  natacao: {
    atividade_id: 106,
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
  } as Atividade,
} satisfies Record<string, Atividade>;
