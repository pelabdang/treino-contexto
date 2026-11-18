import { router, useLocalSearchParams } from "expo-router";

import { TelaConsentimento } from "../../../componentes/TelaConsentimento";
import { useContadorDeFoco } from "../../../navegacao/useContadorDeFoco";
import { useAtleta } from "../../../sessao/SessaoProvider";

const avisoDaRota = (a?: string) => (a === "inexistente" || a === "registrado" ? a : null);

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
      aviso={avisoDaRota(Array.isArray(aviso) ? aviso[0] : aviso)}
      aoVoltar={() => (router.canGoBack() ? router.back() : router.replace("/"))}
      aoAbrirTermo={(id) => router.push(`/consentimento/${id}`)}
    />
  );
}
