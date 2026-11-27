import { router } from "expo-router";

import { TelaInicio } from "../../../componentes/TelaInicio";
import { useContadorDeFoco } from "../../../navegacao/useContadorDeFoco";
import { useAtleta, useSessao } from "../../../sessao/SessaoProvider";

// Início v3: último treino, quinzena e treinos recentes (spec inicio-atleta-v3).
export default function Inicio() {
  const atualizar = useContadorDeFoco();
  const { apiUrl, atletaId, fetchFn } = useAtleta();
  const { estado } = useSessao();
  return (
    <TelaInicio
      apiUrl={apiUrl}
      atletaId={atletaId}
      fetchFn={fetchFn}
      nome={estado.tipo === "dentro" ? estado.nome : undefined}
      atualizar={atualizar}
      aoAbrirTreino={(id) => router.push(`/treino/${id}`)}
      aoResponderCheckin={(id) => router.push(`/checkin/${id}`)}
      aoVerTodos={() => router.navigate("/treinos")}
    />
  );
}
