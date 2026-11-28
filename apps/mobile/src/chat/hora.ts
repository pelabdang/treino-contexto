// Horas e dias do chat, só por recorte de texto. `criada_em` já vem em America/Sao_Paulo (ADR 0004, adendo 16): o app não converte fuso
// nem calcula; só escreve "14:32", "hoje", "ontem" e "qua 19/03". `agora` entra de fora para os testes.
import { diaCurto } from "../componentes/datasInicio";

const DIA_LOCAL = /^\d{4}-\d{2}-\d{2}/;

/** "2025-03-20T14:32:10-03:00" -> "14:32". */
export function horaCurta(iso: string): string {
  return iso.length >= 16 ? iso.slice(11, 16) : "";
}

const doisDigitos = (n: number) => String(n).padStart(2, "0");
const diaIso = (d: Date) => `${d.getFullYear()}-${doisDigitos(d.getMonth() + 1)}-${doisDigitos(d.getDate())}`;

/** "hoje", "ontem" ou "qua 19/03", pelo dia que a API mandou comparado ao dia do aparelho. */
export function rotuloDoDia(iso: string, agora: Date): string {
  if (!DIA_LOCAL.test(iso)) return "";
  const dia = iso.slice(0, 10);
  if (dia === diaIso(agora)) return "hoje";
  const ontem = new Date(agora.getFullYear(), agora.getMonth(), agora.getDate() - 1);
  if (dia === diaIso(ontem)) return "ontem";
  return diaCurto(dia);
}

/** "hoje, 14:32", "ontem, 20:10", "qua 19/03, 07:45" (lista de conversas). */
export function dataDaLista(iso: string, agora: Date): string {
  const dia = rotuloDoDia(iso, agora);
  const hora = horaCurta(iso);
  return [dia, hora].filter(Boolean).join(", ");
}
