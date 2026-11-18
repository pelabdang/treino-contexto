import { router, useLocalSearchParams } from "expo-router";

import { TelaTreino } from "../../../componentes/TelaTreino";
import { useContadorDeFoco } from "../../../navegacao/useContadorDeFoco";
import { useAtleta } from "../../../sessao/SessaoProvider";

export default function Treino() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const atividadeId = Number(Array.isArray(id) ? id[0] : id);
  const atualizar = useContadorDeFoco();
  const { apiUrl, atletaId, fetchFn } = useAtleta();
  const abrirCheckin = () => router.push(`/checkin/${atividadeId}`);
  return (
    <TelaTreino
      apiUrl={apiUrl}
      atletaId={atletaId}
      fetchFn={fetchFn}
      atividadeId={atividadeId}
      atualizar={atualizar}
      aoFazerCheckin={abrirCheckin}
      aoEditarCheckin={abrirCheckin}
      aoVoltar={() => (router.canGoBack() ? router.back() : router.replace("/"))}
    />
  );
}
