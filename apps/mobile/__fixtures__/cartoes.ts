import type { CartaoInicio, CartoesInicio } from "@treino/api-client";

// Cartões do início v4 (ADR 0004, adendo 15, `GET /inicio/cartoes`): textos prontos, como a API manda. Dado sintético.

export const estaSemana: CartaoInicio = {
  id: "esta_semana", formato: "pequeno", rotulo: "Esta semana", valor: "3 treinos", apoio: "2 h 37 min · semana passada: 4", texto: null, barras: [],
  destino: { tela: "evolucao", serie_id: "corrida.volume_km", atividade_id: null },
  rotulo_acessivel: "Esta semana, 3 treinos, 2 horas e 37 minutos, semana passada 4 treinos. Abre a evolução do volume.",
};
export const hojeNaSemana: CartaoInicio = {
  id: "hoje_na_semana", formato: "pequeno", rotulo: "Hoje, sexta", valor: "Corrida leve", apoio: "da sua rotina", texto: null, barras: [],
  destino: { tela: "semana_padrao", serie_id: null, atividade_id: null },
  rotulo_acessivel: "Hoje, sexta, corrida leve, da sua rotina. Abre a semana-padrão.",
};
export const volume4: CartaoInicio = {
  id: "volume_4_semanas", formato: "largo", rotulo: "Volume das 4 semanas", valor: "30 km por semana", apoio: null,
  texto: "30 km por semana, 10 km a menos que nas 4 anteriores.",
  barras: [
    { data_texto: "03/02", valor_texto: "40 km", destaque: false },
    { data_texto: "10/02", valor_texto: "35 km", destaque: false },
    { data_texto: "17/02", valor_texto: "30 km", destaque: false },
    { data_texto: "24/02", valor_texto: "25 km", destaque: true },
  ],
  destino: { tela: "evolucao", serie_id: "corrida.volume_km", atividade_id: null },
  rotulo_acessivel: "Volume das 4 semanas, 30 km por semana. Abre a evolução do volume.",
};
export const emMovimento: CartaoInicio = {
  id: "em_movimento", formato: "largo", rotulo: "Em movimento", valor: "Pace dos seus treinos leves", apoio: null,
  texto: "Pace dos seus treinos leves nas últimas 4 semanas: 5:42/km (mediana de 3 treinos), 12 s/km mais rápido que nas 4 anteriores (5:54/km).",
  barras: [],
  destino: { tela: "evolucao", serie_id: "corrida.pace.leve", atividade_id: null },
  rotulo_acessivel: "Em movimento, pace dos seus treinos leves. Abre a evolução.",
};
export const melhorMarca: CartaoInicio = {
  id: "melhor_marca", formato: "pequeno", rotulo: "Melhor marca", valor: "21:10 · 5 km", apoio: "novo recorde · 12/03", texto: null, barras: [],
  destino: { tela: "treino", serie_id: null, atividade_id: 77 },
  rotulo_acessivel: "Melhor marca, 21 minutos e 10 segundos nos 5 quilômetros, novo recorde em 12 de março. Abre o treino.",
};

export const cartoes: CartoesInicio = {
  atleta_id: 1,
  data: "2025-03-21",
  cartoes: [estaSemana, hojeNaSemana, volume4, emMovimento, melhorMarca],
};
