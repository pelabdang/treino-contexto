import { router, useLocalSearchParams } from "expo-router";

import { TelaConsentimento } from "../../../componentes/TelaConsentimento";
import { useContadorDeFoco } from "../../../navegacao/useContadorDeFoco";
import { useAtleta } from "../../../sessao/SessaoProvider";

export default function Consentimento() {
  const { aviso } = useLocalSearchParams<{ aviso?: string }>();
  const atualizar = useContadorDeFoco();
  const { apiUrl, atletaId, fetchFn } = useAtleta();
  return (
    <TelaConsentimento
      apiUrl={apiUrl}
      atletaId={atletaId}
      fetchFn={fetchFn}
      atualizar={atualizar}
      avisoInexistente={(Array.isArray(aviso) ? aviso[0] : aviso) === "inexistente"}
      aoVoltar={() => (router.canGoBack() ? router.back() : router.replace("/"))}
      aoAbrirTermo={(id) => router.push(`/consentimento/${id}`)}
    />
  );
}
