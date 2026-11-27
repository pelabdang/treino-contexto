import type { SerieEvolucao } from "@treino/api-client";
import { useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, View, type LayoutChangeEvent } from "react-native";
import Svg, { Circle, G, Line, Polygon, Polyline, Rect, Text as SvgTexto } from "react-native-svg";

import { espaco, familia, fonte, tamanho, useTema, type Tema } from "../tema";

// Gráfico de uma série da Evolução (spec evolucao-v1). Só converte valor em posição: faixa, eixo, marcas, textos e selos vêm
// prontos da API; o app não calcula pace, mediana, faixa nem frase (ADR 0004, adendo 15).

const LARGURA_PADRAO = 320;
const ALTURA = 220;
const MARGEM = { esq: 44, dir: 16, topo: 14, base: 30 };
const ALVO = tamanho.alvoMinimo;
const ALVO_MIN = 24;

type Props = {
  serie: SerieEvolucao;
  /** Índice do ponto selecionado em `serie.pontos` (controlado por quem usa o gráfico). */
  selecionado: number | null;
  aoSelecionar: (indice: number) => void;
};

type Pos = { x: number; y: number; indice: number };

/** `true` nas séries de volume por semana: uma barra por semana, partindo do zero. */
export const ehVolume = (serie: Pick<SerieEvolucao, "id">) => serie.id.includes("volume");

export function GraficoSerie({ serie, selecionado, aoSelecionar }: Props) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const [largura, setLargura] = useState(LARGURA_PADRAO);
  const aoMedir = (e: LayoutChangeEvent) => {
    const w = Math.round(e.nativeEvent.layout.width);
    if (w > 0 && w !== largura) setLargura(w);
  };
  const { cor } = tema;
  const eixo = serie.eixo;
  const area = ALTURA - MARGEM.topo - MARGEM.base;
  const barras = ehVolume(serie);
  const aprendendo = serie.aprendendo_texto != null || serie.pontos.some((p) => p.aprendendo);

  const y = (v: number) => {
    if (!eixo) return MARGEM.topo + area / 2;
    const frac = (v - eixo.minimo) / (eixo.maximo - eixo.minimo || 1);
    return MARGEM.topo + (eixo.invertido ? frac : 1 - frac) * area;
  };

  // Posição horizontal pela data real (o intervalo entre treinos importa); um ponto só fica no meio.
  const pos: Pos[] = useMemo(() => {
    const ini = MARGEM.esq + (barras ? 8 : 0);
    const fim = largura - MARGEM.dir - (barras ? 8 : 0);
    const t = serie.pontos.map((p) => Date.parse(`${p.data}T00:00:00Z`));
    const t0 = Math.min(...t);
    const t1 = Math.max(...t);
    return serie.pontos.flatMap((p, indice) =>
      p.valor == null
        ? []
        : [{ indice, x: t1 === t0 ? (ini + fim) / 2 : ini + ((t[indice] - t0) / (t1 - t0)) * (fim - ini), y: y(p.valor) }],
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [serie, largura, barras]);

  // Faixa horizontal de toque de cada ponto: até 44, cortada no meio do caminho até o vizinho, nunca abaixo de 24.
  const alvos = pos.map((p, i) => {
    const esq = i > 0 ? (p.x - pos[i - 1].x) / 2 : ALVO / 2;
    const dir = i < pos.length - 1 ? (pos[i + 1].x - p.x) / 2 : ALVO / 2;
    const a = Math.max(Math.min(esq, ALVO / 2), ALVO_MIN / 2);
    const b = Math.max(Math.min(dir, ALVO / 2), ALVO_MIN / 2);
    return { ...p, esq: p.x - a, largura: a + b };
  });

  const ref = serie.referencia;
  const base = barras && eixo ? y(Math.max(eixo.minimo, 0)) : 0;
  const legenda = [
    barras ? { chave: "semana", texto: "semana" } : { chave: "treino", texto: "treino" },
    ...(!barras && serie.pontos.some((p) => p.fora_do_normal) ? [{ chave: "fora", texto: "fora do normal" }] : []),
    ...(!barras && serie.pontos.some((p) => p.melhor) ? [{ chave: "melhor", texto: "melhor" }] : []),
    ...(ref ? [{ chave: "normal", texto: "normal" }] : []),
  ];
  const datas = (() => {
    const n = serie.pontos.length;
    if (n === 0) return [];
    // Datas longas ("semana de 10/03") não cabem três no eixo: só a primeira e a última.
    const longa = serie.pontos.some((p) => p.data_texto.length > 9);
    const idx = n === 1 ? [0] : n === 2 || longa ? [0, n - 1] : [0, Math.floor((n - 1) / 2), n - 1];
    return idx.map((i, k) => ({ i, ancora: k === 0 ? "start" : k === idx.length - 1 ? "end" : "middle", texto: serie.pontos[i].data_texto }));
  })();

  return (
    <View testID="grafico-serie">
      {eixo?.invertido && (
        <Text testID="mais-rapido" style={styles.dica}>
          mais rápido ↑
        </Text>
      )}
      <View
        accessible
        accessibilityRole="image"
        accessibilityLabel={serie.frase.texto}
        onLayout={aoMedir}
        style={{ height: ALTURA }}
      >
        <Svg width={largura} height={ALTURA}>
          {eixo?.marcas.map((m) => (
            <G key={m.rotulo + m.valor}>
              <Line x1={MARGEM.esq} x2={largura - MARGEM.dir} y1={y(m.valor)} y2={y(m.valor)} stroke={cor["grafico.grade"]} strokeWidth={1} />
              <SvgTexto x={MARGEM.esq - 6} y={y(m.valor) + 4} fontSize={11.5} fontFamily={familia.medio} fill={cor["texto-2"]} textAnchor="end">
                {m.rotulo}
              </SvgTexto>
            </G>
          ))}
          {ref && eixo && (
            <G testID="faixa-normal">
              <Rect x={MARGEM.esq} y={y(ref.maximo)} width={largura - MARGEM.esq - MARGEM.dir} height={Math.max(y(ref.minimo) - y(ref.maximo), 1)} fill={cor["marca-suave"]} />
              <SvgTexto x={largura - MARGEM.dir - 6} y={Math.max(y(ref.maximo) + 14, MARGEM.topo + 12)} fontSize={11.5} fontFamily={familia.medio} fill={cor.link} textAnchor="end">
                {ref.texto}
              </SvgTexto>
            </G>
          )}
          {barras
            ? pos.map((p) => (
                <Rect
                  key={`b${p.indice}`}
                  x={p.x - Math.max(Math.min((largura - MARGEM.esq - MARGEM.dir) / (serie.pontos.length * 2.4), 14), 3)}
                  y={Math.min(p.y, base)}
                  width={Math.max(Math.min((largura - MARGEM.esq - MARGEM.dir) / (serie.pontos.length * 1.2), 28), 6)}
                  height={Math.max(Math.abs(base - p.y), 1)}
                  fill={cor["grafico.pace"]}
                  opacity={serie.pontos[p.indice].parcial ? 0.45 : 1}
                />
              ))
            : pos.length > 1 && (
                <Polyline
                  testID={aprendendo ? "linha-pontilhada" : "linha-serie"}
                  points={pos.map((p) => `${p.x},${p.y}`).join(" ")}
                  fill="none"
                  stroke={cor["grafico.pace"]}
                  strokeWidth={2.5}
                  strokeDasharray={aprendendo ? "6 5" : undefined}
                />
              )}
          {!barras &&
            pos.map((p) => {
              const ponto = serie.pontos[p.indice];
              if (ponto.melhor)
                return (
                  <Polygon key={`m${p.indice}`} testID="marca-melhor" points={`${p.x},${p.y - 8} ${p.x + 8},${p.y} ${p.x},${p.y + 8} ${p.x - 8},${p.y}`} fill={cor["grafico.pace"]} />
                );
              if (ponto.fora_do_normal)
                return (
                  <Polygon key={`f${p.indice}`} testID="marca-fora" points={`${p.x},${p.y - 7} ${p.x + 7},${p.y + 6} ${p.x - 7},${p.y + 6}`} fill={cor.alerta} />
                );
              return <Circle key={`c${p.indice}`} cx={p.x} cy={p.y} r={tamanho.graficoPontoRaio} fill={cor.superficie} stroke={cor["grafico.pace"]} strokeWidth={2} />;
            })}
          {selecionado != null &&
            pos
              .filter((p) => p.indice === selecionado)
              .map((p) => (
                <G key="sel" testID="ponto-selecionado">
                  <Line x1={p.x} x2={p.x} y1={MARGEM.topo} y2={ALTURA - MARGEM.base} stroke={cor.texto} strokeWidth={1} strokeDasharray="3 3" />
                  {!barras && <Circle cx={p.x} cy={p.y} r={12} fill="none" stroke={cor.texto} strokeWidth={2} />}
                </G>
              ))}
          {datas.map((d) => {
            const p = pos.find((q) => q.indice === d.i);
            if (!p) return null;
            return (
              <SvgTexto key={`d${d.i}`} x={p.x} y={ALTURA - 8} fontSize={11.5} fontFamily={familia.medio} fill={cor["texto-2"]} textAnchor={d.ancora as "start" | "middle" | "end"}>
                {d.texto}
              </SvgTexto>
            );
          })}
        </Svg>
        {alvos.map((a) => (
          <Pressable
            key={a.indice}
            testID={`ponto-${a.indice}`}
            accessible={false}
            onPress={() => aoSelecionar(a.indice)}
            style={{ position: "absolute", left: a.esq, width: a.largura, top: Math.max(a.y - ALVO / 2, 0), height: ALVO }}
          />
        ))}
      </View>
      <View style={styles.legenda} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
        {legenda.map((l) => (
          <View key={l.chave} style={styles.legendaItem}>
            <Svg width={16} height={16}>
              {l.chave === "semana" && <Rect x={2} y={2} width={12} height={12} fill={cor["grafico.pace"]} />}
              {l.chave === "treino" && <Circle cx={8} cy={8} r={5} fill={cor.superficie} stroke={cor["grafico.pace"]} strokeWidth={2} />}
              {l.chave === "fora" && <Polygon points="8,2 15,14 1,14" fill={cor.alerta} />}
              {l.chave === "melhor" && <Polygon points="8,0 16,8 8,16 0,8" fill={cor["grafico.pace"]} />}
              {l.chave === "normal" && <Rect x={0} y={3} width={16} height={10} fill={cor["marca-suave"]} stroke={cor.borda} />}
            </Svg>
            <Text style={styles.legendaTexto}>{l.texto}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    dica: { ...fonte.eixo, color: cor["texto-2"], marginBottom: espaco[1] },
    legenda: { flexDirection: "row", flexWrap: "wrap", columnGap: espaco[3], rowGap: espaco[1], marginTop: espaco[2] },
    legendaItem: { flexDirection: "row", alignItems: "center", gap: espaco[1] },
    legendaTexto: { ...fonte.eixo, color: cor["texto-2"] },
  });
}
