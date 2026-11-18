// Guarda das telas de dentro (#502): só abre com acesso. Sem acesso leva a /entrar e lembra o endereço pedido; com a troca de senha
// obrigatória abre /trocar-senha antes de qualquer outra; o papel que não é dono da tela vai ao início do próprio papel.
import { Redirect, Stack, usePathname } from "expo-router";
import { useEffect } from "react";

import { TelaSemRede, TelaVerificando } from "../../componentes/TelaAcesso";
import { caminhoDoPapel, inicioDoPapel } from "../../sessao/destino";
import { useSessao } from "../../sessao/SessaoProvider";
import { useTema } from "../../tema";

export default function LayoutDeDentro() {
  const { cor } = useTema();
  const { estado, registrarCaminho, lembrarDestino, verificarDeNovo } = useSessao();
  const caminho = usePathname();
  registrarCaminho(caminho);
  const lembrar = estado.tipo === "sem_acesso" && estado.lembrar;
  useEffect(() => {
    if (lembrar) lembrarDestino(caminho);
  }, [lembrar, caminho, lembrarDestino]);

  if (estado.tipo === "verificando") return <TelaVerificando />;
  if (estado.tipo === "sem_rede") return <TelaSemRede aoTentar={verificarDeNovo} />;
  if (estado.tipo === "sem_acesso") return <Redirect href="/entrar" />;
  if (estado.trocaObrigatoria && caminho !== "/trocar-senha") return <Redirect href="/trocar-senha" />;
  if (!caminhoDoPapel(estado.papel, caminho)) return <Redirect href={inicioDoPapel(estado.papel) as "/"} />;
  return <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: cor.fundo } }} />;
}
