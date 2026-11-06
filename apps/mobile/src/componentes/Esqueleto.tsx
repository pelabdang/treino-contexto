import { useEffect, useMemo, useState } from "react";
import { AccessibilityInfo, Animated, Easing, StyleSheet, View } from "react-native";

import { borda, espaco, movimento, raio, useTema, type Tema } from "../tema";

/** Segue o "reduzir movimento" do sistema; sem a resposta ainda, assume que há movimento. */
function useReduzirMovimento(): boolean {
  const [reduzir, setReduzir] = useState(false);
  useEffect(() => {
    let ativo = true;
    AccessibilityInfo.isReduceMotionEnabled?.()
      .then((v) => ativo && setReduzir(v))
      .catch(() => {});
    const sub = AccessibilityInfo.addEventListener?.("reduceMotionChanged", setReduzir);
    return () => {
      ativo = false;
      sub?.remove?.();
    };
  }, []);
  return reduzir;
}

/** Pulso de opacidade 1 -> 0,6 em `movimento.esqueleto` ms (tokens). Parado com "reduzir movimento". */
function usePulso(reduzir: boolean): Animated.Value {
  const [opacidade] = useState(() => new Animated.Value(1));
  useEffect(() => {
    if (reduzir) {
      opacidade.setValue(1);
      return;
    }
    const metade = movimento.esqueleto / 2;
    const anim = Animated.loop(
      Animated.sequence([
        Animated.timing(opacidade, { toValue: 0.6, duration: metade, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        Animated.timing(opacidade, { toValue: 1, duration: metade, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      ]),
    );
    anim.start();
    return () => anim.stop();
  }, [reduzir, opacidade]);
  return opacidade;
}

/** Esqueleto dos três cartões da tela de evolução (último treino, gráfico, lista). Só decorativo: o texto "Carregando" fica fora. */
export function EsqueletoEvolucao() {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const opacidade = usePulso(useReduzirMovimento());
  const barra = (largura: number | `${number}%`, altura: number, chave?: string) => (
    <View key={chave} style={[styles.barra, { width: largura, height: altura }]} />
  );
  return (
    <Animated.View
      testID="esqueleto-evolucao"
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
      style={{ opacity: opacidade }}
    >
      <View style={styles.cartao}>
        {barra("50%", 20)}
        {barra("30%", 16)}
        {barra("40%", 44)}
        {barra("60%", 20)}
      </View>
      <View style={styles.cartao}>
        {barra("30%", 20)}
        {barra("100%", 160)}
        {barra("100%", 160)}
      </View>
      <View style={styles.cartao}>
        {barra("30%", 20)}
        {[0, 1, 2].map((i) => barra("100%", 40, `l${i}`))}
      </View>
    </Animated.View>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    cartao: {
      marginTop: espaco[4],
      padding: espaco[4],
      gap: espaco[3],
      borderRadius: raio.grande,
      borderWidth: borda.fina,
      borderColor: cor.borda,
      backgroundColor: cor.superficie,
    },
    barra: { borderRadius: raio.pequeno, backgroundColor: cor["superficie-2"] },
  });
}
