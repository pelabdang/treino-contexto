import { router } from "expo-router";

import { TelaCheckinsPendentes } from "../componentes/TelaCheckinsPendentes";
import { config } from "../config";
import { useContadorDeFoco } from "../navegacao/useContadorDeFoco";

export default function CheckinsPendentes() {
  const atualizar = useContadorDeFoco();
  return (
    <TelaCheckinsPendentes
      apiUrl={config.apiUrl}
      atletaId={config.atletaId}
      atualizar={atualizar}
      aoAbrirCheckin={(id) => router.push(`/checkin/${id}?origem=pendentes`)}
      aoVoltar={() => (router.canGoBack() ? router.back() : router.replace("/"))}
    />
  );
}
