// Linha "Copiar" e 👍/👎 no fim do cartão de uma resposta `respondida` (adendo da spec do chat, #629). Copiar põe só o `texto` na área de
// transferência; a avaliação é otimista e volta ao estado anterior se a API falhar. Nada da pergunta nem da resposta vai à API junto.
import { MaterialIcons } from "@expo/vector-icons";
import { useEffect, useMemo, useRef, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { copiarTexto } from "../chat/copiar";
import { comFoco } from "../tema/foco";
import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";

type Valor = 1 | -1 | null;

type Props = {
  texto: string;
  avaliacaoInicial: Valor;
  /** Grava a avaliação na API; devolve se deu certo. */
  aoAvaliar: (valor: Valor) => Promise<boolean>;
};

export const TEXTO_COPIAR_ERRO = "Não deu para copiar.";
export const TEXTO_AVALIAR_ERRO = "Não deu para registrar. Tente de novo.";
const COPIADO_POR_MS = 2000;

export function AcoesResposta({ texto, avaliacaoInicial, aoAvaliar }: Props) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const [valor, setValor] = useState<Valor>(avaliacaoInicial);
  const [gravando, setGravando] = useState(false);
  const [copiado, setCopiado] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const relogio = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (relogio.current) clearTimeout(relogio.current); }, []);

  const copiar = async () => {
    const deu = await copiarTexto(texto);
    if (!deu) {
      setAviso(TEXTO_COPIAR_ERRO);
      return;
    }
    setAviso(null);
    setCopiado(true);
    if (relogio.current) clearTimeout(relogio.current);
    relogio.current = setTimeout(() => setCopiado(false), COPIADO_POR_MS);
  };

  const avaliar = async (escolhido: 1 | -1) => {
    if (gravando) return;
    const anterior = valor;
    const novo: Valor = anterior === escolhido ? null : escolhido; // tocar no marcado desmarca; tocar no outro troca
    setValor(novo);
    setAviso(null);
    setGravando(true);
    const deu = await aoAvaliar(novo);
    setGravando(false);
    if (!deu) {
      setValor(anterior);
      setAviso(TEXTO_AVALIAR_ERRO);
    }
  };

  const polegar = (v: 1 | -1, icone: "thumb-up" | "thumb-down", rotulo: string) => {
    const marcado = valor === v;
    return (
      <Pressable
        testID={v === 1 ? "chat-gostei" : "chat-nao-gostei"}
        accessibilityRole="togglebutton"
        accessibilityLabel={rotulo}
        accessibilityState={{ checked: marcado, selected: marcado }}
        onPress={() => void avaliar(v)}
        style={comFoco([styles.polegar, marcado && styles.polegarMarcado], styles.foco)}
      >
        <MaterialIcons name={icone} size={tamanho.iconeMedio} color={marcado ? tema.cor.link : tema.cor["texto-2"]} accessible={false} />
      </Pressable>
    );
  };

  return (
    <View testID="chat-acoes" accessibilityRole="toolbar" accessibilityLabel="Ações da resposta" style={styles.bloco}>
      <View style={styles.linha}>
        <Pressable testID="chat-copiar" accessibilityRole="button" accessibilityLabel="Copiar resposta" onPress={() => void copiar()} style={comFoco([styles.copiar, copiado && styles.copiado], styles.foco)}>
          <MaterialIcons name={copiado ? "check" : "content-copy"} size={tamanho.iconeMedio} color={tema.cor.link} accessible={false} />
          <Text style={styles.copiarTexto}>{copiado ? "Copiado" : "Copiar"}</Text>
        </Pressable>
        <View style={styles.polegares}>
          {polegar(1, "thumb-up", "Gostei da resposta")}
          {polegar(-1, "thumb-down", "Não gostei da resposta")}
        </View>
      </View>
      {copiado && (
        <Text accessibilityLiveRegion="polite" style={styles.apoioLeitor}>
          Resposta copiada
        </Text>
      )}
      {aviso && (
        <Text testID="chat-acoes-aviso" accessibilityRole="alert" style={styles.aviso}>
          {aviso}
        </Text>
      )}
    </View>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    bloco: { gap: espaco[1], paddingTop: espaco[2], borderTopWidth: borda.fina, borderTopColor: cor.borda },
    linha: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
    copiar: { minHeight: tamanho.alvoMinimo, minWidth: 120, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: espaco[2], paddingHorizontal: espaco[3], borderRadius: raio.botao },
    copiado: { backgroundColor: cor["marca-suave"] },
    copiarTexto: { ...fonte.botao, color: cor.link },
    polegares: { flexDirection: "row", gap: espaco[1] },
    polegar: { width: tamanho.alvoMinimo, height: tamanho.alvoMinimo, alignItems: "center", justifyContent: "center", borderRadius: raio.botao, borderWidth: borda.fina, borderColor: "transparent" },
    polegarMarcado: { borderWidth: borda.foco, borderColor: cor.link, backgroundColor: cor["marca-suave"] },
    apoioLeitor: { position: "absolute", width: 1, height: 1, opacity: 0 },
    aviso: { ...fonte.legenda, color: cor.erro },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}
