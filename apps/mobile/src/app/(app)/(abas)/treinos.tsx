import { router, useLocalSearchParams } from "expo-router";

import { TelaTreinos } from "../../../componentes/TelaTreinos";
import { useContadorDeFoco } from "../../../navegacao/useContadorDeFoco";
import { useAtleta } from "../../../sessao/SessaoProvider";

// Treinos: a lista real (GET /atletas/{id}/atividades). `?filtro=sem-checkin` abre já filtrada (link do Início).
export default function Treinos() {
  const { filtro } = useLocalSearchParams<{ filtro?: string }>();
  const atualizar = useContadorDeFoco();
  const { apiUrl, atletaId, fetchFn } = useAtleta();
  return (
    <TelaTreinos
      apiUrl={apiUrl}
      atletaId={atletaId}
      fetchFn={fetchFn}
      atualizar={atualizar}
      semCheckinInicial={(Array.isArray(filtro) ? filtro[0] : filtro) === "sem-checkin"}
      aoAbrirTreino={(id) => router.push(`/treino/${id}`)}
    />
  );
}
