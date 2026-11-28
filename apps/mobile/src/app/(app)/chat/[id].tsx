import { router, useLocalSearchParams } from "expo-router";

import { TelaChat } from "../../../componentes/TelaChat";
import { useAtleta } from "../../../sessao/SessaoProvider";

// Conversa existente (`/chat/<id>`); abre direto na web.
export default function ChatConversa() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const conversaId = Number(Array.isArray(id) ? id[0] : id);
  const { apiUrl, atletaId, fetchFn } = useAtleta();
  return (
    <TelaChat
      key={conversaId}
      apiUrl={apiUrl}
      atletaId={atletaId}
      fetchFn={fetchFn}
      conversaId={conversaId}
      aoVoltar={() => (router.canGoBack() ? router.back() : router.replace("/"))}
      aoEsperarNoInicio={() => router.replace("/")}
      aoAbrirConversas={() => router.push("/chat/conversas")}
      aoAbrirTreino={(treino) => router.push(`/treino/${treino}`)}
      aoAbrirEvolucao={(serie) => router.push({ pathname: "/evolucao", params: { serie } })}
    />
  );
}
