// "Esta semana" do Início v5 (spec inicio-v5-direcoes, item 3): vem do cartão `esta_semana` da API, com texto pronto. Com pendência de check-in
// encolhe para uma linha ("3 treinos · 2 h 37 min", `apoio_curto`); sem pendência é o herói, com a comparação pronta (`comparacao_texto`).
// Os 7 dias vêm de `dias[]` (rótulo, estado, modalidades e rótulo falado prontos): o app só desenha o ✓, o anel de hoje e o traço.
import { MaterialIcons } from "@expo/vector-icons";
import type { CartaoInicio } from "@treino/api-client";
import { useMemo } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { comFoco } from "../tema/foco";
import { MODALIDADES } from "./modalidades";
import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";

type Props = { cartao: CartaoInicio; heroi: boolean; aoAbrir: (destino: CartaoInicio["destino"]) => void };
type Dia = CartaoInicio["dias"][number];

export function BlocoSemana({ cartao, heroi, aoAbrir }: Props) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const dias = cartao.dias ?? [];
  const apoioHeroi = [cartao.apoio_curto, cartao.comparacao_texto].filter(Boolean).join(" · ") || cartao.apoio;
  const linha = [cartao.valor, cartao.apoio_curto ?? cartao.apoio].filter(Boolean).join(" · ");
  return (
    <View testID="cartao-semana" style={styles.cartao}>
      <Pressable testID="bloco-semana" accessibilityRole="button" accessibilityLabel={cartao.rotulo_acessivel} onPress={() => aoAbrir(cartao.destino)} style={comFoco(styles.topoToque, styles.foco)}>
        <View style={styles.topo}>
          <Text style={styles.sobretitulo}>{cartao.rotulo.toUpperCase()}</Text>
          <MaterialIcons name="chevron-right" size={tamanho.iconeMedio} color={tema.cor["texto-2"]} accessible={false} />
        </View>
        {heroi ? (
          <>
            <Text testID="semana-valor" style={styles.heroi}>{cartao.valor}</Text>
            {apoioHeroi ? <Text style={styles.apoio}>{apoioHeroi}</Text> : null}
          </>
        ) : (
          <Text testID="semana-linha" style={styles.linha}>{linha}</Text>
        )}
      </Pressable>
      {dias.length > 0 && (
        <View testID="semana-dias" style={styles.dias}>
          {dias.map((d) => (
            <DiaDaSemana key={d.rotulo} dia={d} styles={styles} tema={tema} />
          ))}
        </View>
      )}
    </View>
  );
}

type Estilos = ReturnType<typeof criarEstilos>;

function DiaDaSemana({ dia, styles, tema }: { dia: Dia; styles: Estilos; tema: Tema }) {
  const mod = MODALIDADES[dia.modalidades[0] ?? ""];
  const hoje = dia.estado === "hoje";
  // Dia com treino (feito, ou hoje com treino): círculo cheio na cor da modalidade e ✓ branco (no escuro, a cor do fundo, para contrastar com a cor clara).
  const comTreino = dia.estado === "feito" || (hoje && dia.modalidades.length > 0);
  return (
    <View testID={`dia-${dia.rotulo}`} accessible accessibilityLabel={dia.rotulo_acessivel} style={styles.dia}>
      <Text style={styles.diaRotulo}>{dia.rotulo}</Text>
      <View style={[styles.marca, hoje && { borderColor: tema.cor.texto }]}>
        {comTreino ? (
          <View testID={`dia-${dia.rotulo}-feito`} style={[styles.circulo, { backgroundColor: mod ? tema.cor[mod.cor] : tema.cor["texto-2"] }]}>
            <Text style={[styles.visto, { color: tema.escuro ? tema.cor.fundo : "#FFFFFF" }]}>✓</Text>
          </View>
        ) : (
          <View testID={`dia-${dia.rotulo}-${dia.estado}`} style={[styles.circulo, styles.circuloCinza, dia.estado === "futuro" && styles.futuro]} />
        )}
      </View>
    </View>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    cartao: { gap: espaco[3], padding: espaco[4], borderRadius: raio["cartao-destaque"], borderWidth: borda.fina, borderColor: cor.borda, backgroundColor: cor.superficie },
    topoToque: { gap: espaco[1] },
    topo: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
    sobretitulo: { ...fonte.sobretitulo, color: cor["texto-2"] },
    heroi: { ...fonte["numero-heroi"], color: cor.texto },
    apoio: { ...fonte.corpo, color: cor.texto },
    linha: { ...fonte["corpo-forte"], color: cor.texto },
    dias: { flexDirection: "row", justifyContent: "space-between" },
    dia: { alignItems: "center", gap: espaco[1], minWidth: 36 },
    diaRotulo: { ...fonte.legenda, color: cor["texto-2"] }, // todos iguais em texto-2 (contraste 4,5:1), inclusive os futuros
    marca: { width: 32, height: 32, borderRadius: raio.pilula, alignItems: "center", justifyContent: "center", borderWidth: borda.foco, borderColor: "transparent" },
    circulo: { width: 26, height: 26, borderRadius: raio.pilula, alignItems: "center", justifyContent: "center" },
    circuloCinza: { backgroundColor: cor.borda },
    visto: { ...fonte["corpo-forte"], lineHeight: 20 },
    futuro: { opacity: 0.5 },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}
