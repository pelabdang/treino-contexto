// Tela do chat "Pergunte ao seu treino" (spec docs/design/telas/chat.md, #600): histórico, perguntas prontas, compositor e os estados da API.
// O app não calcula: o texto de cada resposta, recusa e erro vem pronto da API (ou é fixo daqui); o `motivo` nunca aparece.
import { MaterialIcons } from "@expo/vector-icons";
import type { OpcoesCliente } from "@treino/api-client";
import { type ComponentRef, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View, useWindowDimensions } from "react-native";

import {
  buscarConversa,
  criarConversa,
  enviarMensagem,
  type LimiteChat,
  type LinkChat,
  type MensagemChat,
  type ResultadoChat,
} from "../chat/api";
import { horaCurta, rotuloDoDia } from "../chat/hora";
import {
  AVISO_IA,
  CONTADOR_A_PARTIR_DE,
  FRASE_COMECO,
  MAXIMO_PERGUNTA,
  PERGUNTAS_PRONTAS,
  PLACEHOLDER,
  PLACEHOLDER_ESPERA,
  ROTULO_IA,
  SEM_TREINOS,
  TEXTO_ERRO_FIXO,
  TEXTO_NAO_ENCONTRADA,
  TEXTO_SEM_REDE,
  TITULO_CHAT,
  TITULO_COMECO,
  TITULO_LIMITE,
} from "../chat/textos";
import { comFoco } from "../tema/foco";
import { buscarTreinos } from "../treinos/api";
import { EsperaChat } from "./EsperaChat";
import { Faixa } from "./Faixa";
import { borda, espaco, fonte, larguraConteudoMax, raio, tamanho, useMargemTela, useTema, type Tema } from "../tema";

type Props = {
  apiUrl: string;
  atletaId: number;
  fetchFn?: typeof fetch;
  /** Conversa existente (`/chat/<id>`); sem ela, a conversa é nova. */
  conversaId?: number;
  /** Pergunta pronta tocada no Início: já é enviada ao abrir. */
  perguntaInicial?: string;
  aoVoltar: () => void;
  aoAbrirConversas: () => void;
  aoAbrirTreino: (atividadeId: number) => void;
  aoAbrirEvolucao: (serieId: string) => void;
  agora?: () => Date;
};

/** `msg` nulo = a pergunta está sendo respondida. `local`: o erro nasceu aqui (a API não guardou a pergunta). */
type Item = { chave: string; pergunta: string; msg: MensagemChat | null; local?: boolean };
type Carga = "carregando" | "ok" | "erro" | "nao_encontrada";
type Aviso = { tipo: "limite"; limite: LimiteChat } | { tipo: "rede" } | null;

const ESPERA_PADRAO_MS = 60_000;

function erroLocal(chave: string, pergunta: string): Item {
  const msg: MensagemChat = { id: 0, ordem: 0, pergunta, estado: "erro", motivo: null, texto: TEXTO_ERRO_FIXO, links: [], criada_em: "" };
  return { chave, pergunta, msg, local: true };
}

export function TelaChat({ apiUrl, atletaId, fetchFn, conversaId, perguntaInicial, aoVoltar, aoAbrirConversas, aoAbrirTreino, aoAbrirEvolucao, agora = () => new Date() }: Props) {
  const tema = useTema();
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
  const opcoes: OpcoesCliente = useMemo(() => ({ baseUrl: apiUrl, fetch: fetchFn }), [apiUrl, fetchFn]);
  const [itens, setItens] = useState<Item[]>([]);
  const [carga, setCarga] = useState<Carga>(conversaId != null ? "carregando" : "ok");
  const [tentativa, setTentativa] = useState(0);
  const [texto, setTexto] = useState("");
  const [aviso, setAviso] = useState<Aviso>(null);
  const [semTreinos, setSemTreinos] = useState(false);
  const idAtual = useRef<number | null>(conversaId ?? null);
  const emCurso = useRef(false);
  const sequencia = useRef(0);
  const rolagem = useRef<ComponentRef<typeof ScrollView>>(null);
  const campo = useRef<ComponentRef<typeof TextInput>>(null);
  const altura = useWindowDimensions().height;

  // Conversa existente: busca as mensagens.
  useEffect(() => {
    if (conversaId == null) return;
    let vivo = true;
    buscarConversa(atletaId, conversaId, opcoes).then((r) => {
      if (!vivo) return;
      if (r.ok) {
        setItens((atual) => [...r.dados.mensagens.map((m) => ({ chave: `s${m.id}`, pergunta: m.pergunta, msg: m })), ...atual.filter((i) => i.msg === null)]);
        setCarga("ok");
      } else setCarga(r.erro.tipo === "nao_encontrada" ? "nao_encontrada" : "erro");
    });
    return () => {
      vivo = false;
    };
  }, [atletaId, conversaId, opcoes, tentativa]);

  // Conversa nova: só para escolher entre as perguntas prontas e o aviso de "sem treinos".
  useEffect(() => {
    if (conversaId != null) return;
    let vivo = true;
    buscarTreinos(atletaId, { limite: 1 }, opcoes).then((r) => {
      if (vivo && r.ok) setSemTreinos((r.dados.itens ?? []).length === 0);
    });
    return () => {
      vivo = false;
    };
  }, [atletaId, conversaId, opcoes]);

  // O limite acaba sozinho: a contagem interna em `espere_s` só reabre o campo (nenhum número aparece).
  useEffect(() => {
    if (aviso?.tipo !== "limite") return;
    const ms = aviso.limite.espere_s > 0 ? aviso.limite.espere_s * 1000 : ESPERA_PADRAO_MS;
    const t = setTimeout(() => setAviso(null), ms);
    return () => clearTimeout(t);
  }, [aviso]);

  const enviar = useCallback(
    async (pergunta: string, trocar?: string) => {
      const p = pergunta.trim();
      if (!p || emCurso.current) return;
      emCurso.current = true;
      setAviso(null);
      const chave = `n${++sequencia.current}`;
      setItens((atual) => [...atual.filter((i) => i.chave !== trocar), { chave, pergunta: p, msg: null }]);
      setTexto("");
      const trocarPor = (msg: MensagemChat | null) => setItens((atual) => atual.map((i) => (i.chave === chave ? { ...i, msg } : i)));
      const falhou = (r: Extract<ResultadoChat<unknown>, { ok: false }>) => {
        if (r.erro.tipo === "limite" || r.erro.tipo === "rede") {
          // A pergunta não foi guardada: sai do histórico e volta para o campo.
          setItens((atual) => atual.filter((i) => i.chave !== chave));
          setTexto(p);
          setAviso(r.erro.tipo === "limite" ? { tipo: "limite", limite: r.erro.limite } : { tipo: "rede" });
        } else if (r.erro.tipo === "nao_encontrada" && idAtual.current != null) {
          setItens((atual) => atual.filter((i) => i.chave !== chave));
          setCarga("nao_encontrada");
        } else setItens((atual) => atual.map((i) => (i.chave === chave ? erroLocal(chave, p) : i)));
      };
      if (idAtual.current == null) {
        const r = await criarConversa(atletaId, p, opcoes);
        if (r.ok) {
          idAtual.current = r.dados.id;
          trocarPor(r.dados.mensagens[r.dados.mensagens.length - 1] ?? null);
        } else falhou(r);
      } else {
        const r = await enviarMensagem(atletaId, idAtual.current, p, opcoes);
        if (r.ok) trocarPor(r.dados);
        else falhou(r);
      }
      emCurso.current = false;
      campo.current?.focus();
    },
    [atletaId, opcoes],
  );

  const primeiraVez = useRef(true);
  useEffect(() => {
    if (!primeiraVez.current) return;
    primeiraVez.current = false;
    if (perguntaInicial && conversaId == null) void enviar(perguntaInicial);
  }, [perguntaInicial, conversaId, enviar]);

  const pensando = itens.some((i) => i.msg === null);
  const limite = aviso?.tipo === "limite";
  const podeEnviar = texto.trim().length > 0 && !pensando && !limite;
  const comeco = carga === "ok" && itens.length === 0;

  const aoTeclar = (e: { nativeEvent: { key: string; shiftKey?: boolean }; preventDefault?: () => void }) => {
    if (Platform.OS === "web" && e.nativeEvent.key === "Enter" && !e.nativeEvent.shiftKey) {
      e.preventDefault?.();
      if (podeEnviar) void enviar(texto);
    }
  };

  const rotulos = itens.map((i) => (i.msg?.criada_em ? rotuloDoDia(i.msg.criada_em, agora()) : ""));
  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={[styles.tela, { maxHeight: altura }]}>
      <View style={styles.cabecalho}>
        <Pressable testID="chat-voltar" accessibilityRole="button" accessibilityLabel="Voltar" onPress={aoVoltar} style={comFoco(styles.alvo, styles.foco)}>
          <MaterialIcons name="chevron-left" size={tamanho.iconeGrande} color={tema.cor.link} accessible={false} />
        </Pressable>
        <Text accessibilityRole="header" numberOfLines={1} style={styles.titulo}>
          {TITULO_CHAT}
        </Text>
        <Pressable testID="chat-conversas" accessibilityRole="button" onPress={aoAbrirConversas} style={comFoco([styles.alvo, styles.alvoTexto], styles.foco)}>
          <Text style={styles.linkTexto}>Conversas ›</Text>
        </Pressable>
      </View>

      <ScrollView
        ref={rolagem}
        testID="chat-historico"
        style={styles.historico}
        contentContainerStyle={styles.conteudo}
        keyboardShouldPersistTaps="handled"
        onContentSizeChange={() => rolagem.current?.scrollToEnd({ animated: false })}
      >
        {carga === "carregando" && <Text accessibilityLiveRegion="polite" style={styles.apoio}>Carregando a conversa…</Text>}
        {carga === "erro" && (
          <View testID="chat-erro-carga" style={styles.estado}>
            <MaterialIcons name="error-outline" size={tamanho.iconeEstado} color={tema.cor.erro} accessible={false} />
            <Text accessibilityRole="alert" style={styles.textoErro}>Não deu para carregar a conversa.</Text>
            <Pressable testID="chat-tentar-carga" accessibilityRole="button" onPress={() => { setCarga("carregando"); setTentativa((n) => n + 1); }} style={comFoco([styles.alvo, styles.alvoTexto], styles.foco)}>
              <Text style={styles.linkTexto}>Tentar de novo</Text>
            </Pressable>
          </View>
        )}
        {carga === "nao_encontrada" && (
          <View testID="chat-nao-encontrada" style={styles.estado}>
            <MaterialIcons name="error-outline" size={tamanho.iconeEstado} color={tema.cor.erro} accessible={false} />
            <Text accessibilityRole="alert" style={styles.textoErro}>{TEXTO_NAO_ENCONTRADA}</Text>
            <Pressable testID="chat-voltar-conversas" accessibilityRole="button" onPress={aoAbrirConversas} style={comFoco([styles.alvo, styles.alvoTexto], styles.foco)}>
              <Text style={styles.linkTexto}>Voltar às conversas</Text>
            </Pressable>
          </View>
        )}

        {comeco && (
          <View testID="chat-comeco" style={styles.comeco}>
            <Text accessibilityRole="header" style={styles.tituloComeco}>{TITULO_COMECO}</Text>
            {semTreinos ? (
              <Text testID="chat-sem-treinos" style={styles.apoio}>{SEM_TREINOS}</Text>
            ) : (
              <>
                <Text style={styles.apoio}>{FRASE_COMECO}</Text>
                {PERGUNTAS_PRONTAS.map((q, i) => (
                  <Pressable key={q} testID={`pergunta-pronta-${i}`} accessibilityRole="button" onPress={() => void enviar(q)} style={comFoco(styles.pronta, styles.foco)}>
                    <Text style={styles.prontaTexto}>{q}</Text>
                    <MaterialIcons name="chevron-right" size={tamanho.iconeGrande} color={tema.cor["texto-2"]} accessible={false} />
                  </Pressable>
                ))}
              </>
            )}
          </View>
        )}

        {itens.map((item, n) => {
          const quando = item.msg?.criada_em ?? "";
          const anterior = rotulos.slice(0, n).reverse().find(Boolean) ?? "";
          const marcador = rotulos[n] && rotulos[n] !== anterior ? rotulos[n] : "";
          return (
            <View key={item.chave} style={styles.troca}>
              {marcador !== "" && <Text style={styles.dia}>{marcador}</Text>}
              <View accessible accessibilityLabel={`Você${quando ? `, ${horaCurta(quando)}` : ""}: ${item.pergunta}`} style={styles.pergunta}>
                <Text style={styles.perguntaTexto}>{item.pergunta}</Text>
                <Text style={styles.hora}>{quando ? `Você · ${horaCurta(quando)}` : "Você"}</Text>
              </View>
              {item.msg === null ? (
                <EsperaChat />
              ) : (
                <CartaoResposta msg={item.msg} aoTentar={() => void enviar(item.pergunta, item.local ? item.chave : undefined)} aoAbrirTreino={aoAbrirTreino} aoAbrirEvolucao={aoAbrirEvolucao} desligado={pensando || limite} styles={styles} tema={tema} />
              )}
            </View>
          );
        })}
      </ScrollView>

      <View style={styles.compositor}>
        {aviso?.tipo === "limite" && (
          <View testID="chat-limite" accessibilityRole="alert" style={styles.limite}>
            <Text style={styles.limiteTitulo}>{TITULO_LIMITE}</Text>
            {aviso.limite.detail !== "" && <Text style={styles.limiteTexto}>{aviso.limite.detail}</Text>}
            {aviso.limite.espere_texto != null && <Text testID="chat-limite-espere" style={styles.limiteTexto}>{aviso.limite.espere_texto}</Text>}
          </View>
        )}
        {aviso?.tipo === "rede" && <Faixa tipo="info" texto={TEXTO_SEM_REDE} testID="chat-sem-rede" />}
        <View style={styles.entrada}>
          <TextInput
            ref={campo}
            testID="chat-campo"
            accessibilityLabel={PLACEHOLDER}
            value={texto}
            onChangeText={setTexto}
            onKeyPress={aoTeclar}
            multiline
            maxLength={MAXIMO_PERGUNTA}
            editable={!pensando && !limite}
            placeholder={limite ? PLACEHOLDER_ESPERA : PLACEHOLDER}
            placeholderTextColor={tema.cor["texto-2"]}
            style={[styles.campo, (pensando || limite) && styles.campoDesligado]}
          />
          <Pressable
            testID="chat-enviar"
            accessibilityRole="button"
            accessibilityLabel="Enviar pergunta"
            accessibilityState={{ disabled: !podeEnviar }}
            disabled={!podeEnviar}
            onPress={() => void enviar(texto)}
            style={comFoco([styles.enviar, !podeEnviar && styles.enviarDesligado], styles.foco)}
          >
            <MaterialIcons name="arrow-upward" size={tamanho.iconeGrande} color={podeEnviar ? tema.cor["sobre-botao"] : tema.cor["texto-desligado"]} accessible={false} />
          </Pressable>
        </View>
        {texto.length >= CONTADOR_A_PARTIR_DE && (
          <Text testID="chat-contador" style={styles.contador}>{`${texto.length} de ${MAXIMO_PERGUNTA}`}</Text>
        )}
        <Text testID="chat-aviso-ia" style={styles.avisoIa}>{AVISO_IA}</Text>
      </View>
    </KeyboardAvoidingView>
  );
}

type Estilos = ReturnType<typeof criarEstilos>;

function CartaoResposta({ msg, aoTentar, aoAbrirTreino, aoAbrirEvolucao, desligado, styles, tema }: { msg: MensagemChat; aoTentar: () => void; aoAbrirTreino: (id: number) => void; aoAbrirEvolucao: (serie: string) => void; desligado: boolean; styles: Estilos; tema: Tema }) {
  const hora = msg.criada_em ? horaCurta(msg.criada_em) : "";
  const abrir = (l: LinkChat) => {
    if (l.tipo === "treino" && l.atividade_id != null) aoAbrirTreino(l.atividade_id);
    else if (l.tipo === "evolucao" && l.serie_id) aoAbrirEvolucao(l.serie_id);
  };
  if (msg.estado === "recusada") {
    return (
      <View testID="chat-recusa" accessible accessibilityLabel={`Resposta${hora ? `, ${hora}` : ""}: ${msg.texto}`} style={[styles.resposta, styles.recusa]}>
        <Text style={styles.respostaTexto}>{msg.texto}</Text>
      </View>
    );
  }
  if (msg.estado !== "respondida") {
    // `reprovada` e `erro`: a mesma frase fixa e o mesmo botão; o motivo não aparece.
    return (
      <View testID="chat-erro" style={[styles.resposta, styles.erro]}>
        <Text accessibilityRole="alert" style={styles.respostaTexto}>{msg.texto}</Text>
        <Pressable testID="chat-tentar-de-novo" accessibilityRole="button" disabled={desligado} onPress={aoTentar} style={comFoco([styles.botaoContorno, desligado && styles.enviarDesligado], styles.foco)}>
          <Text style={styles.botaoContornoTexto}>Tentar de novo</Text>
        </Pressable>
      </View>
    );
  }
  return (
    <View testID="chat-resposta" accessibilityLiveRegion="polite" style={styles.resposta}>
      <Text accessibilityLabel={`Resposta${hora ? `, ${hora}` : ""}: ${msg.texto}${msg.links.length > 0 ? `, ${msg.links.length} ${msg.links.length === 1 ? "link" : "links"}` : ""}`} style={styles.respostaTexto}>
        {msg.texto}
      </Text>
      {msg.links.map((l, i) => (
        <Pressable key={`${l.tipo}-${l.atividade_id ?? l.serie_id ?? i}-${i}`} testID={`chat-link-${i}`} accessibilityRole="button" onPress={() => abrir(l)} style={comFoco(styles.botaoContorno, styles.foco)}>
          <Text style={styles.botaoContornoTexto}>{l.rotulo}</Text>
          <MaterialIcons name="chevron-right" size={tamanho.iconeMedio} color={tema.cor.link} accessible={false} />
        </Pressable>
      ))}
      <Text style={styles.hora}>{hora ? `${hora} · ${ROTULO_IA}` : ROTULO_IA}</Text>
    </View>
  );
}

function criarEstilos({ cor }: Tema, margem: number) {
  return StyleSheet.create({
    tela: { flex: 1, width: "100%", maxWidth: larguraConteudoMax + 2 * margem, alignSelf: "center" },
    cabecalho: { flexDirection: "row", alignItems: "center", minHeight: 56, paddingHorizontal: margem - espaco[2], gap: espaco[1], borderBottomWidth: borda.fina, borderBottomColor: cor.borda },
    alvo: { minHeight: tamanho.alvoMinimo, minWidth: tamanho.alvoMinimo, justifyContent: "center", alignItems: "center" },
    alvoTexto: { paddingHorizontal: espaco[2] },
    titulo: { ...fonte["titulo-secao"], color: cor.texto, flex: 1 },
    linkTexto: { ...fonte.botao, color: cor.link },
    historico: { flex: 1 },
    conteudo: { padding: margem, gap: espaco[4], flexGrow: 1 },
    apoio: { ...fonte.corpo, color: cor["texto-2"] },
    estado: { alignItems: "center", gap: espaco[3], paddingVertical: espaco[5] },
    textoErro: { ...fonte["corpo-forte"], color: cor.erro, textAlign: "center" },
    comeco: { gap: espaco[3] },
    tituloComeco: { ...fonte["numero-grande"], color: cor.texto },
    pronta: { minHeight: tamanho.botaoAltura, flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: espaco[4], borderRadius: raio.botao, borderWidth: borda.fina, borderColor: cor["borda-forte"], backgroundColor: cor.superficie },
    prontaTexto: { ...fonte.corpo, color: cor.texto, flex: 1 },
    troca: { gap: espaco[3] },
    dia: { ...fonte.legenda, color: cor["texto-2"], textAlign: "center" },
    pergunta: { alignSelf: "flex-end", maxWidth: "85%", gap: espaco[1], padding: espaco[3], borderRadius: raio["cartao-destaque"], backgroundColor: cor["superficie-2"] },
    perguntaTexto: { ...fonte.corpo, color: cor.texto },
    hora: { ...fonte.legenda, color: cor["texto-2"] },
    resposta: { alignSelf: "flex-start", maxWidth: "100%", gap: espaco[3], padding: espaco[4], borderRadius: raio.cartao, borderWidth: borda.fina, borderColor: cor.borda, backgroundColor: cor.superficie },
    recusa: { borderStyle: "dashed", borderColor: cor["borda-forte"], backgroundColor: cor.fundo },
    erro: { borderColor: cor.erro, backgroundColor: cor["erro-suave"] },
    respostaTexto: { ...fonte.corpo, color: cor.texto },
    botaoContorno: { minHeight: tamanho.alvoMinimo, flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: espaco[2], paddingHorizontal: espaco[3], borderRadius: raio.botao, borderWidth: borda.fina, borderColor: cor["borda-forte"] },
    botaoContornoTexto: { ...fonte.botao, color: cor.link },
    compositor: { gap: espaco[2], padding: margem, paddingTop: espaco[3], borderTopWidth: borda.fina, borderTopColor: cor.borda, backgroundColor: cor.fundo },
    limite: { gap: espaco[1], padding: espaco[3], borderRadius: raio.bloco, borderWidth: borda.fina, borderColor: cor.alerta, backgroundColor: cor["alerta-suave"] },
    limiteTitulo: { ...fonte["corpo-forte"], color: cor.alerta },
    limiteTexto: { ...fonte.corpo, color: cor.texto },
    entrada: { flexDirection: "row", alignItems: "flex-end", gap: espaco[2] },
    campo: { flex: 1, minHeight: 52, maxHeight: 120, paddingHorizontal: espaco[3], paddingVertical: espaco[3], borderRadius: raio.botao, borderWidth: borda.fina, borderColor: cor["borda-forte"], backgroundColor: cor.superficie, color: cor.texto, ...fonte.corpo },
    campoDesligado: { backgroundColor: cor["superficie-2"], borderColor: cor.borda },
    enviar: { width: tamanho.alvoMinimo, height: 52, justifyContent: "center", alignItems: "center", borderRadius: raio.botao, backgroundColor: cor.botao },
    enviarDesligado: { backgroundColor: cor["superficie-2"], opacity: 0.8 },
    contador: { ...fonte.legenda, color: cor["texto-2"], textAlign: "right" },
    avisoIa: { ...fonte.legenda, color: cor["texto-2"] },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}
