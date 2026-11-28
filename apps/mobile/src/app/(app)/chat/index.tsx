import { router, useLocalSearchParams } from "expo-router";

import { TelaChat } from "../../../componentes/TelaChat";
import { useAtleta } from "../../../sessao/SessaoProvider";

// Conversa nova (`/chat`). `?pergunta=` vem da pergunta pronta do Início e já é enviada ao abrir.
export default function ChatNovo() {
  const { pergunta } = useLocalSearchParams<{ pergunta?: string }>();
  const { apiUrl, atletaId, fetchFn } = useAtleta();
  return (
    <TelaChat
      apiUrl={apiUrl}
      atletaId={atletaId}
      fetchFn={fetchFn}
      perguntaInicial={typeof pergunta === "string" && pergunta ? pergunta : undefined}
      aoVoltar={() => (router.canGoBack() ? router.back() : router.replace("/"))}
      aoEsperarNoInicio={() => router.replace("/")}
      aoAbrirConversas={() => router.push("/chat/conversas")}
      aoAbrirTreino={(id) => router.push(`/treino/${id}`)}
      aoAbrirEvolucao={(serie) => router.push({ pathname: "/evolucao", params: { serie } })}
    />
  );
}
