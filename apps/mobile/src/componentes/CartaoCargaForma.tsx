import { MaterialIcons } from "@expo/vector-icons";
import type { Atividade, CargaAtividade } from "@treino/api-client";
import { useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";
import { dataCurta } from "./GraficoTiros";

type FormaDoDia = NonNullable<Atividade["forma_do_dia"]>;

// Definições fixas do glossário (spec #463): texto do app, sem adjetivo de valor.
const LINHAS = [
  { chave: "ctl", rotulo: "Condicionamento (CTL)", definicao: "Condicionamento: média da sua carga nos últimos 42 dias." },
  { chave: "atl", rotulo: "Fadiga (ATL)", definicao: "Fadiga: média da sua carga nos últimos 7 dias." },
  {
    chave: "tsb",
    rotulo: "Forma (TSB)",
    definicao: "Forma: condicionamento menos fadiga; negativa quer dizer que a carga recente está acima da média de 42 dias.",
  },
] as const;

type Props = { carga?: CargaAtividade | null; forma?: FormaDoDia | null };

/** Cartão "Carga e forma do dia" (#466, spec #463): só números e textos da API, como estimativa, sem gráfico. */
export function CartaoCargaForma({ carga, forma }: Props) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const [aberta, setAberta] = useState<string | null>(null);

  const cargaCalculada = carga?.estado === "calculada" && carga.valor_texto != null;
  const avisoCarga = carga && !cargaCalculada ? carga.texto : null;
  const formaCalculada = forma?.estado === "calculada";
  const formaAprendendo = forma?.estado === "aprendendo" && !!forma.texto_aprendendo;
  // Sem carga e sem forma a mostrar (campos ausentes, `sem_serie` sozinho): o cartão não aparece.
  if (!cargaCalculada && !avisoCarga && !formaCalculada && !formaAprendendo) return null;

  const nota = (icone: "info-outline" | "hourglass-empty", texto: string, id: string) => (
    <View key={id} testID={id} style={styles.aviso}>
      <MaterialIcons name={icone} size={tamanho.iconePequeno} color={tema.cor.texto} />
      <Text style={styles.avisoTexto}>{texto}</Text>
    </View>
  );

  return (
    <View testID="cartao-carga-forma" style={styles.cartao}>
      <Text accessibilityRole="header" style={styles.titulo}>
        Carga e forma do dia
      </Text>
      <View style={styles.chip}>
        <Text style={styles.chipTexto}>estimativa</Text>
      </View>

      {cargaCalculada && carga && (
        <View testID="carga-treino" accessible accessibilityLabel={`Carga deste treino, ${carga.valor_texto} pontos. ${carga.metodo_texto ?? ""}`}>
          <Text style={styles.rotulo}>Carga deste treino</Text>
          <Text style={styles.destaque}>
            {carga.valor_texto} <Text style={styles.unidade}>pontos</Text>
          </Text>
          {carga.metodo_texto ? <Text style={styles.secundario}>{carga.metodo_texto}</Text> : null}
        </View>
      )}
      {avisoCarga && nota("info-outline", avisoCarga, "aviso-carga")}

      {formaCalculada && forma && (
        <View style={styles.bloco}>
          <Text style={styles.rotulo}>No fim do dia {dataCurta(forma.data_local)}</Text>
          {LINHAS.map(({ chave, rotulo, definicao }) => {
            const valor = forma[`${chave}_texto` as "ctl_texto" | "atl_texto" | "tsb_texto"];
            if (valor == null) return null;
            const expandida = aberta === chave;
            return (
              <View key={chave}>
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={`${rotulo}, ${valor.replace("\u2212", "menos ")}`}
                  accessibilityHint="Mostra o que significa"
                  accessibilityState={{ expanded: expandida }}
                  onPress={() => setAberta(expandida ? null : chave)}
                  style={styles.linha}
                >
                  <Text style={styles.rotuloLinha}>{rotulo}</Text>
                  <Text style={styles.valorLinha}>{valor}</Text>
                  <MaterialIcons name={expandida ? "expand-less" : "expand-more"} size={tamanho.iconePequeno} color={tema.cor["texto-2"]} />
                </Pressable>
                {expandida && <Text style={styles.definicao}>{definicao}</Text>}
              </View>
            );
          })}
          {forma.sem_carga_no_dia > 0 && forma.texto_sem_carga ? nota("info-outline", forma.texto_sem_carga, "aviso-sem-carga-no-dia") : null}
        </View>
      )}
      {formaAprendendo && forma?.texto_aprendendo && (
        <View style={styles.bloco}>{nota("hourglass-empty", forma.texto_aprendendo, "aviso-aprendendo")}</View>
      )}

      <Text style={styles.legenda}>Estimativas a partir dos seus treinos. Não são medidas e não são diagnóstico.</Text>
    </View>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    cartao: { marginTop: espaco[4], padding: espaco[4], borderRadius: raio.grande, borderWidth: borda.fina, borderColor: cor.borda, backgroundColor: cor.superficie },
    titulo: { ...fonte["titulo-secao"], color: cor.texto },
    chip: { alignSelf: "flex-start", marginVertical: espaco[2], paddingHorizontal: espaco[3], borderRadius: raio.pilula, backgroundColor: cor["superficie-2"] },
    chipTexto: { ...fonte.rotulo, color: cor.texto },
    rotulo: { ...fonte.rotulo, color: cor["texto-2"] },
    destaque: { ...fonte["numero-destaque"], color: cor.texto },
    unidade: { ...fonte.rotulo, color: cor["texto-2"] },
    secundario: { ...fonte.corpo, color: cor["texto-2"] },
    bloco: { marginTop: espaco[3], paddingTop: espaco[3], borderTopWidth: borda.fina, borderTopColor: cor.borda },
    linha: { flexDirection: "row", alignItems: "center", gap: espaco[2], minHeight: tamanho.alvoMinimo },
    rotuloLinha: { ...fonte.corpo, color: cor["texto-2"], flex: 1 },
    valorLinha: { ...fonte["corpo-forte"], fontVariant: ["tabular-nums"], color: cor.texto },
    definicao: { ...fonte.legenda, color: cor["texto-2"], paddingBottom: espaco[2] },
    aviso: { flexDirection: "row", alignItems: "flex-start", gap: espaco[2], marginTop: espaco[2], padding: espaco[3], borderRadius: raio.medio, backgroundColor: cor["superficie-2"] },
    avisoTexto: { ...fonte.corpo, color: cor.texto, flex: 1 },
    legenda: { ...fonte.legenda, marginTop: espaco[3], color: cor["texto-2"] },
  });
}
