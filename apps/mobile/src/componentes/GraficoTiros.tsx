import type { EvolucaoTiros1km, SessaoTiros } from "@treino/api-client";
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Circle, G, Line, Polyline } from "react-native-svg";

// Desenha os dois painéis (pace e FC). Faixa, marcas e rótulos vêm do bloco
// `eixos` da API: aqui só se converte valor em posição na tela. O app não
// formata pace nem escolhe escala (ADR 0004).

const LARGURA_PADRAO = 320;
const ALTURA_PAINEL = 160;
const MARGEM = { esq: 44, dir: 16, topo: 12, base: 12 };
const ALTURA_TITULO = 28;
const ALVO_TOQUE = 32;
const COR_PACE = "#1b6ca8";
const COR_FC = "#c0392b";

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

function Painel(props: {
  nome: string;
  titulo: string;
  cor: string;
  largura: number;
  eixo: Eixo;
  pontos: Ponto[];
  aoTocar: (s: SessaoTiros) => void;
  selecionada: number | null;
}) {
  const { nome, titulo, cor, largura, eixo, pontos, aoTocar, selecionada } = props;
  const linha = pontos.map((p) => `${p.x},${p.y}`).join(" ");
  return (
    <View testID={`painel-${nome}`} style={styles.painel}>
      <Text style={styles.tituloPainel}>{titulo}</Text>
      <Svg width={largura} height={ALTURA_PAINEL}>
        {eixo.marcas.map((m) => {
          const y = posicaoY(m.valor, eixo);
          return (
            <G key={`${m.valor}-${m.rotulo}`}>
              <Line x1={MARGEM.esq} x2={largura - MARGEM.dir} y1={y} y2={y} stroke="#ddd" strokeWidth={1} />
            </G>
          );
        })}
        {pontos.length > 1 && <Polyline points={linha} fill="none" stroke={cor} strokeWidth={1.5} />}
        {pontos.map((p) => (
          <Circle
            key={p.sessao.atividade_id}
            testID={`ponto-${nome}-${p.sessao.atividade_id}`}
            cx={p.x}
            cy={p.y}
            r={p.sessao.atividade_id === selecionada ? 7 : 5}
            fill={cor}
          />
        ))}
      </Svg>
      {/* O toque fica num Pressable por cima: onPress no Circle faz o react-native-svg
          repassar props de responder ao DOM na web ("Unknown event handler property"). */}
      {pontos.map((p) => (
        <Pressable
          key={`toque-${p.sessao.atividade_id}`}
          testID={`toque-${nome}-${p.sessao.atividade_id}`}
          accessibilityRole="button"
          accessibilityLabel={`Sessão de ${dataCurta(p.sessao.data)}`}
          onPress={() => aoTocar(p.sessao)}
          style={[
            styles.alvo,
            { left: p.x - ALVO_TOQUE / 2, top: ALTURA_TITULO + p.y - ALVO_TOQUE / 2 },
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
  const [largura, setLargura] = useState(LARGURA_PADRAO);
  const [selecionada, setSelecionada] = useState<SessaoTiros | null>(null);
  const { eixos, sessoes } = dados;

  if (!eixos || sessoes.length === 0) {
    return <Text>Sem sessões de tiros no período.</Text>;
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
    ? sessoes.map((s, i) => ({ sessao: s, x: xs[i], y: posicaoY(s.pace_medio_s_km, eixoPace) }))
    : [];
  const pontosFc: Ponto[] = eixoFc
    ? sessoes.flatMap((s, i) =>
        s.fc_media === null ? [] : [{ sessao: s, x: xs[i], y: posicaoY(s.fc_media, eixoFc) }],
      )
    : [];

  return (
    <View onLayout={(e) => setLargura(Math.max(e.nativeEvent.layout.width, 200))}>
      {eixoPace ? (
        <Painel
          nome="pace"
          titulo="Pace médio dos tiros (min/km)"
          cor={COR_PACE}
          largura={largura}
          eixo={eixoPace}
          pontos={pontosPace}
          aoTocar={setSelecionada}
          selecionada={selecionada?.atividade_id ?? null}
        />
      ) : (
        <Text>Sem pace para mostrar.</Text>
      )}
      {eixoFc ? (
        <Painel
          nome="fc"
          titulo="FC média dos tiros (bpm)"
          cor={COR_FC}
          largura={largura}
          eixo={eixoFc}
          pontos={pontosFc}
          aoTocar={setSelecionada}
          selecionada={selecionada?.atividade_id ?? null}
        />
      ) : (
        <View testID="aviso-sem-fc">
          <Text style={styles.tituloPainel}>FC média dos tiros (bpm)</Text>
          <Text style={styles.aviso}>Nenhuma sessão deste período tem frequência cardíaca.</Text>
        </View>
      )}
      <View style={{ height: 24 }}>
        {sessoes.map((s, i) => (
          <Text key={s.atividade_id} style={[styles.data, { left: xs[i] - 30 }]}>
            {dataCurta(s.data)}
          </Text>
        ))}
      </View>
      {selecionada && (
        <View testID="detalhe-sessao" style={styles.detalhe}>
          <Text style={styles.detalheTitulo}>{dataCurta(selecionada.data)}</Text>
          <Text>Pace médio: {selecionada.pace_medio} min/km</Text>
          <Text>FC média: {selecionada.fc_media === null ? "sem FC" : `${selecionada.fc_media} bpm`}</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  painel: { position: "relative" },
  alvo: { position: "absolute", width: ALVO_TOQUE, height: ALVO_TOQUE, borderRadius: ALVO_TOQUE / 2 },
  rotulo: { position: "absolute", left: 0, width: MARGEM.esq - 6, textAlign: "right", fontSize: 11, color: "#444" },
  data: { position: "absolute", top: 4, width: 60, textAlign: "center", fontSize: 11, color: "#444" },
  tituloPainel: { fontSize: 14, fontWeight: "600", height: ALTURA_TITULO, paddingTop: 8, color: "#111" },
  aviso: { fontSize: 14, color: "#666", paddingVertical: 12 },
  detalhe: { marginTop: 8, padding: 12, borderRadius: 8, backgroundColor: "#f3f3f3" },
  detalheTitulo: { fontWeight: "700" },
});
