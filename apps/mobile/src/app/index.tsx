import { TelaEvolucao } from "../componentes/TelaEvolucao";
import { config } from "../config";

export default function Inicio() {
  return <TelaEvolucao apiUrl={config.apiUrl} atletaId={config.atletaId} />;
}
