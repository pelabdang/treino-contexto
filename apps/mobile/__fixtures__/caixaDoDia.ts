// Caixa do dia sintética (nenhum dado real): alunos fictícios escritos à mão, texto marcador na observação.
import type { CaixaDoDia, DetalheTreino } from "../src/caixa/api";

export const OBSERVACAO_MARCADOR = "Texto de exemplo escrito à mão (MARCADOR-OBS-123).";

const detalheComCheckin: DetalheTreino = {
  tipo_confirmado: false,
  tipo_texto: "Intervalado",
  tipo_origem_texto: "sugerido pela regra",
  checkin: {
    pse_texto: "8",
    sensacao: 2,
    sensacao_texto: "Mal",
    atalhos: [
      { chave: "dor", texto: "Dor" },
      { chave: "cansaco", texto: "Cansaço" },
    ],
    nada_a_relatar: false,
    observacao: OBSERVACAO_MARCADOR,
  },
  feedback: { estado: "pronto", texto: "Texto de exemplo do feedback.", origem: "automatico" },
};
const detalheSemCheckin: DetalheTreino = {
  tipo_confirmado: false,
  tipo_texto: null,
  tipo_origem_texto: null,
  checkin: null,
  feedback: { estado: "sem_checkin", mensagem: "O prazo do check-in deste treino acabou.", checkin_aberto: false },
};

export const caixa: CaixaDoDia = {
  versao: "atencao@1",
  hoje: "2025-11-13",
  janela_atencao_dias: 7,
  janela_novos_dias: 14,
  alunos: [
    {
      atleta_id: 1,
      nome: "Atleta Fixture Ana",
      sem_motivo: false,
      texto_sem_motivo: null,
      treinos: [
        {
          atividade_id: 501,
          modalidade: "corrida",
          data_local: "2025-11-11",
          hora_local: "06:30",
          duracao_texto: "45 min",
          motivos: [
            { codigo: "dor", texto: "Treino de terça com dor marcada no check-in." },
            { codigo: "fora_do_normal", texto: "Treino de terça fora do normal: FC média acima do habitual." },
          ],
          detalhe: detalheComCheckin,
        },
      ],
    },
    {
      atleta_id: 2,
      nome: "Atleta Fixture Bruno",
      sem_motivo: false,
      texto_sem_motivo: null,
      treinos: [
        {
          atividade_id: 502,
          modalidade: "corrida",
          data_local: "2025-11-12",
          hora_local: "07:00",
          duracao_texto: "50 min",
          motivos: [{ codigo: "divergencia", texto: "Treino de quarta diferente da semana-padrão: previsto intervalado, sem esforço detectado." }],
          detalhe: { ...detalheSemCheckin, tipo_texto: "Leve", tipo_origem_texto: "confirmado por você", tipo_confirmado: true },
        },
      ],
    },
    {
      atleta_id: 3,
      nome: "Atleta Fixture Carla",
      sem_motivo: false,
      texto_sem_motivo: null,
      treinos: [
        {
          atividade_id: 503,
          modalidade: "ciclismo",
          data_local: "2025-11-08",
          hora_local: "08:00",
          duracao_texto: "1 h 10",
          motivos: [{ codigo: "checkin_vencendo", texto: "Treino de sábado sem check-in; o prazo termina em 2 dias." }],
          detalhe: detalheSemCheckin,
        },
      ],
    },
    { atleta_id: 4, nome: "Atleta Fixture Diego", sem_motivo: true, texto_sem_motivo: "Nada a destacar nos últimos 7 dias.", treinos: [] },
  ],
  novos: [
    {
      atividade_id: 511,
      atleta_id: 1,
      atleta_nome: "Atleta Fixture Ana",
      modalidade: "corrida",
      data_local: "2025-11-11",
      hora_local: "06:30",
      duracao_texto: "45 min",
      tipo_sugerido: "intervalado",
      tipo_sugerido_texto: "Intervalado",
      origem_texto: "sugerido pela regra",
      detalhe: detalheComCheckin,
    },
    {
      atividade_id: 512,
      atleta_id: 4,
      atleta_nome: "Atleta Fixture Diego",
      modalidade: "natacao",
      data_local: "2025-11-10",
      hora_local: "18:00",
      duracao_texto: "40 min",
      tipo_sugerido: "leve",
      tipo_sugerido_texto: "Leve",
      origem_texto: "sugerido pela semana-padrão",
      detalhe: { ...detalheSemCheckin, tipo_texto: "Leve", tipo_origem_texto: "sugerido pela semana-padrão" },
    },
  ],
};
