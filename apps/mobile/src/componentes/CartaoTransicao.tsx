// Cartão "Treino de transição" (#467, spec #463): mostra o rótulo e deixa o atleta corrigir pelas rotas que já existem.
// A API decide se o cartão aparece (`editavel`); o app não olha modalidade nem subtipo.
import { MaterialIcons } from "@expo/vector-icons";
import type { TransicaoAtividade } from "@treino/api-client";
import { useMemo, useState } from "react";
import { AccessibilityInfo, Platform, Pressable, StyleSheet, Text, View } from "react-native";

import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";
import { corrigirTransicao, desfazerCorrecaoDeTransicao } from "../transicao/api";

type Props = {
  transicao: TransicaoAtividade | null | undefined;
  apiUrl: string;
  atletaId: number;
  atividadeId: number;
  fetchFn?: typeof fetch;
  /** Depois do `200`: a tela busca o treino de novo (o normal, a carga e o feedback podem mudar). */
  aoCorrigido: () => Promise<unknown>;
};

const ERRO_GENERICO = "Não foi possível salvar. Tente de novo.";

function textos(t: TransicaoAtividade) {
  if (t.valor) {
    return t.origem === "atleta"
      ? { frase: "Este treino faz parte de um treino de transição.", detalhe: "Você marcou assim." }
      : {
          frase: "Este treino faz parte de um treino de transição.",
          detalhe: "O app sugeriu isso porque outro treino começou logo depois.",
        };
  }
  return t.origem === "atleta"
    ? { frase: "Você marcou que este treino não é de transição.", detalhe: null }
    : { frase: "Este treino não está marcado como de transição.", detalhe: null };
}

export function CartaoTransicao({ transicao, apiUrl, atletaId, atividadeId, fetchFn, aoCorrigido }: Props) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const [salvando, setSalvando] = useState(false);
  const [qual, setQual] = useState<"principal" | "voltar" | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [anuncio, setAnuncio] = useState("");
  if (!transicao || transicao.editavel === false) return null;

  const { frase, detalhe } = textos(transicao);
  const atleta = transicao.origem === "atleta";
  // Botão principal: só quando o atleta ainda não disse o que o botão diz (`true` + `atleta` não tem principal).
  const principal = transicao.valor ? (atleta ? null : { rotulo: "Não é transição", alvo: false }) : { rotulo: "Marcar como transição", alvo: true };
  const podeVoltar = atleta;

  const anunciar = (texto: string) => {
    setAnuncio(texto);
    if (Platform.OS === "android") return;
    try {
      AccessibilityInfo.announceForAccessibility?.(texto);
    } catch {
      // sem leitor de tela
    }
  };

  const enviar = async (qualBotao: "principal" | "voltar", chamada: () => ReturnType<typeof corrigirTransicao>, aviso: string) => {
    setSalvando(true);
    setQual(qualBotao);
    setErro(null);
    const r = await chamada();
    if (!r.ok) {
      setSalvando(false);
      setErro(r.erro.tipo === "nao_encontrado" ? "Treino não encontrado." : ERRO_GENERICO);
      return;
    }
    await aoCorrigido();
    setSalvando(false);
    anunciar(aviso);
  };
  const opcoes = { baseUrl: apiUrl, fetch: fetchFn };

  return (
    <View testID="cartao-transicao" style={styles.cartao}>
      <Text accessibilityRole="header" style={styles.titulo}>
        Treino de transição
      </Text>
      <View accessible accessibilityLabel={detalhe ? `${frase} ${detalhe}` : frase} style={styles.linhaTexto}>
        {transicao.valor && <MaterialIcons name="swap-horiz" size={tamanho.iconeMedio} color={tema.cor.texto} />}
        <View style={{ flex: 1 }}>
          <Text style={styles.corpo}>{frase}</Text>
          {detalhe && <Text style={styles.secundario}>{detalhe}</Text>}
        </View>
      </View>

      {principal && (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={principal.alvo ? "Marcar este treino como treino de transição" : "Marcar este treino como não sendo de transição"}
          accessibilityState={{ disabled: salvando }}
          disabled={salvando}
          onPress={() =>
            enviar(
              "principal",
              () => corrigirTransicao(atletaId, atividadeId, principal.alvo, opcoes),
              principal.alvo ? "Marcado como treino de transição." : "Marcado como não sendo treino de transição.",
            )
          }
          style={[styles.botao, salvando && styles.desligado]}
        >
          <Text style={styles.botaoTexto}>{salvando && qual === "principal" ? "Salvando..." : principal.rotulo}</Text>
        </Pressable>
      )}
      {podeVoltar && (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Voltar à sugestão do app"
          accessibilityState={{ disabled: salvando }}
          disabled={salvando}
          onPress={() => enviar("voltar", () => desfazerCorrecaoDeTransicao(atletaId, atividadeId, opcoes), "Voltou à sugestão do app.")}
          style={[styles.botaoTextoLink, salvando && styles.desligado]}
        >
          <Text style={styles.link}>{salvando && qual === "voltar" ? "Salvando..." : "Voltar à sugestão do app"}</Text>
        </Pressable>
      )}

      {erro && (
        <View accessibilityRole="alert" style={styles.erro}>
          <MaterialIcons name="error-outline" size={tamanho.iconePequeno} color={tema.cor.erro} />
          <Text style={styles.erroTexto}>{erro}</Text>
        </View>
      )}
      <Text style={styles.legenda}>Isso muda com quais treinos este é comparado.</Text>
      <Text accessibilityLiveRegion="polite" style={styles.anuncio}>
        {anuncio}
      </Text>
    </View>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    cartao: { marginTop: espaco[4], padding: espaco[4], borderRadius: raio.grande, borderWidth: borda.fina, borderColor: cor.borda, backgroundColor: cor.superficie },
    titulo: { ...fonte["titulo-secao"], color: cor.texto, marginBottom: espaco[2] },
    linhaTexto: { flexDirection: "row", alignItems: "flex-start", gap: espaco[2] },
    corpo: { ...fonte.corpo, color: cor.texto },
    secundario: { ...fonte.corpo, color: cor["texto-2"] },
    botao: {
      marginTop: espaco[3],
      minHeight: tamanho.botaoAltura,
      alignItems: "center",
      justifyContent: "center",
      borderRadius: raio.medio,
      borderWidth: borda.fina,
      borderColor: cor["borda-forte"],
      backgroundColor: cor.superficie,
    },
    botaoTexto: { ...fonte.botao, color: cor.texto },
    botaoTextoLink: { marginTop: espaco[2], minHeight: tamanho.botaoAltura, justifyContent: "center", alignSelf: "flex-start" },
    link: { ...fonte.botao, color: cor.destaque },
    desligado: { opacity: 0.6 },
    erro: { flexDirection: "row", alignItems: "center", gap: espaco[2], marginTop: espaco[2] },
    erroTexto: { ...fonte.corpo, color: cor.erro, flex: 1 },
    legenda: { ...fonte.legenda, marginTop: espaco[2], color: cor["texto-2"] },
    anuncio: { height: 0, overflow: "hidden" },
  });
}
