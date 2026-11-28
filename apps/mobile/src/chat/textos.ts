// Textos e listas fixas do chat "Pergunte ao seu treino" (spec docs/design/telas/chat.md). Tudo o que ainda pode mudar
// por decisão do Angelo mora aqui, em um lugar só. As respostas, recusas e erros vêm prontos da API.

/** Decisão do Angelo pendente: a entrada pelo Início, como tela empilhada e sem aba nova. Desligar tira o ponto de entrada. */
export const ENTRADA_CHAT_NO_INICIO = true;

/** Decisão do Angelo pendente: "Copiar resposta" e 👍/👎 ficam de fora da primeira versão. Ligar não faz nada ainda (sem tela). */
export const COPIAR_E_AVALIAR = false;

/** Decisão do Angelo pendente: as 6 perguntas prontas, fixas no app (não há rota para elas). O texto é enviado como pergunta comum. */
export const PERGUNTAS_PRONTAS: readonly string[] = [
  "Como foi minha semana?",
  "Meu pace nos treinos leves melhorou?",
  "Quanto corri neste mês?",
  "Como estão minha carga e minha forma?",
  "O que escrevi no check-in de ontem?",
  "Como foi meu último treino?",
];

export const TITULO_CHAT = "Pergunte ao seu treino";
export const CHAMADA_ENTRADA = "Escreva a sua pergunta";
export const TITULO_COMECO = "O que você quer saber sobre os seus treinos?";
export const FRASE_COMECO = "Escreva a sua pergunta ou toque em uma destas.";
export const SEM_TREINOS = "Você ainda não tem treinos aqui. Importe o primeiro para perguntar.";
export const ROTULO_IA = "Resposta de IA com números do seu histórico";
export const AVISO_IA = "A sua pergunta vai a um serviço de IA.";
export const TEXTO_ERRO_FIXO = "Não consegui responder agora. Tente de novo em instantes.";
export const TEXTO_SEM_REDE = "Sem conexão. Verifique a internet e tente de novo.";
export const TEXTO_NAO_ENCONTRADA = "Não encontramos esta conversa.";
export const TITULO_LIMITE = "Limite de perguntas";
export const PLACEHOLDER = "Escreva a sua pergunta";
export const PLACEHOLDER_ESPERA = "Aguarde para perguntar…";

export const MAXIMO_PERGUNTA = 1000;
export const CONTADOR_A_PARTIR_DE = 900;
/** Limite do cliente: espera a API por até 60 s antes de desistir (a API tem 45 s). */
export const TEMPO_LIMITE_PEDIDO_MS = 60_000;
/** A espera (só troca o texto; o app não estima nada). */
export const ESPERA_MEDIA_MS = 10_000;
export const ESPERA_LONGA_MS = 25_000;

export const TEXTO_ESPERA = {
  curta: "Consultando os seus treinos…",
  media: "Ainda consultando. Perguntas sobre vários treinos levam mais tempo.",
  longa: "Está demorando mais que o normal. A resposta pode levar até 45 segundos.",
} as const;
export const DICA_ESPERA = "Pode levar até 45 segundos.";

export const TEXTO_LISTA_VAZIA = "Nenhuma conversa ainda. Faça a sua primeira pergunta.";
export const TEXTO_LISTA_ERRO = "Não deu para carregar as conversas.";
export const TEXTO_APAGAR_ERRO = "Não deu para apagar. Tente de novo.";
export const TEXTO_APAGADA = "Conversa apagada";
export const RODAPE_LISTA = "As conversas ficam guardadas até você apagar. O seu professor não vê as suas conversas.";
export const TITULO_APAGAR = "Apagar esta conversa?";
export const TEXTO_APAGAR = "As perguntas e as respostas somem do app. O que já foi enviado ao serviço de IA não pode ser apagado por nós.";
