import { router } from "expo-router";

import { TelaEvolucao } from "../componentes/TelaEvolucao";
import { config } from "../config";
import { useContadorDeFoco } from "../navegacao/useContadorDeFoco";

export default function Inicio() {
  const atualizar = useContadorDeFoco();
  return (
    <TelaEvolucao
      apiUrl={config.apiUrl}
      atletaId={config.atletaId}
      atualizar={atualizar}
      aoAbrirTreino={(id) => router.push(`/treino/${id}`)}
      aoAbrirSemanaPadrao={() => router.push("/semana-padrao")}
      aoAbrirCheckinsPendentes={() => router.push("/checkins-pendentes")}
    />
  );
}
