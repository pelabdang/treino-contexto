import { TelaCaixaDoDia } from "../../../componentes/TelaCaixaDoDia";
import { useProfessor } from "../../../sessao/SessaoProvider";

export default function CaixaDoDia() {
  const { apiUrl, professorId, fetchFn } = useProfessor();
  return <TelaCaixaDoDia apiUrl={apiUrl} professorId={professorId} fetchFn={fetchFn} />;
}
