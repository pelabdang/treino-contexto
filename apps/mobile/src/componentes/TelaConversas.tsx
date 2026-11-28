// Lista de conversas do chat e "Apagar" (spec docs/design/telas/chat.md). A data é só o texto de `atualizada_em`; nada é calculado.
import { MaterialIcons } from "@expo/vector-icons";
import type { OpcoesCliente } from "@treino/api-client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { apagarConversa, listarConversas, type ConversaResumo } from "../chat/api";
import { dataDaLista } from "../chat/hora";
import { RODAPE_LISTA, TEXTO_APAGADA, TEXTO_APAGAR, TEXTO_APAGAR_ERRO, TEXTO_LISTA_ERRO, TEXTO_LISTA_VAZIA, TITULO_APAGAR } from "../chat/textos";
import { comFoco } from "../tema/foco";
import { borda, espaco, fonte, larguraConteudoMax, raio, tamanho, useMargemTela, useTema, type Tema } from "../tema";

type Props = {
  apiUrl: string;
  atletaId: number;
  fetchFn?: typeof fetch;
  aoVoltar: () => void;
  aoAbrirConversa: (id: number) => void;
  aoNovaConversa: () => void;
  /** Muda quando a tela volta ao foco: a lista é buscada de novo. */
  atualizar?: number;
  agora?: () => Date;
};

type Lista = { tipo: "carregando" } | { tipo: "erro" } | { tipo: "ok"; conversas: ConversaResumo[] };

export function TelaConversas({ apiUrl, atletaId, fetchFn, aoVoltar, aoAbrirConversa, aoNovaConversa, atualizar = 0, agora = () => new Date() }: Props) {
  const tema = useTema();
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
  const opcoes: OpcoesCliente = useMemo(() => ({ baseUrl: apiUrl, fetch: fetchFn }), [apiUrl, fetchFn]);
  const [lista, setLista] = useState<Lista>({ tipo: "carregando" });
  const [tentativa, setTentativa] = useState(0);
  const [menu, setMenu] = useState<number | null>(null);
  const [apagando, setApagando] = useState<ConversaResumo | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  useEffect(() => {
    let vivo = true;
    listarConversas(atletaId, opcoes).then((r) => {
      if (!vivo) return;
      if (r.ok) setLista({ tipo: "ok", conversas: r.dados });
      else setLista((atual) => (atual.tipo === "ok" ? atual : { tipo: "erro" }));
    });
    return () => {
      vivo = false;
    };
  }, [atletaId, opcoes, tentativa, atualizar]);

  useEffect(() => {
    if (!aviso) return;
    const t = setTimeout(() => setAviso(null), 4000);
    return () => clearTimeout(t);
  }, [aviso]);

  const confirmarApagar = useCallback(async () => {
    const alvo = apagando;
    if (!alvo) return;
    setApagando(null);
    setMenu(null);
    const r = await apagarConversa(atletaId, alvo.id, opcoes);
    if (r.ok || r.erro.tipo === "nao_encontrada") {
      setLista((atual) => (atual.tipo === "ok" ? { tipo: "ok", conversas: atual.conversas.filter((c) => c.id !== alvo.id) } : atual));
      setAviso(TEXTO_APAGADA);
    } else setAviso(TEXTO_APAGAR_ERRO);
  }, [apagando, atletaId, opcoes]);

  return (
    <View style={styles.tela}>
      <View style={styles.cabecalho}>
        <Pressable testID="conversas-voltar" accessibilityRole="button" accessibilityLabel="Voltar" onPress={aoVoltar} style={comFoco(styles.alvo, styles.foco)}>
          <MaterialIcons name="chevron-left" size={tamanho.iconeGrande} color={tema.cor.link} accessible={false} />
        </Pressable>
        <Text accessibilityRole="header" style={styles.titulo}>
          Conversas
        </Text>
      </View>
      <ScrollView testID="tela-conversas" contentContainerStyle={styles.conteudo}>
        <Pressable testID="nova-conversa" accessibilityRole="button" onPress={aoNovaConversa} style={comFoco(styles.primario, styles.foco)}>
          <MaterialIcons name="add" size={tamanho.iconeMedio} color={tema.cor["sobre-botao"]} accessible={false} />
          <Text style={styles.primarioTexto}>Nova conversa</Text>
        </Pressable>
        {lista.tipo === "carregando" && <Text accessibilityLiveRegion="polite" style={styles.apoio}>Carregando as conversas…</Text>}
        {lista.tipo === "erro" && (
          <View testID="conversas-erro" style={styles.estado}>
            <Text accessibilityRole="alert" style={styles.textoErro}>{TEXTO_LISTA_ERRO}</Text>
            <Pressable testID="conversas-tentar" accessibilityRole="button" onPress={() => { setLista({ tipo: "carregando" }); setTentativa((n) => n + 1); }} style={comFoco(styles.alvoTexto, styles.foco)}>
              <Text style={styles.linkTexto}>Tentar de novo</Text>
            </Pressable>
          </View>
        )}
        {lista.tipo === "ok" && lista.conversas.length === 0 && <Text testID="conversas-vazia" style={styles.apoio}>{TEXTO_LISTA_VAZIA}</Text>}
        {lista.tipo === "ok" &&
          lista.conversas.map((c) => (
            <View key={c.id} style={styles.item}>
              <View style={styles.linha}>
                <Pressable testID={`conversa-${c.id}`} accessibilityRole="button" onPress={() => aoAbrirConversa(c.id)} style={comFoco(styles.abrir, styles.foco)}>
                  <Text numberOfLines={2} style={styles.tituloConversa}>{c.titulo}</Text>
                  <Text style={styles.data}>{dataDaLista(c.atualizada_em, agora())}</Text>
                </Pressable>
                <Pressable testID={`mais-${c.id}`} accessibilityRole="button" accessibilityLabel={`Mais opções da conversa ${c.titulo}`} accessibilityState={{ expanded: menu === c.id }} onPress={() => setMenu(menu === c.id ? null : c.id)} style={comFoco(styles.alvo, styles.foco)}>
                  <MaterialIcons name="more-horiz" size={tamanho.iconeGrande} color={tema.cor["texto-2"]} accessible={false} />
                </Pressable>
              </View>
              {menu === c.id && (
                <Pressable testID={`apagar-${c.id}`} accessibilityRole="button" onPress={() => setApagando(c)} style={comFoco(styles.menuApagar, styles.foco)}>
                  <MaterialIcons name="delete-outline" size={tamanho.iconeMedio} color={tema.cor.erro} accessible={false} />
                  <Text style={styles.apagarTexto}>Apagar conversa</Text>
                </Pressable>
              )}
            </View>
          ))}
        <Text style={styles.rodape}>{RODAPE_LISTA}</Text>
      </ScrollView>
      {aviso && (
        <View testID="conversas-aviso" accessibilityLiveRegion="polite" style={styles.aviso}>
          <Text style={styles.avisoTexto}>{aviso}</Text>
        </View>
      )}
      <Modal visible={apagando != null} transparent animationType="none" onRequestClose={() => setApagando(null)} accessibilityViewIsModal>
        <View style={styles.fundo}>
          <View role="dialog" aria-modal aria-label={TITULO_APAGAR} testID="dialogo-apagar" style={styles.caixa}>
            <Text accessibilityRole="header" style={styles.dialogoTitulo}>{TITULO_APAGAR}</Text>
            <Text style={styles.dialogoTexto}>{TEXTO_APAGAR}</Text>
            <View style={styles.botoes}>
              <Pressable testID="cancelar-apagar" accessibilityRole="button" onPress={() => setApagando(null)} style={comFoco([styles.botao, styles.primario2], styles.foco)}>
                <Text style={styles.primarioTexto}>Cancelar</Text>
              </Pressable>
              <Pressable testID="confirmar-apagar" accessibilityRole="button" onPress={() => void confirmarApagar()} style={comFoco([styles.botao, styles.perigo], styles.foco)}>
                <Text style={styles.perigoTexto}>Apagar</Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

function criarEstilos({ cor }: Tema, margem: number) {
  return StyleSheet.create({
    tela: { flex: 1, width: "100%", maxWidth: larguraConteudoMax + 2 * margem, alignSelf: "center" },
    cabecalho: { flexDirection: "row", alignItems: "center", minHeight: 56, paddingHorizontal: margem - espaco[2], gap: espaco[1] },
    alvo: { minHeight: tamanho.alvoMinimo, minWidth: tamanho.alvoMinimo, justifyContent: "center", alignItems: "center" },
    alvoTexto: { minHeight: tamanho.alvoMinimo, justifyContent: "center" },
    titulo: { ...fonte["titulo-secao"], color: cor.texto, flex: 1 },
    conteudo: { padding: margem, paddingTop: espaco[2], gap: espaco[3] },
    primario: { minHeight: tamanho.botaoAltura, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: espaco[2], borderRadius: raio.botao, backgroundColor: cor.botao },
    primario2: { backgroundColor: cor.botao },
    primarioTexto: { ...fonte.botao, color: cor["sobre-botao"] },
    apoio: { ...fonte.corpo, color: cor["texto-2"] },
    estado: { gap: espaco[2], alignItems: "flex-start" },
    textoErro: { ...fonte["corpo-forte"], color: cor.erro },
    linkTexto: { ...fonte.botao, color: cor.link },
    item: { borderRadius: raio.cartao, borderWidth: borda.fina, borderColor: cor.borda, backgroundColor: cor.superficie },
    linha: { flexDirection: "row", alignItems: "center" },
    abrir: { flex: 1, minHeight: tamanho.listaLinhaAltura, justifyContent: "center", gap: espaco[1], padding: espaco[3] },
    tituloConversa: { ...fonte["corpo-forte"], color: cor.texto },
    data: { ...fonte.legenda, color: cor["texto-2"] },
    menuApagar: { minHeight: tamanho.alvoMinimo, flexDirection: "row", alignItems: "center", gap: espaco[2], paddingHorizontal: espaco[3], borderTopWidth: borda.fina, borderTopColor: cor.borda },
    apagarTexto: { ...fonte.botao, color: cor.erro },
    rodape: { ...fonte.legenda, color: cor["texto-2"], paddingTop: espaco[2] },
    aviso: { position: "absolute", left: margem, right: margem, bottom: espaco[5], padding: espaco[3], borderRadius: raio.bloco, backgroundColor: cor.texto },
    avisoTexto: { ...fonte.rotulo, color: cor.fundo, textAlign: "center" },
    fundo: { flex: 1, backgroundColor: "rgba(0,0,0,0.5)", justifyContent: "center", alignItems: "center", padding: espaco[4] },
    caixa: { width: "100%", maxWidth: 400, padding: espaco[4], gap: espaco[3], backgroundColor: cor.superficie, borderWidth: borda.fina, borderColor: cor.borda, borderRadius: raio.cartao },
    dialogoTitulo: { ...fonte["titulo-secao"], color: cor.texto },
    dialogoTexto: { ...fonte.corpo, color: cor["texto-2"] },
    botoes: { flexDirection: "row", gap: espaco[3] },
    botao: { flex: 1, minHeight: tamanho.botaoAltura, alignItems: "center", justifyContent: "center", borderRadius: raio.botao },
    perigo: { backgroundColor: cor.erro },
    perigoTexto: { ...fonte.botao, color: cor["sobre-erro"] },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}
