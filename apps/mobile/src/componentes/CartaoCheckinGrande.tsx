// Cartão grande de check-in do Início v5 (spec inicio-v5-direcoes, item 2): aparece só quando há treino sem check-in. A pergunta (`pergunta_texto`, com "ontem" ou o dia da
// semana), a data, a hora e a duração vêm prontas da API; sem `pergunta_texto` cai num texto fixo.
import { MaterialIcons } from "@expo/vector-icons";
import type { components } from "@treino/api-client";
import { useMemo } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { comFoco } from "../tema/foco";
import { diaCurto } from "./datasInicio";
import { MODALIDADES } from "./modalidades";
import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";

type Pendente = components["schemas"]["PendenteOut"];

type Props = {
  treino: Pendente;
  /** Quantos outros treinos esperam check-in (a API conta; o app só mostra). */
  outros: number;
  aoResponder: () => void;
  aoVerOutros: () => void;
};

export function CartaoCheckinGrande({ treino, outros, aoResponder, aoVerOutros }: Props) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const mod = MODALIDADES[treino.modalidade];
  const nome = mod?.nome ?? "Treino";
  return (
    <View testID="checkin-grande" style={styles.cartao}>
      <View style={styles.linha}>
        {mod && <MaterialIcons name={mod.icone} size={tamanho.iconeGrande} color={tema.cor["sobre-marca"]} accessible={false} />}
        <Text style={styles.treino}>{`${nome} · ${diaCurto(treino.data_local)} · ${treino.hora_local} · ${treino.duracao}`}</Text>
      </View>
      <Text accessibilityRole="header" style={styles.pergunta}>
        {treino.pergunta_texto || (mod ? `Como foi o treino de ${mod.nome.toLowerCase()}?` : "Como foi o treino?")}
      </Text>
      <Text style={styles.apoio}>3 perguntas, uns 30 segundos. Você recebe o feedback deste treino.</Text>
      <Pressable testID="responder-checkin" accessibilityRole="button" onPress={aoResponder} style={comFoco(styles.botao, styles.foco)}>
        <Text style={styles.botaoTexto}>Responder o check-in</Text>
      </Pressable>
      {outros > 0 && (
        <Pressable testID="outros-sem-checkin" accessibilityRole="button" onPress={aoVerOutros} style={comFoco(styles.mais, styles.foco)}>
          <Text style={styles.maisTexto}>{outros === 1 ? "+ 1 treino sem check-in ›" : `+ ${outros} treinos sem check-in ›`}</Text>
        </Pressable>
      )}
    </View>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    cartao: { gap: espaco[3], padding: espaco[4], borderRadius: raio["cartao-destaque"], backgroundColor: cor.marca },
    linha: { flexDirection: "row", alignItems: "center", gap: espaco[2] },
    treino: { ...fonte.rotulo, color: cor["sobre-marca"], flex: 1 },
    pergunta: { ...fonte["titulo-tela"], color: cor["sobre-marca"] },
    apoio: { ...fonte.corpo, color: cor["sobre-marca"] },
    botao: { minHeight: tamanho.botaoAltura, alignItems: "center", justifyContent: "center", paddingHorizontal: espaco[4], borderRadius: raio.botao, backgroundColor: cor["sobre-marca"] }, // sobre o volt o botão é sempre tinta
    botaoTexto: { ...fonte.botao, color: cor.marca, textAlign: "center" },
    mais: { minHeight: tamanho.alvoMinimo, justifyContent: "center", alignSelf: "flex-start" },
    maisTexto: { ...fonte["corpo-forte"], color: cor["sobre-marca"] },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor["sobre-marca"], outlineOffset: 2 },
  });
}
