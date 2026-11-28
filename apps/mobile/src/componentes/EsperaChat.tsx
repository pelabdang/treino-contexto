// Cartão "pensando" do chat (spec chat.md, "A espera"): sem streaming e sem porcentagem. O tempo só troca o texto (10 s e 25 s); o app não estima nada.
import { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { DICA_ESPERA, ESPERA_LONGA_MS, ESPERA_MEDIA_MS, TEXTO_ESPERA } from "../chat/textos";
import { EsqueletoResposta, useReduzirMovimento } from "./Esqueleto";
import { borda, espaco, fonte, raio, useTema, type Tema } from "../tema";

export function EsperaChat() {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const reduzir = useReduzirMovimento();
  const [fase, setFase] = useState<"curta" | "media" | "longa">("curta");
  useEffect(() => {
    const a = setTimeout(() => setFase("media"), ESPERA_MEDIA_MS);
    const b = setTimeout(() => setFase("longa"), ESPERA_LONGA_MS);
    return () => {
      clearTimeout(a);
      clearTimeout(b);
    };
  }, []);
  const longa = fase === "longa";
  return (
    <View testID="chat-pensando" accessibilityLiveRegion="polite" style={[styles.cartao, longa && styles.longa]}>
      <View style={styles.linha}>
        <ActivityIndicator animating={!reduzir} color={longa ? tema.cor.alerta : tema.cor["texto-2"]} accessibilityLabel="Aguardando a resposta" />
        <Text testID="chat-pensando-texto" style={[styles.texto, longa && { color: tema.cor.alerta }]}>
          {TEXTO_ESPERA[fase]}
        </Text>
      </View>
      {!longa && <EsqueletoResposta />}
      {!longa && <Text style={styles.dica}>{DICA_ESPERA}</Text>}
    </View>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    cartao: { gap: espaco[3], padding: espaco[4], borderRadius: raio.cartao, borderWidth: borda.fina, borderColor: cor.borda, backgroundColor: cor.superficie },
    longa: { backgroundColor: cor["alerta-suave"], borderColor: cor.alerta },
    linha: { flexDirection: "row", alignItems: "center", gap: espaco[3] },
    texto: { ...fonte["corpo-forte"], color: cor.texto, flex: 1 },
    dica: { ...fonte.legenda, color: cor["texto-2"] },
  });
}
