import { router, useLocalSearchParams } from "expo-router";

import { TelaTreino } from "../../componentes/TelaTreino";
import { config } from "../../config";
import { useContadorDeFoco } from "../../navegacao/useContadorDeFoco";

export default function Treino() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const atividadeId = Number(Array.isArray(id) ? id[0] : id);
  const atualizar = useContadorDeFoco();
  const abrirCheckin = () => router.push(`/checkin/${atividadeId}`);
  return (
    <TelaTreino
      apiUrl={config.apiUrl}
      atletaId={config.atletaId}
      atividadeId={atividadeId}
      atualizar={atualizar}
      aoFazerCheckin={abrirCheckin}
      aoEditarCheckin={abrirCheckin}
      aoVoltar={() => (router.canGoBack() ? router.back() : router.replace("/"))}
    />
  );
}
