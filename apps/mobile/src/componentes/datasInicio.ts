// Datas curtas em português para o início: "ter 18/03". A data vem da API como AAAA-MM-DD (data local do treino).
const DIAS = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];

export function diaCurto(dataLocal: string): string {
  const [a, m, d] = dataLocal.split("-").map(Number);
  const dia = DIAS[new Date(Date.UTC(a, m - 1, d)).getUTCDay()];
  return `${dia} ${String(d).padStart(2, "0")}/${String(m).padStart(2, "0")}`;
}

const DIAS_LONGOS = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"];

/** "sexta, 21/03" para a data de hoje (no fuso do aparelho). */
export function hojePorExtenso(agora: Date): string {
  return `${DIAS_LONGOS[agora.getDay()]}, ${String(agora.getDate()).padStart(2, "0")}/${String(agora.getMonth() + 1).padStart(2, "0")}`;
}
