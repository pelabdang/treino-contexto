import { router } from "expo-router";

import { TelaCheckinsPendentes } from "../../componentes/TelaCheckinsPendentes";
import { useContadorDeFoco } from "../../navegacao/useContadorDeFoco";
import { useAtleta } from "../../sessao/SessaoProvider";

export default function CheckinsPendentes() {
  const atualizar = useContadorDeFoco();
  const { apiUrl, atletaId, fetchFn } = useAtleta();
  return (
    <TelaCheckinsPendentes
      apiUrl={apiUrl}
      atletaId={atletaId}
      fetchFn={fetchFn}
      atualizar={atualizar}
      aoAbrirCheckin={(id) => router.push(`/checkin/${id}?origem=pendentes`)}
      aoVoltar={() => (router.canGoBack() ? router.back() : router.replace("/"))}
    />
  );
}
