import { router, useLocalSearchParams } from "expo-router";

import { trocarEnderecoDaConversa } from "../../../chat/endereco";
import { PERGUNTAS_PRONTAS } from "../../../chat/textos";
import { TelaChat } from "../../../componentes/TelaChat";
import { useAtleta } from "../../../sessao/SessaoProvider";

// Conversa nova (`/chat`). Do Início: `?pronta=<índice>` já envia a pergunta pronta (o texto é fixo do app e nunca vai para a URL) e `?foco=1` abre com o teclado.
export default function ChatNovo() {
  const { pronta, foco } = useLocalSearchParams<{ pronta?: string; foco?: string }>();
  const { apiUrl, atletaId, fetchFn } = useAtleta();
  const indice = typeof pronta === "string" && pronta !== "" ? Number(pronta) : -1;
  return (
    <TelaChat
      apiUrl={apiUrl}
      atletaId={atletaId}
      fetchFn={fetchFn}
      perguntaInicial={PERGUNTAS_PRONTAS[indice]}
      focoInicial={foco === "1"}
      aoCriada={trocarEnderecoDaConversa}
      aoEsperarNoInicio={() => router.replace("/")}
      aoVoltar={() => (router.canGoBack() ? router.back() : router.replace("/"))}
      aoAbrirConversas={() => router.push("/chat/conversas")}
      aoAbrirTreino={(id) => router.push(`/treino/${id}`)}
      aoAbrirEvolucao={(serie) => router.push({ pathname: "/evolucao", params: { serie } })}
    />
  );
}
