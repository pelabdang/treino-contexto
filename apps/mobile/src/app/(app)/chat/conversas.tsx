import { router } from "expo-router";

import { TelaConversas } from "../../../componentes/TelaConversas";
import { useContadorDeFoco } from "../../../navegacao/useContadorDeFoco";
import { useAtleta } from "../../../sessao/SessaoProvider";

export default function Conversas() {
  const atualizar = useContadorDeFoco();
  const { apiUrl, atletaId, fetchFn } = useAtleta();
  return (
    <TelaConversas
      apiUrl={apiUrl}
      atletaId={atletaId}
      fetchFn={fetchFn}
      atualizar={atualizar}
      aoVoltar={() => (router.canGoBack() ? router.back() : router.replace("/"))}
      aoAbrirConversa={(id) => router.push(`/chat/${id}`)}
      aoNovaConversa={() => router.push("/chat")}
    />
  );
}
