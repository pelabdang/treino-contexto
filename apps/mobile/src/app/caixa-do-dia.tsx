import { TelaCaixaDoDia } from "../componentes/TelaCaixaDoDia";
import { config } from "../config";

export default function CaixaDoDia() {
  return <TelaCaixaDoDia apiUrl={config.apiUrl} professorId={config.professorId} />;
}
