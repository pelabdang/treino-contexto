import { router } from "expo-router";
import { useState } from "react";

import { TelaTrocarSenha } from "../../componentes/TelaTrocarSenha";
import { destinoDepoisDeEntrar, inicioDoPapel } from "../../sessao/destino";
import { useSessao } from "../../sessao/SessaoProvider";

export default function TrocarSenha() {
  const { estado, trocarSenha, consumirDestino } = useSessao();
  // Fixa o que valia ao abrir: depois de salvar, a marca de troca obrigatória some, mas a tela ainda é a do primeiro acesso.
  const [primeiroAcesso] = useState(estado.tipo === "dentro" && estado.trocaObrigatoria);
  const papel = estado.tipo === "dentro" ? estado.papel : "atleta";
  return (
    <TelaTrocarSenha
      primeiroAcesso={primeiroAcesso}
      aoTrocar={trocarSenha}
      aoConcluir={async () => {
        // Primeiro acesso: segue para o endereço lembrado (se houver) ou o início do papel. Voluntária: volta.
        if (primeiroAcesso) router.replace(destinoDepoisDeEntrar(papel, await consumirDestino()) as "/");
        else if (router.canGoBack()) router.back();
        else router.replace(inicioDoPapel(papel) as "/");
      }}
      aoVoltar={() => (router.canGoBack() ? router.back() : router.replace(inicioDoPapel(papel) as "/"))}
    />
  );
}
