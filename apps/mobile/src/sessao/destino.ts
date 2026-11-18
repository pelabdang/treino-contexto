// Para onde ir depois de entrar (spec docs/design/telas/entrar.md). O endereço lembrado é sempre um caminho DO PRÓPRIO app.
export type Papel = "atleta" | "professor";

/** Início de cada papel: o atleta na evolução dos tiros, o professor na caixa do dia. */
export const inicioDoPapel = (papel: Papel): string => (papel === "professor" ? "/caixa-do-dia" : "/");

/** Aceita só caminho interno (uma única "/" no começo, sem domínio, sem barra invertida nem caractere de controle). */
export function destinoValido(caminho: string | null | undefined): caminho is string {
  if (!caminho || typeof caminho !== "string") return false;
  if (!caminho.startsWith("/") || caminho.startsWith("//")) return false;
  if (/[\\\u0000-\u001f]/.test(caminho)) return false;
  if (caminho.includes("://")) return false;
  return !/^\/(entrar|trocar-senha)(\/|\?|#|$)/.test(caminho);
}

const SO_PROFESSOR = ["/caixa-do-dia"];

/** O papel pode abrir esse caminho? A caixa é do professor; as demais telas (início, treino, check-in, semana-padrão) são do atleta. */
export function caminhoDoPapel(papel: Papel, caminho: string): boolean {
  const raiz = "/" + (caminho.split(/[?#]/)[0].split("/")[1] ?? "");
  if (raiz === "/entrar" || raiz === "/trocar-senha") return true;
  const doProfessor = SO_PROFESSOR.includes(raiz);
  return papel === "professor" ? doProfessor : !doProfessor;
}

/** Destino final depois de entrar: o lembrado, se for válido e do papel; senão o início do papel. */
export function destinoDepoisDeEntrar(papel: Papel, lembrado: string | null | undefined): string {
  return destinoValido(lembrado) && caminhoDoPapel(papel, lembrado) ? lembrado : inicioDoPapel(papel);
}
