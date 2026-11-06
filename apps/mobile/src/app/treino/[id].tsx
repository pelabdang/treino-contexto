import { router, useLocalSearchParams } from "expo-router";

import { TelaTreino } from "../../componentes/TelaTreino";
import { config } from "../../config";

export default function Treino() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const atividadeId = Number(Array.isArray(id) ? id[0] : id);
  return (
    <TelaTreino
      apiUrl={config.apiUrl}
      atletaId={config.atletaId}
      atividadeId={atividadeId}
      aoVoltar={() => (router.canGoBack() ? router.back() : router.replace("/"))}
    />
  );
}
