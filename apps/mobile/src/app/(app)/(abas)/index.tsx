import { router } from "expo-router";

import { TelaInicio } from "../../../componentes/TelaInicio";
import { ENTRADA_CHAT_NO_INICIO } from "../../../chat/textos";
import { useContadorDeFoco } from "../../../navegacao/useContadorDeFoco";
import { useAtleta, useSessao } from "../../../sessao/SessaoProvider";

// Início v5 (spec inicio-v5-direcoes): check-in, esta semana, chat, hoje e último treino.
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
      aoVerPendentes={() => router.navigate("/treinos?filtro=sem-checkin")}
      aoAbrirChat={ENTRADA_CHAT_NO_INICIO ? () => router.push({ pathname: "/chat", params: { foco: "1" } }) : undefined}
      aoPerguntar={(i) => router.push({ pathname: "/chat", params: { pronta: String(i) } })}
      aoAbrirConversas={() => router.push("/chat/conversas")}
      aoAbrirDestino={(d) => {
        // `destino` da API: a Evolução (já com a série), a semana-padrão ou um treino.
        if (d.tela === "treino" && d.atividade_id != null) router.push(`/treino/${d.atividade_id}`);
        else if (d.tela === "semana_padrao") router.push("/semana-padrao");
        else router.navigate(d.serie_id ? { pathname: "/evolucao", params: { serie: d.serie_id } } : "/evolucao");
      }}
    />
  );
}
