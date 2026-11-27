// Cartão "Seus últimos 14 dias" (spec v3, seção 4): condicionamento (linha cheia) e fadiga (tracejada) e a frase de análise que a API
// manda em `frase_forma`. Sem CTL, ATL ou TSB na tela; selo "estimativa" sempre. O app só desenha: os números vêm prontos.
import type { SerieCarga } from "@treino/api-client";
import { useMemo } from "react";
import { StyleSheet, Text, View } from "react-native";
import Svg, { Line, Polyline } from "react-native-svg";

import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";

const LARGURA = 300;
const ALTURA = 110;
const MARGEM = 8;

/** Pontos "x,y" da série; eixo y compartilhado (zero embaixo). Uma só medida vira um ponto no meio. */
export function pontos(valores: number[], maximo: number): string {
  const passo = valores.length > 1 ? (LARGURA - 2 * MARGEM) / (valores.length - 1) : 0;
  return valores
    .map((v, i) => {
      const x = valores.length > 1 ? MARGEM + i * passo : LARGURA / 2;
      const y = ALTURA - MARGEM - (maximo > 0 ? (v / maximo) * (ALTURA - 2 * MARGEM) : 0);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export function CartaoQuinzena({ serie }: { serie: SerieCarga }) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const dias = serie.dias ?? [];
  const frase = serie.frase_forma ?? null;
  const aprendendo = frase?.tipo === "aprendendo" || dias.length === 0 || dias.every((d) => d.aprendendo);
  const ultimo = dias[dias.length - 1];
  const ctl = dias.map((d) => d.ctl);
  const atl = dias.map((d) => d.atl);
  const maximo = Math.max(1, ...ctl, ...atl);
  const cCond = tema.cor["grafico.pace"];
  const cFad = tema.cor["grafico.fc"];

  return (
    <View testID="quinzena" style={styles.cartao}>
      <View style={styles.cabecalho}>
        <Text accessibilityRole="header" style={styles.titulo}>
          Seus últimos 14 dias
        </Text>
        <View style={styles.selo}>
          <Text style={styles.seloTexto}>estimativa</Text>
        </View>
      </View>
      {!aprendendo && (
        <>
          <Svg testID="grafico-quinzena" accessible={false} importantForAccessibility="no-hide-descendants" viewBox={`0 0 ${LARGURA} ${ALTURA}`} style={styles.grafico}>
            <Line x1={MARGEM} x2={LARGURA - MARGEM} y1={ALTURA - MARGEM} y2={ALTURA - MARGEM} stroke={tema.cor["grafico.grade"]} strokeWidth={1} />
            <Polyline fill="none" stroke={cCond} strokeWidth={tamanho.graficoLinhaPrincipal} strokeLinecap="round" strokeLinejoin="round" points={pontos(ctl, maximo)} />
            <Polyline fill="none" stroke={cFad} strokeWidth={tamanho.graficoLinhaMedia} strokeDasharray="4 4" strokeLinecap="round" points={pontos(atl, maximo)} />
          </Svg>
          <View style={styles.legenda}>
            <View style={styles.item}>
              <View style={[styles.tracoCheio, { backgroundColor: cCond }]} />
              <Text style={styles.rotulo}>Condicionamento</Text>
              <Text testID="valor-condicionamento" style={styles.valor}>
                {ultimo?.ctl_texto ?? ""}
              </Text>
            </View>
            <View style={styles.item}>
              <View style={[styles.tracoTracejado, { borderColor: cFad }]} />
              <Text style={styles.rotulo}>Fadiga</Text>
              <Text testID="valor-fadiga" style={styles.valor}>
                {ultimo?.atl_texto ?? ""}
              </Text>
            </View>
          </View>
        </>
      )}
      {frase ? (
        <Text testID="frase-quinzena" style={styles.frase}>
          {frase.texto}
        </Text>
      ) : aprendendo ? (
        <Text testID="frase-quinzena" style={styles.frase}>
          Ainda estamos aprendendo o seu ritmo. Com mais treinos, o gráfico aparece aqui.
        </Text>
      ) : null}
    </View>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    cartao: { padding: espaco[4], gap: espaco[3], borderRadius: raio.cartao, borderWidth: borda.fina, borderColor: cor.borda, backgroundColor: cor.superficie },
    cabecalho: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: espaco[2] },
    titulo: { ...fonte["titulo-secao"], color: cor.texto },
    selo: { paddingHorizontal: espaco[2], paddingVertical: 2, borderRadius: raio.pilula, backgroundColor: cor["superficie-2"] },
    seloTexto: { ...fonte.legenda, color: cor["texto-2"] },
    grafico: { width: "100%", aspectRatio: LARGURA / ALTURA },
    legenda: { gap: espaco[2] },
    item: { flexDirection: "row", alignItems: "center", gap: espaco[2] },
    tracoCheio: { width: 24, height: 3, borderRadius: 2 },
    tracoTracejado: { width: 24, height: 0, borderTopWidth: 3, borderStyle: "dashed" },
    rotulo: { ...fonte.rotulo, color: cor["texto-2"], flex: 1 },
    valor: { ...fonte["numero-grande"], color: cor.texto },
    frase: { ...fonte.corpo, color: cor.texto },
  });
}
