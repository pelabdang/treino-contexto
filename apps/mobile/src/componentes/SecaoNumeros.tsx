import type { CartaoInicio } from "@treino/api-client";
import { MaterialIcons } from "@expo/vector-icons";
import { useMemo, type ReactNode } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { comFoco } from "../tema/foco";
import { borda, espaco, familia, fonte, raio, tamanho, useTema, type Tema } from "../tema";

// Início v4, seção "Seus números" (spec inicio-v4). A API manda só os cartões que têm dado, na ordem fixa, com texto pronto:
// o app não soma, compara nem arredonda. Pequenos ficam em pares (um sozinho ocupa a linha); largos ocupam a linha toda.

export type DestinoCartao = CartaoInicio["destino"];

type Props = {
  cartoes: CartaoInicio[];
  aoAbrir: (destino: DestinoCartao) => void;
};

/** Os cartões em linhas: pares de pequenos e um largo por linha, sem mudar a ordem da API. */
export function linhasDeCartoes(cartoes: CartaoInicio[]): CartaoInicio[][] {
  const linhas: CartaoInicio[][] = [];
  let par: CartaoInicio[] = [];
  const soltar = () => {
    if (par.length) linhas.push(par);
    par = [];
  };
  for (const c of cartoes) {
    if (c.formato === "largo") {
      soltar();
      linhas.push([c]);
    } else {
      par.push(c);
      if (par.length === 2) soltar();
    }
  }
  soltar();
  return linhas;
}

export function SecaoNumeros({ cartoes, aoAbrir }: Props) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  if (cartoes.length === 0) return null;
  return (
    <View testID="secao-numeros" style={styles.secao}>
      <Text accessibilityRole="header" style={styles.titulo}>
        Seus números
      </Text>
      {linhasDeCartoes(cartoes).map((linha) => (
        <View key={linha.map((c) => c.id).join("+")} testID="linha-cartoes" style={styles.linha}>
          {linha.map((c) => (
            <Cartao key={c.id} cartao={c} aoAbrir={aoAbrir} styles={styles} tema={tema} sozinho={linha.length === 1} />
          ))}
        </View>
      ))}
    </View>
  );
}

function Cartao({ cartao, aoAbrir, styles, tema, sozinho }: { cartao: CartaoInicio; aoAbrir: (d: DestinoCartao) => void; styles: Estilos; tema: Tema; sozinho: boolean }): ReactNode {
  const largo = cartao.formato === "largo";
  const temBarras = largo && cartao.barras.length > 0;
  return (
    <Pressable
      testID={`cartao-${cartao.id}`}
      accessibilityRole="button"
      accessibilityLabel={cartao.rotulo_acessivel}
      onPress={() => aoAbrir(cartao.destino)}
      style={comFoco([styles.cartao, largo || sozinho ? styles.cartaoLargura : styles.cartaoMeio, !largo && styles.cartaoAltura], styles.foco)}
    >
      <View style={styles.topo}>
        <Text style={styles.rotulo}>{cartao.rotulo}</Text>
        <MaterialIcons name="chevron-right" size={tamanho.iconeMedio} color={tema.cor["texto-2"]} accessible={false} />
      </View>
      {largo && !temBarras ? (
        <Text style={styles.valorLargo}>{cartao.valor}</Text>
      ) : (
        <Text numberOfLines={1} adjustsFontSizeToFit style={[styles.valor, cartao.valor.length > 8 && styles.valorLongo]}>
          {cartao.valor}
        </Text>
      )}
      {temBarras && (
        <View testID={`barras-${cartao.id}`} accessibilityRole="list" style={styles.barras}>
          {cartao.barras.map((b, i) => (
            <View key={`${b.data_texto}-${i}`} style={styles.barraColuna}>
              <Text style={styles.barraValor}>{b.valor_texto}</Text>
              <View style={[styles.barra, b.destaque ? styles.barraDestaque : styles.barraComum]} />
              <Text style={styles.barraData}>{b.data_texto}</Text>
            </View>
          ))}
        </View>
      )}
      {cartao.apoio ? <Text style={styles.apoio}>{cartao.apoio}</Text> : null}
      {largo && cartao.texto ? <Text style={styles.texto}>{cartao.texto}</Text> : null}
    </Pressable>
  );
}

type Estilos = ReturnType<typeof criarEstilos>;

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    secao: { gap: espaco[3] },
    titulo: { ...fonte["titulo-secao"], color: cor.texto },
    linha: { flexDirection: "row", gap: espaco[3] },
    cartao: { minHeight: tamanho.alvoMinimo, padding: 14, borderRadius: raio.cartao, borderWidth: borda.fina, borderColor: cor.borda, backgroundColor: cor.superficie, gap: espaco[1] },
    cartaoMeio: { flex: 1, minWidth: 0 },
    cartaoLargura: { flexGrow: 1, flexBasis: "100%" },
    cartaoAltura: { minHeight: 112 },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
    topo: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: espaco[1] },
    rotulo: { ...fonte.sobretitulo, color: cor["texto-2"], textTransform: "uppercase", flex: 1 },
    valor: { ...fonte["numero-destaque"], fontFamily: familia.numero, fontSize: 32, lineHeight: 36, color: cor.texto },
    valorLongo: { fontSize: 27, lineHeight: 32 },
    valorLargo: { ...fonte["titulo-cartao"], color: cor.texto },
    apoio: { ...fonte.rotulo, color: cor["texto-2"] },
    texto: { ...fonte.corpo, color: cor.texto },
    barras: { flexDirection: "row", alignItems: "flex-end", gap: espaco[3], paddingTop: espaco[1] },
    barraColuna: { flex: 1, alignItems: "center", gap: 2 },
    barraValor: { ...fonte.eixo, color: cor.texto },
    barra: { width: "100%", height: 32, borderRadius: raio.pequeno },
    barraDestaque: { backgroundColor: cor["grafico.pace"] },
    barraComum: { backgroundColor: cor["superficie-2"] },
    barraData: { ...fonte.eixo, color: cor["texto-2"] },
  });
}
