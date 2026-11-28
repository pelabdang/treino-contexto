// Depois da primeira resposta o endereço da conversa passa a ser `/chat/<id>` (recarregar a página não perde o fio), SEM remontar a tela:
// `router.replace` troca de rota e a tela some por uns 300 a 500 ms (bloqueio da Lia no #623). Na web troca só o endereço do navegador;
// no celular não há endereço, então não há nada a fazer. O id não é dado de saúde; a pergunta e a resposta nunca vão para a URL.
import { Platform } from "react-native";

export function trocarEnderecoDaConversa(id: number): void {
  if (Platform.OS !== "web" || typeof window === "undefined" || !window.history?.replaceState) return;
  window.history.replaceState(window.history.state, "", `/chat/${id}`);
}
