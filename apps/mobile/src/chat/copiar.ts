// Copiar a resposta (adendo da spec do chat): só o `texto`, sem links, hora nem rótulo. Devolve se deu certo; nunca lança.
import * as Clipboard from "expo-clipboard";

export async function copiarTexto(texto: string): Promise<boolean> {
  try {
    return (await Clipboard.setStringAsync(texto)) !== false;
  } catch {
    return false;
  }
}
