// Semana-padrão sintética (ADR 0011, item 9). Nenhum dado real.
import type { SemanaPadrao } from "@treino/api-client";

export const semanaComPlano: SemanaPadrao = {
  atleta_id: 1,
  em: "2026-03-10",
  vigente: {
    vigente_desde: "2026-03-02",
    definido_por: "atleta",
    definido_em: "2026-03-01T21:10:00-03:00",
    itens: [
      { dia_semana: 1, dia_semana_texto: "segunda", modalidade: "natacao", tipo_treino: null },
      { dia_semana: 2, dia_semana_texto: "terça", modalidade: "corrida", tipo_treino: "fartlek" },
    ],
  },
  vigencias: [
    { vigente_desde: "2026-03-02", definido_por: "atleta", total_itens: 2 },
    { vigente_desde: "2026-02-02", definido_por: "professor", total_itens: 1 },
  ],
};

export const semanaAntiga: SemanaPadrao = {
  atleta_id: 1,
  em: "2026-02-02",
  vigente: {
    vigente_desde: "2026-02-02",
    definido_por: "professor",
    definido_em: "2026-02-01T10:00:00-03:00",
    itens: [{ dia_semana: 3, dia_semana_texto: "quarta", modalidade: "ciclismo", tipo_treino: "longo" }],
  },
  vigencias: semanaComPlano.vigencias,
};

export const semanaVazia: SemanaPadrao = { atleta_id: 1, em: "2026-03-10", vigente: null, vigencias: [] };
