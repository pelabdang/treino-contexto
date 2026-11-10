// Peças do check-in usadas na tela de check-in e nos cartões do treino: grade de PSE, lista de sensação, atalhos,
// diálogo e folha. Nada aqui guarda resposta fora da memória do componente que a recebe (ADR 0012, item 5).
import { MaterialIcons } from "@expo/vector-icons";
import { useEffect, useMemo, type ReactNode } from "react";
import { Modal, Platform, Pressable, StyleSheet, Text, useWindowDimensions, View } from "react-native";

import { ATALHOS, NIVEIS_PSE, ANCORAS_PSE, SENSACOES, pseFalada, type ChaveAtalho } from "../checkin/escala";
import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";

/** Grade com uma coluna só em tela estreita ou com fonte grande (spec: nada é cortado). */
function useUmaColuna(): boolean {
  const { width, fontScale } = useWindowDimensions();
  return width < 340 || fontScale > 1.3;
}

export function GradePse({
  valor,
  aoEscolher,
  desligado,
}: {
  valor: number | null;
  aoEscolher: (pse: number) => void;
  desligado?: boolean;
}) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const umaColuna = useUmaColuna();
  const botao = (n: number) => {
    const escolhido = valor === n;
    const ancora = ANCORAS_PSE[n];
    return (
      <Pressable
        key={n}
        testID={`pse-${n}`}
        accessibilityRole="radio"
        accessibilityLabel={pseFalada(n)}
        accessibilityState={{ checked: escolhido, disabled: !!desligado }}
        disabled={desligado}
        onPress={() => aoEscolher(n)}
        style={[styles.pse, umaColuna && { minHeight: tamanho.botaoAltura }, escolhido && styles.escolhido]}
      >
        <Text style={styles.pseNumero}>{n}</Text>
        {ancora ? <Text style={styles.pseAncora}>{ancora}</Text> : null}
        {escolhido && <MaterialIcons name="check" size={tamanho.iconeMedio} color={tema.cor.destaque} accessible={false} />}
      </Pressable>
    );
  };
  return (
    <View accessibilityRole="radiogroup" style={umaColuna ? styles.colunaUnica : styles.duasColunas}>
      {umaColuna ? (
        NIVEIS_PSE.map(botao)
      ) : (
        <>
          <View style={styles.coluna}>{NIVEIS_PSE.filter((n) => n <= 5).map(botao)}</View>
          <View style={styles.coluna}>{NIVEIS_PSE.filter((n) => n > 5).map(botao)}</View>
        </>
      )}
    </View>
  );
}

export function ListaSensacao({
  valor,
  aoEscolher,
  desligado,
}: {
  valor: number | null;
  aoEscolher: (sensacao: number) => void;
  desligado?: boolean;
}) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  return (
    <View accessibilityRole="radiogroup" style={styles.listaSensacao}>
      {SENSACOES.map((s) => {
        const escolhido = valor === s.valor;
        return (
          <Pressable
            key={s.valor}
            testID={`sensacao-${s.valor}`}
            accessibilityRole="radio"
            accessibilityLabel={`Sensação, ${s.texto.toLowerCase()}`}
            accessibilityState={{ checked: escolhido, disabled: !!desligado }}
            disabled={desligado}
            onPress={() => aoEscolher(s.valor)}
            style={[styles.sensacao, escolhido && styles.escolhido]}
          >
            <MaterialIcons name={s.icone} size={tamanho.iconeGrande} color={tema.cor["texto-2"]} accessible={false} />
            <Text style={styles.sensacaoTexto}>{s.texto}</Text>
            {escolhido && <MaterialIcons name="check" size={tamanho.iconeMedio} color={tema.cor.destaque} accessible={false} />}
          </Pressable>
        );
      })}
    </View>
  );
}

export function ChipsAtalhos({
  marcados,
  aoAlternar,
  desligado,
}: {
  marcados: ChaveAtalho[];
  aoAlternar: (chave: ChaveAtalho) => void;
  desligado?: boolean;
}) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  return (
    <View style={styles.atalhos}>
      {ATALHOS.map((a) => {
        const marcado = marcados.includes(a.chave);
        return (
          <Pressable
            key={a.chave}
            testID={`atalho-${a.chave}`}
            accessibilityRole="checkbox"
            accessibilityLabel={a.texto}
            accessibilityState={{ checked: marcado, disabled: !!desligado }}
            disabled={desligado}
            onPress={() => aoAlternar(a.chave)}
            style={[styles.chipAtalho, marcado && styles.escolhido]}
          >
            {marcado && <MaterialIcons name="check" size={tamanho.iconePequeno} color={tema.cor.destaque} accessible={false} />}
            <Text style={styles.chipAtalhoTexto}>{a.texto}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export type AcaoDialogo = { rotulo: string; aoPress: () => void; perigo?: boolean };

/** Diálogo de confirmação: ação primária (a segura) em cima e a secundária embaixo. Esc e voltar fecham. */
export function Dialogo({
  visivel,
  titulo,
  texto,
  primaria,
  secundaria,
  aoFechar,
}: {
  visivel: boolean;
  titulo: string;
  texto: string;
  primaria: AcaoDialogo;
  secundaria: AcaoDialogo;
  aoFechar: () => void;
}) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  useEsc(visivel, aoFechar);
  return (
    <Modal visible={visivel} transparent animationType="fade" onRequestClose={aoFechar}>
      <View style={styles.fundoModal}>
        <View accessibilityViewIsModal style={styles.dialogo}>
          <Text accessibilityRole="header" style={styles.dialogoTitulo}>
            {titulo}
          </Text>
          <Text style={styles.dialogoTexto}>{texto}</Text>
          <Pressable accessibilityRole="button" onPress={primaria.aoPress} style={styles.botaoPrimario}>
            <Text style={styles.botaoPrimarioTexto}>{primaria.rotulo}</Text>
          </Pressable>
          <Pressable accessibilityRole="button" onPress={secundaria.aoPress} style={styles.botaoSecundario}>
            <Text style={[styles.botaoSecundarioTexto, secundaria.perigo && { color: tema.cor.erro }]}>{secundaria.rotulo}</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

/** Folha que sobe do pé (usada pelo "Mudar" da edição). */
export function Folha({
  visivel,
  titulo,
  fechar,
  children,
}: {
  visivel: boolean;
  titulo: string;
  fechar: () => void;
  children: ReactNode;
}) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  useEsc(visivel, fechar);
  return (
    <Modal visible={visivel} transparent animationType="slide" onRequestClose={fechar}>
      <Pressable accessibilityLabel="Fechar" style={styles.fundoModal} onPress={fechar}>
        <Pressable accessibilityViewIsModal style={styles.folha} onPress={() => {}}>
          <View style={styles.folhaTopo}>
            <Text accessibilityRole="header" style={styles.dialogoTitulo}>
              {titulo}
            </Text>
            <Pressable accessibilityRole="button" accessibilityLabel="Fechar" onPress={fechar} style={styles.fechar}>
              <MaterialIcons name="close" size={tamanho.iconeGrande} color={tema.cor["texto-2"]} accessible={false} />
            </Pressable>
          </View>
          {children}
        </Pressable>
      </Pressable>
    </Modal>
  );
}

function useEsc(ativo: boolean, fechar: () => void) {
  useEffect(() => {
    if (!ativo || Platform.OS !== "web" || typeof document === "undefined") return;
    const tecla = (e: KeyboardEvent) => {
      if (e.key === "Escape") fechar();
    };
    document.addEventListener("keydown", tecla);
    return () => document.removeEventListener("keydown", tecla);
  }, [ativo, fechar]);
}

function criarEstilos({ cor }: Tema) {
  const escolhido = { backgroundColor: cor["destaque-suave"], borderColor: cor.destaque, borderWidth: 2 };
  const botao = { minHeight: tamanho.botaoAltura, justifyContent: "center", alignItems: "center", borderRadius: raio.medio } as const;
  return StyleSheet.create({
    escolhido,
    duasColunas: { flexDirection: "row", gap: espaco[2], marginTop: espaco[3] },
    colunaUnica: { gap: espaco[2], marginTop: espaco[3] },
    coluna: { flex: 1, gap: espaco[2] },
    pse: {
      minHeight: 52,
      flexDirection: "row",
      alignItems: "center",
      gap: espaco[2],
      paddingHorizontal: espaco[3],
      paddingVertical: espaco[1],
      borderRadius: raio.medio,
      borderWidth: borda.fina,
      borderColor: cor["borda-forte"],
      backgroundColor: cor.superficie,
    },
    pseNumero: { ...fonte["titulo-secao"], color: cor.texto },
    pseAncora: { ...fonte.rotulo, color: cor.texto, flexShrink: 1 },
    listaSensacao: { gap: espaco[2], marginTop: espaco[3] },
    sensacao: {
      minHeight: tamanho.listaLinhaAltura,
      flexDirection: "row",
      alignItems: "center",
      gap: espaco[3],
      paddingHorizontal: espaco[3],
      borderRadius: raio.medio,
      borderWidth: borda.fina,
      borderColor: cor["borda-forte"],
      backgroundColor: cor.superficie,
    },
    sensacaoTexto: { ...fonte.corpo, color: cor.texto, flex: 1 },
    atalhos: { flexDirection: "row", flexWrap: "wrap", gap: espaco[2], marginTop: espaco[3] },
    chipAtalho: {
      minHeight: tamanho.botaoAltura,
      flexDirection: "row",
      alignItems: "center",
      gap: espaco[1],
      paddingHorizontal: espaco[4],
      borderRadius: raio.pilula,
      borderWidth: borda.fina,
      borderColor: cor["borda-forte"],
      backgroundColor: cor.superficie,
    },
    chipAtalhoTexto: { ...fonte.corpo, color: cor.texto },
    fundoModal: { flex: 1, justifyContent: "flex-end", backgroundColor: "rgba(0,0,0,0.4)" },
    dialogo: {
      margin: espaco[4],
      padding: espaco[4],
      gap: espaco[3],
      borderRadius: raio.grande,
      backgroundColor: cor.superficie,
    },
    dialogoTitulo: { ...fonte["titulo-secao"], color: cor.texto, flex: 1 },
    dialogoTexto: { ...fonte.corpo, color: cor.texto },
    folha: {
      padding: espaco[4],
      borderTopLeftRadius: raio.grande,
      borderTopRightRadius: raio.grande,
      backgroundColor: cor.superficie,
      maxHeight: "90%",
    },
    folhaTopo: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
    fechar: { width: tamanho.alvoMinimo, height: tamanho.alvoMinimo, alignItems: "center", justifyContent: "center" },
    botaoPrimario: { ...botao, backgroundColor: cor.destaque },
    botaoPrimarioTexto: { ...fonte.botao, color: cor["sobre-destaque"] },
    botaoSecundario: { ...botao, borderWidth: borda.fina, borderColor: cor["borda-forte"], backgroundColor: cor.superficie },
    botaoSecundarioTexto: { ...fonte.botao, color: cor.texto },
  });
}
