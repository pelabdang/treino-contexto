// Bloco 1 do treino v3, "Como foi" (spec docs/design/telas/inicio-atleta-v3.md, seção 2): o número do treino e a linha de apoio.
// O feedback vem logo abaixo (CartaoFeedback) ou, sem check-in com prazo aberto, a faixa volt que convida a responder.
import type { Atividade } from "@treino/api-client";
import { useMemo } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { linhaDeApoio, numeroDoTreino } from "../inicio/numero";
import { comFoco } from "../tema/foco";
import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";

export function CartaoComoFoi({ atividade }: { atividade: Atividade }) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const n = numeroDoTreino(atividade);
  const apoio = linhaDeApoio(atividade);
  const falado = `${n.rotulo}, ${n.valor}${n.unidade ? ` ${n.unidade}` : ""}${apoio ? `, ${apoio}` : ""}`;
  return (
    <View testID="cartao-como-foi" accessible accessibilityLabel={falado} style={styles.cartao}>
      <Text style={styles.rotulo}>{n.rotulo}</Text>
      <View style={styles.numeroLinha}>
        <Text testID="numero-treino" style={styles.numero}>
          {n.valor}
        </Text>
        {n.unidade ? <Text style={styles.unidade}>{n.unidade}</Text> : null}
      </View>
      {apoio ? <Text style={styles.apoio}>{apoio}</Text> : null}
    </View>
  );
}

/** Faixa volt do treino sem check-in: "Responda o check-in para receber o feedback". */
export function FaixaCheckin({ aoResponder }: { aoResponder: () => void }) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  return (
    <View testID="faixa-checkin" style={styles.faixa}>
      <Text style={styles.faixaTexto}>Responda o check-in para receber o feedback.</Text>
      <Pressable testID="responder-checkin" accessibilityRole="button" onPress={aoResponder} style={comFoco(styles.botao, styles.foco)}>
        <Text style={styles.botaoTexto}>Responder o check-in (3 perguntas)</Text>
      </Pressable>
    </View>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    cartao: { padding: espaco[4], gap: espaco[1], borderRadius: raio["cartao-destaque"], borderWidth: borda.fina, borderColor: cor.borda, backgroundColor: cor.superficie },
    rotulo: { ...fonte.sobretitulo, color: cor["texto-2"] },
    numeroLinha: { flexDirection: "row", alignItems: "flex-end", gap: espaco[2] },
    numero: { ...fonte["numero-heroi"], color: cor.texto },
    unidade: { ...fonte.rotulo, color: cor["texto-2"], marginBottom: espaco[2] },
    apoio: { ...fonte.corpo, color: cor.texto },
    faixa: { gap: espaco[2], padding: espaco[3], borderRadius: raio.bloco, backgroundColor: cor.marca },
    faixaTexto: { ...fonte["corpo-forte"], color: cor["sobre-marca"] },
    // Dentro da faixa volt o botão é sempre tinta (no escuro `cor.botao` também é volt).
    botao: { minHeight: tamanho.botaoAltura, alignItems: "center", justifyContent: "center", paddingHorizontal: espaco[4], borderRadius: raio.botao, backgroundColor: cor["sobre-marca"] },
    botaoTexto: { ...fonte.botao, color: cor.marca, textAlign: "center" },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}
