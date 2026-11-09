import { router } from "expo-router";

import { TelaEvolucao } from "../componentes/TelaEvolucao";
import { config } from "../config";

export default function Inicio() {
  return (
    <TelaEvolucao
      apiUrl={config.apiUrl}
      atletaId={config.atletaId}
      aoAbrirTreino={(id) => router.push(`/treino/${id}`)}
      aoAbrirSemanaPadrao={() => router.push("/semana-padrao")}
    />
  );
}
