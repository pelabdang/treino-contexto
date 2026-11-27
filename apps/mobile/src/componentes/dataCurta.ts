// "2025-03-04" -> "04/03/25" (só recorte de texto da data local da API).
export function dataCurta(data: string): string {
  const [a, m, d] = data.split("-");
  return `${d}/${m}/${a.slice(2)}`;
}
