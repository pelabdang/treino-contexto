import { router } from "expo-router";
import { useEffect } from "react";

import { TelaSemRede, TelaVerificando } from "../componentes/TelaAcesso";
import { TelaEntrar } from "../componentes/TelaEntrar";
import { destinoDepoisDeEntrar, type Papel } from "../sessao/destino";
import { useSessao } from "../sessao/SessaoProvider";

// Única rota que abre sem acesso. Quem está dentro segue: com a troca de senha obrigatória vai a /trocar-senha (o endereço lembrado
// espera); senão, ao endereço lembrado (se for do papel e do próprio app) ou ao início do papel.
export default function Entrar() {
  const { estado, entrar, verificarDeNovo } = useSessao();
  if (estado.tipo === "verificando") return <TelaVerificando />;
  if (estado.tipo === "sem_rede") return <TelaSemRede aoTentar={verificarDeNovo} />;
  if (estado.tipo === "dentro") return <Seguir papel={estado.papel} trocaObrigatoria={estado.trocaObrigatoria} />;
  return <TelaEntrar expirou={estado.expirou} saiu={!estado.expirou && !estado.lembrar} aoEntrar={entrar} />;
}

function Seguir({ papel, trocaObrigatoria }: { papel: Papel; trocaObrigatoria: boolean }) {
  const { consumirDestino } = useSessao();
  useEffect(() => {
    let vivo = true;
    if (trocaObrigatoria) {
      router.replace("/trocar-senha");
      return;
    }
    void consumirDestino().then((d) => {
      if (vivo) router.replace(destinoDepoisDeEntrar(papel, d) as "/");
    });
    return () => {
      vivo = false;
    };
  }, [papel, trocaObrigatoria, consumirDestino]);
  return <TelaVerificando />;
}
