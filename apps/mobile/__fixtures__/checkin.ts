// Check-ins sintéticos (nada de dado real) para os testes. O texto marcador prova que o app não escreve respostas em log.
import type { Atividade, CargaPse, Checkin, CheckinsPendentes } from "@treino/api-client";

import { atividades } from "./atividades";

export const MARCADOR = "MARCADOR-SINTETICO-123";

export const checkinExemplo: Checkin = {
  atividade_id: 101,
  pse: 5,
  pse_texto: "difícil",
  sensacao: 4,
  sensacao_texto: "Bem",
  nada_a_relatar: false,
  atalhos: [
    { chave: "cansaco", texto: "Cansaço" },
    { chave: "trabalho_estresse", texto: "Trabalho ou estresse" },
  ],
  texto: MARCADOR,
  versao: "checkin@1",
  registrado_em: "2025-03-18T12:00:00Z",
  atualizado_em: "2025-03-18T12:00:00Z",
};

export const cargaCalculada: CargaPse = {
  versao: "carga_pse@1",
  estado: "calculada",
  pse: 5,
  minutos: 52,
  valor: 260,
  valor_texto: "260 UA",
  texto: "Carga pela PSE: 5 x 52 min = 260 UA.",
};

const base = atividades.ok;

export const atividadesCheckin = {
  /** Sem check-in, prazo aberto. */
  semCheckin: base,
  /** Com check-in e carga calculada. */
  comCheckin: { ...base, checkin: checkinExemplo, carga_pse: cargaCalculada } as Atividade,
  /** Check-in "nada a relatar". */
  nada: {
    ...base,
    checkin: { ...checkinExemplo, nada_a_relatar: true, atalhos: [], texto: null },
    carga_pse: cargaCalculada,
  } as Atividade,
  /** Duração ausente: só o texto da carga. */
  semDuracao: {
    ...base,
    checkin: checkinExemplo,
    carga_pse: { versao: "carga_pse@1", estado: "sem_duracao", minutos: 0, texto: "Sem duração para calcular a carga pela PSE." },
  } as Atividade,
  /** Prazo de criação vencido. */
  foraDoPrazo: { ...base, checkin_aberto: false } as Atividade,
  /** Treino inteiro de multiesporte: sem cartão. */
  multiesportePai: { ...base, subtipo: "multiesporte_pai", checkin_aberto: false, carga_pse: null } as Atividade,
  troca: { ...base, subtipo: "troca", checkin_aberto: false, carga_pse: null } as Atividade,
  /** Parte de multiesporte com a PSE da parte anterior. */
  comSugestao: { ...base, pse_sugerida: 5 } as Atividade,
  comSugestaoSemAncora: { ...base, pse_sugerida: 6 } as Atividade,
};

export const pendentes: CheckinsPendentes = {
  dias: 7,
  total: 2,
  pendentes: [
    { atividade_id: 101, modalidade: "corrida", data_local: "2025-03-18", hora_local: "06:30", duracao: "0:52:05", titulo: "Corrida, 52 min" },
    { atividade_id: 106, modalidade: "natacao", data_local: "2025-03-17", hora_local: "07:00", duracao: "0:45:00", titulo: "Natação, 45 min" },
  ],
};
