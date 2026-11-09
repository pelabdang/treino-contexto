import { router } from "expo-router";

import { TelaSemanaPadrao } from "../componentes/TelaSemanaPadrao";
import { config } from "../config";

export default function SemanaPadrao() {
  return (
    <TelaSemanaPadrao
      apiUrl={config.apiUrl}
      atletaId={config.atletaId}
      aoVoltar={() => (router.canGoBack() ? router.back() : router.replace("/"))}
    />
  );
}
