import { router } from "expo-router";

import { TelaSemanaPadrao } from "../../componentes/TelaSemanaPadrao";
import { useAtleta } from "../../sessao/SessaoProvider";

export default function SemanaPadrao() {
  const { apiUrl, atletaId, fetchFn } = useAtleta();
  return (
    <TelaSemanaPadrao
      apiUrl={apiUrl}
      atletaId={atletaId}
      fetchFn={fetchFn}
      aoVoltar={() => (router.canGoBack() ? router.back() : router.replace("/"))}
    />
  );
}
