// Datas da tela da semana-padrão. É calendário do aparelho, não métrica (docs/design/telas/semana-padrao.md).

const dois = (n: number) => String(n).padStart(2, "0");

/** Data local `AAAA-MM-DD` (sem passar por UTC). */
export function isoLocal(d: Date): string {
  return `${d.getFullYear()}-${dois(d.getMonth() + 1)}-${dois(d.getDate())}`;
}

/** `AAAA-MM-DD` para `dd/mm/aaaa`. */
export function isoParaBr(iso: string): string {
  const [a, m, d] = iso.split("-");
  return `${d}/${m}/${a}`;
}

/** `AAAA-MM-DD` para `dd/mm/aa`. */
export function isoParaBrCurto(iso: string): string {
  const [a, m, d] = iso.split("-");
  return `${d}/${m}/${a.slice(2)}`;
}

/** Máscara `dd/mm/aaaa`: só dígitos, no máximo 8, barras no lugar. */
export function mascararData(texto: string): string {
  const d = texto.replace(/\D/g, "").slice(0, 8);
  if (d.length <= 2) return d;
  if (d.length <= 4) return `${d.slice(0, 2)}/${d.slice(2)}`;
  return `${d.slice(0, 2)}/${d.slice(2, 4)}/${d.slice(4)}`;
}

export type LeituraData = { tipo: "vazia" } | { tipo: "invalida" } | { tipo: "ok"; iso: string };

/** Lê `dd/mm/aaaa`. Dia que não existe (31/02) é inválido. */
export function lerDataBr(texto: string): LeituraData {
  if (!texto.trim()) return { tipo: "vazia" };
  const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(texto.trim());
  if (!m) return { tipo: "invalida" };
  const dia = Number(m[1]);
  const mes = Number(m[2]);
  const ano = Number(m[3]);
  const d = new Date(ano, mes - 1, dia);
  if (ano < 1900 || d.getFullYear() !== ano || d.getMonth() !== mes - 1 || d.getDate() !== dia) return { tipo: "invalida" };
  return { tipo: "ok", iso: `${m[3]}-${m[2]}-${m[1]}` };
}

/** A próxima segunda-feira depois de `hoje` (se hoje é segunda, a de daqui a 7 dias). */
export function proximaSegunda(hoje: Date): Date {
  const d = new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate());
  const dias = (8 - d.getDay()) % 7 || 7;
  d.setDate(d.getDate() + dias);
  return d;
}
