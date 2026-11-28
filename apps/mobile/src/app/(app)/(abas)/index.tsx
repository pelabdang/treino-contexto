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
      aoAbrirDestino={(d) => {
        // `destino` da API: a Evolução (já com a série), a semana-padrão ou um treino.
        if (d.tela === "treino" && d.atividade_id != null) router.push(`/treino/${d.atividade_id}`);
        else if (d.tela === "semana_padrao") router.push("/semana-padrao");
        else router.navigate(d.serie_id ? { pathname: "/evolucao", params: { serie: d.serie_id } } : "/evolucao");
      }}
    />
  );
}
