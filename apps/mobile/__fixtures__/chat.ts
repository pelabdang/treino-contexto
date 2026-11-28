// Respostas sintéticas do chat, no formato da API (adendo 16 da ADR 0004). Nada de dado real.
import type { ConversaChat, MensagemChat } from "../src/chat/api";

export const mensagem = (extra: Partial<MensagemChat> = {}): MensagemChat => ({
  id: 1,
  ordem: 1,
  pergunta: "Como foi minha semana?",
  estado: "respondida",
  motivo: null,
  texto: "Nesta semana você correu 3 vezes, 28,4 km no total.",
  links: [],
  criada_em: "2025-03-20T14:32:10-03:00",
  ...extra,
});

export const conversa = (extra: Partial<ConversaChat> = {}): ConversaChat => ({
  id: 7,
  titulo: "Como foi minha semana?",
  criada_em: "2025-03-20T14:32:00-03:00",
  atualizada_em: "2025-03-20T14:32:10-03:00",
  mensagens: [mensagem()],
  ...extra,
});

export const comLinks = mensagem({
  links: [
    { tipo: "evolucao", rotulo: "Abrir na Evolução", serie_id: "corrida.volume_km" },
    { tipo: "treino", rotulo: "Abrir treino", atividade_id: 107 },
  ],
});
export const recusaTema = mensagem({ estado: "recusada", motivo: "fora_do_tema", texto: "Eu respondo perguntas sobre os seus treinos. Pergunte, por exemplo, sobre o seu pace, a sua carga ou como foi a sua semana." });
export const recusaMudanca = mensagem({ estado: "recusada", motivo: "pedido_de_mudanca", texto: "Mudar o treino é com o seu professor." });
export const falha = mensagem({ estado: "erro", motivo: "provedor", texto: "Não consegui responder agora. Tente de novo em instantes." });
export const reprovada = mensagem({ estado: "reprovada", motivo: "numero_nao_confere", texto: "Não consegui responder agora. Tente de novo em instantes." });
