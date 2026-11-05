import type { EvolucaoTiros1km, SessaoTiros } from "@treino/api-client";
import { useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Circle, G, Line, Polyline } from "react-native-svg";

import { borda, espaco, familia, fonte, raio, tamanho, useTema, type Tema } from "../tema";

// Desenha os dois painéis (pace e FC). Faixa, marcas e rótulos vêm do bloco
// `eixos` da API: aqui só se converte valor em posição na tela. O app não
// formata pace nem escolhe escala (ADR 0004).

const LARGURA_PADRAO = 320;
const ALTURA_PAINEL = tamanho.graficoPainelAltura;
const MARGEM = { esq: 44, dir: 16, topo: 12, base: 12 };
const ALTURA_TITULO = 28;
const ALVO_TOQUE = tamanho.alvoMinimo;

type Eixo = {
  min: number;
  max: number;
  invertido: boolean;
  marcas: { valor: number; rotulo: string }[];
};

type Props = { dados: EvolucaoTiros1km };

// "2025-03-04" -> "04/03/25" (só recorte de texto da data local da API).
export function dataCurta(data: string): string {
  const [a, m, d] = data.split("-");
  return `${d}/${m}/${a.slice(2)}`;
}

export function posicaoY(v: number, eixo: Eixo): number {
  const area = ALTURA_PAINEL - MARGEM.topo - MARGEM.base;
  const frac = (v - eixo.min) / (eixo.max - eixo.min);
  // Normal: valor maior no alto. Invertido: valor menor (mais rápido) no alto.
  return MARGEM.topo + (eixo.invertido ? frac : 1 - frac) * area;
}

function posicoesX(sessoes: SessaoTiros[], largura: number): number[] {
  const ini = MARGEM.esq;
  const fim = largura - MARGEM.dir;
  const t = sessoes.map((s) => Date.parse(`${s.data}T00:00:00Z`));
  const t0 = Math.min(...t);
  const t1 = Math.max(...t);
  if (t1 === t0) return t.map(() => (ini + fim) / 2);
  return t.map((v) => ini + ((v - t0) / (t1 - t0)) * (fim - ini));
}

type Ponto = { sessao: SessaoTiros; x: number; y: number };

/**
 * Faixa horizontal do alvo de toque de cada ponto: 44 de largura, cortada no meio
 * do caminho até o vizinho para os alvos não se sobreporem. Nunca fica abaixo de
 * `ALVO_MIN_LARGURA` (24), centrada no ponto: se as datas são coladas ou iguais, os
 * alvos se sobrepõem e vale o da sessão mais recente (renderizado depois, por cima).
 * A altura segue sempre 44.
 */
const ALVO_MIN_LARGURA = 24;
export function faixasDeToque(xs: number[], alvo: number = ALVO_TOQUE): { esq: number; largura: number }[] {
  const ordem = xs.map((x, i) => ({ x, i })).sort((a, b) => a.x - b.x);
  const faixas = new Array<{ esq: number; largura: number }>(xs.length);
  ordem.forEach(({ x, i }, k) => {
    const ant = ordem[k - 1];
    const prox = ordem[k + 1];
    const esq = ant ? Math.max(x - alvo / 2, (ant.x + x) / 2) : x - alvo / 2;
    const dir = prox ? Math.min(x + alvo / 2, (x + prox.x) / 2) : x + alvo / 2;
    faixas[i] =
      dir - esq >= ALVO_MIN_LARGURA
        ? { esq, largura: dir - esq }
        : { esq: x - ALVO_MIN_LARGURA / 2, largura: ALVO_MIN_LARGURA };
  });
  return faixas;
}

function Painel(props: {
  nome: string;
  titulo: string;
  dica?: string;
  rotuloPonto: (s: SessaoTiros) => string;
  cor: string;
  largura: number;
  eixo: Eixo;
  pontos: Ponto[];
  aoTocar: (s: SessaoTiros) => void;
  selecionada: number | null;
  tema: Tema;
  styles: Estilos;
}) {
  const { nome, titulo, dica, rotuloPonto, cor, largura, eixo, pontos, aoTocar, selecionada, tema, styles } = props;
  const faixas = faixasDeToque(pontos.map((p) => p.x));
  const linha = pontos.map((p) => `${p.x},${p.y}`).join(" ");
  return (
    <View testID={`painel-${nome}`} style={styles.painel}>
      <View style={styles.cabecalhoPainel}>
        <Text style={styles.tituloPainel}>{titulo}</Text>
        {dica && <Text style={styles.dica}>{dica}</Text>}
      </View>
      <Svg width={largura} height={ALTURA_PAINEL}>
        {eixo.marcas.map((m) => {
          const y = posicaoY(m.valor, eixo);
          return (
            <G key={`${m.valor}-${m.rotulo}`}>
              <Line x1={MARGEM.esq} x2={largura - MARGEM.dir} y1={y} y2={y} stroke={tema.cor["grafico.grade"]} strokeWidth={borda.fina} />
            </G>
          );
        })}
        {pontos.length > 1 && <Polyline points={linha} fill="none" stroke={cor} strokeWidth={tamanho.graficoLinhaPrincipal} />}
        {pontos.map((p) => (
          <Circle
            key={p.sessao.atividade_id}
            testID={`ponto-${nome}-${p.sessao.atividade_id}`}
            cx={p.x}
            cy={p.y}
            r={p.sessao.atividade_id === selecionada ? tamanho.graficoPontoSelecionadoRaio : tamanho.graficoPontoRaio}
            fill={cor}
            {...(p.sessao.atividade_id === selecionada
              ? { stroke: tema.cor.texto, strokeWidth: borda.foco }
              : {})}
          />
        ))}
      </Svg>
      {/* O toque fica num Pressable por cima: onPress no Circle faz o react-native-svg
          repassar props de responder ao DOM na web ("Unknown event handler property"). */}
      {pontos.map((p, i) => (
        <Pressable
          key={`toque-${p.sessao.atividade_id}`}
          testID={`toque-${nome}-${p.sessao.atividade_id}`}
          accessibilityRole="button"
          accessibilityLabel={`Sessão de ${dataCurta(p.sessao.data)}, ${rotuloPonto(p.sessao)}`}
          onPress={() => aoTocar(p.sessao)}
          style={[
            styles.alvo,
            { left: faixas[i].esq, width: faixas[i].largura, zIndex: i, top: ALTURA_TITULO + p.y - ALVO_TOQUE / 2 },
          ]}
        />
      ))}
      {eixo.marcas.map((m) => (
        <Text
          key={`r-${m.valor}-${m.rotulo}`}
          style={[styles.rotulo, { top: ALTURA_TITULO + posicaoY(m.valor, eixo) - 8 }]}
        >
          {m.rotulo}
        </Text>
      ))}
    </View>
  );
}

export function GraficoTiros({ dados }: Props) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const [largura, setLargura] = useState(LARGURA_PADRAO);
  const [selecionada, setSelecionada] = useState<SessaoTiros | null>(null);
  const { eixos, sessoes } = dados;

  if (!eixos || sessoes.length === 0) {
    return <Text style={styles.texto}>Sem sessões de tiros no período.</Text>;
  }

  const xs = posicoesX(sessoes, largura);
  const eixoPace: Eixo | null = eixos.pace && {
    min: eixos.pace.min_s_km,
    max: eixos.pace.max_s_km,
    invertido: eixos.pace.invertido,
    marcas: eixos.pace.marcas.map((m) => ({ valor: m.valor_s_km, rotulo: m.rotulo })),
  };
  const eixoFc: Eixo | null = eixos.fc && {
    min: eixos.fc.min_bpm,
    max: eixos.fc.max_bpm,
    invertido: false,
    marcas: eixos.fc.marcas.map((m) => ({ valor: m.valor_bpm, rotulo: m.rotulo })),
  };

  const pontosPace: Ponto[] = eixoPace
    ? sessoes.map((s, i) => ({ sessao: s, x: xs[i], y: posicaoY(s.pace_melhor_s_km, eixoPace) }))
    : [];
  const pontosFc: Ponto[] = eixoFc
    ? sessoes.flatMap((s, i) =>
        s.fc_melhor_tiro === null ? [] : [{ sessao: s, x: xs[i], y: posicaoY(s.fc_melhor_tiro, eixoFc) }],
      )
    : [];

  return (
    <View onLayout={(e) => setLargura(Math.max(e.nativeEvent.layout.width, 200))}>
      {eixoPace ? (
        <Painel
          nome="pace"
          titulo="Melhor pace (min/km)"
          dica="mais rápido ↑"
          rotuloPonto={(s) => `melhor tiro ${s.pace_melhor} min/km`}
          cor={tema.cor["grafico.pace"]}
          largura={largura}
          eixo={eixoPace}
          pontos={pontosPace}
          aoTocar={setSelecionada}
          selecionada={selecionada?.atividade_id ?? null}
          tema={tema}
          styles={styles}
        />
      ) : (
        <Text style={styles.texto}>Sem pace para mostrar.</Text>
      )}
      {eixoFc ? (
        <Painel
          nome="fc"
          titulo="FC do melhor tiro (bpm)"
          rotuloPonto={(s) => `FC do melhor tiro ${s.fc_melhor_tiro} bpm`}
          cor={tema.cor["grafico.fc"]}
          largura={largura}
          eixo={eixoFc}
          pontos={pontosFc}
          aoTocar={setSelecionada}
          selecionada={selecionada?.atividade_id ?? null}
          tema={tema}
          styles={styles}
        />
      ) : (
        <View testID="aviso-sem-fc">
          <Text style={styles.tituloPainel}>FC do melhor tiro (bpm)</Text>
          <Text style={styles.aviso}>Nenhuma sessão deste período tem frequência cardíaca.</Text>
        </View>
      )}
      <View style={{ height: espaco[5] }}>
        {sessoes.map((s, i) => (
          <Text
            key={s.atividade_id}
            style={[styles.data, { left: xs[i] - 30 }, s.atividade_id === selecionada?.atividade_id && styles.dataSelecionada]}
          >
            {dataCurta(s.data)}
          </Text>
        ))}
      </View>
      {selecionada && (
        <View testID="detalhe-sessao" style={styles.detalhe}>
          <Text style={styles.detalheTitulo}>
            {dataCurta(selecionada.data)} · {selecionada.n_tiros} tiros
          </Text>
          <Text style={styles.texto}>Melhor tiro: {selecionada.pace_melhor} min/km</Text>
          <Text style={styles.texto}>
            FC do melhor tiro: {selecionada.fc_melhor_tiro === null ? "sem FC" : `${selecionada.fc_melhor_tiro} bpm`}
          </Text>
          <Text style={styles.texto}>Média dos tiros: {selecionada.pace_medio} min/km</Text>
          <Text style={styles.texto}>FC média: {selecionada.fc_media === null ? "sem FC" : `${selecionada.fc_media} bpm`}</Text>
        </View>
      )}
    </View>
  );
}

type Estilos = ReturnType<typeof criarEstilos>;

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    painel: { position: "relative" },
    alvo: { position: "absolute", height: ALVO_TOQUE },
    cabecalhoPainel: { flexDirection: "row", alignItems: "baseline", justifyContent: "space-between" },
    dica: { ...fonte.legenda, color: cor["texto-2"] },
    rotulo: { ...fonte.eixo, position: "absolute", left: 0, width: MARGEM.esq - 6, textAlign: "right", color: cor["texto-2"] },
    dataSelecionada: { fontFamily: familia.bold, color: cor.texto },
    data: { ...fonte.eixo, position: "absolute", top: espaco[1], width: 60, textAlign: "center", color: cor["texto-2"] },
    tituloPainel: { ...fonte.rotulo, height: ALTURA_TITULO, paddingTop: espaco[2], color: cor.texto },
    aviso: { ...fonte.rotulo, color: cor["texto-2"], paddingVertical: espaco[3] },
    texto: { ...fonte.corpo, color: cor.texto },
    detalhe: { marginTop: espaco[2], padding: espaco[3], borderRadius: raio.medio, backgroundColor: cor["superficie-2"] },
    detalheTitulo: { ...fonte["corpo-forte"], color: cor.texto },
  });
}
