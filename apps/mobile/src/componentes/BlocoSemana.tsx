// "Esta semana" do Início v5 (spec inicio-v5-direcoes, item 3): vem do cartão `esta_semana` da API, com texto pronto. Com pendência de check-in ele
// encolhe para uma linha; sem pendência é o herói. Os 7 dias (✓, anel de hoje) dependem de dado que a API ainda não manda e ficam de fora.
import { MaterialIcons } from "@expo/vector-icons";
import type { CartaoInicio } from "@treino/api-client";
import { useMemo } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { comFoco } from "../tema/foco";
import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";

type Props = { cartao: CartaoInicio; heroi: boolean; aoAbrir: (destino: CartaoInicio["destino"]) => void };

export function BlocoSemana({ cartao, heroi, aoAbrir }: Props) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  return (
    <Pressable testID="bloco-semana" accessibilityRole="button" accessibilityLabel={cartao.rotulo_acessivel} onPress={() => aoAbrir(cartao.destino)} style={comFoco(styles.cartao, styles.foco)}>
      <View style={styles.topo}>
        <Text style={styles.sobretitulo}>{cartao.rotulo.toUpperCase()}</Text>
        <MaterialIcons name="chevron-right" size={tamanho.iconeMedio} color={tema.cor["texto-2"]} accessible={false} />
      </View>
      {heroi ? (
        <>
          <Text testID="semana-valor" style={styles.heroi}>{cartao.valor}</Text>
          {cartao.apoio ? <Text style={styles.apoio}>{cartao.apoio}</Text> : null}
        </>
      ) : (
        <Text testID="semana-linha" style={styles.linha}>{[cartao.valor, cartao.apoio].filter(Boolean).join(" · ")}</Text>
      )}
    </Pressable>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    cartao: { gap: espaco[1], padding: espaco[4], borderRadius: raio["cartao-destaque"], borderWidth: borda.fina, borderColor: cor.borda, backgroundColor: cor.superficie },
    topo: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
    sobretitulo: { ...fonte.sobretitulo, color: cor["texto-2"] },
    heroi: { ...fonte["numero-heroi"], color: cor.texto },
    apoio: { ...fonte.corpo, color: cor.texto },
    linha: { ...fonte["corpo-forte"], color: cor.texto },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}
