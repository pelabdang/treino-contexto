// Lista de consentimentos do atleta (#503, spec docs/design/telas/consentimento.md): quem pode ver os treinos. Aguardando primeiro,
// depois consentidos. Dar consentimento abre a tela do termo; retirar pede confirmação ("Cancelar" é o botão principal).
// Estado em ícone e palavra, nunca só cor. Nada do que vem da API (nome, versão do termo) vai para log.
import { MaterialIcons } from "@expo/vector-icons";
import { type ComponentRef, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AccessibilityInfo, Modal, Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from "react-native";

import { buscarProfessores, dataCurta, ordenar, retirarConsentimento, type Vinculo } from "../consentimento/api";
import { FOCAVEL, focar } from "../navegacao/foco";
import { comFoco } from "../tema/foco";
import { EsqueletoPendentes } from "./Esqueleto";
import { Faixa } from "./Faixa";
import { borda, espaco, fonte, larguraConteudoMax, larguraMargemGrande, raio, tamanho, useMargemTela, useTema, type Tema } from "../tema";

type Props = {
  apiUrl: string;
  atletaId: number;
  aoVoltar?: () => void;
  aoAbrirTermo: (professorId: number) => void;
  /** Muda quando a tela volta ao foco: busca a lista de novo (depois de dar o consentimento). */
  atualizar?: number;
  /** Veio da tela do termo porque o vínculo não existe mais. */
  avisoInexistente?: boolean;
  fetchFn?: typeof fetch;
};

type Estado = { tipo: "carregando" } | { tipo: "ok"; lista: Vinculo[] } | { tipo: "rede" } | { tipo: "erro" };

export const TEXTO_VAZIO = "Nenhum professor pediu para ver os seus treinos. Quando pedir, o pedido aparece aqui.";

export function TelaConsentimento({ apiUrl, atletaId, aoVoltar, aoAbrirTermo, atualizar = 0, avisoInexistente = false, fetchFn }: Props) {
  const tema = useTema();
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
  const [estado, setEstado] = useState<Estado>({ tipo: "carregando" });
  const [tentativa, setTentativa] = useState(0);
  const [retirando, setRetirando] = useState<Vinculo | null>(null);
  const [erroRetirar, setErroRetirar] = useState(false);
  const opcoes = useMemo(() => ({ baseUrl: apiUrl, fetch: fetchFn }), [apiUrl, fetchFn]);

  useEffect(() => {
    let ativo = true;
    buscarProfessores(atletaId, opcoes).then((r) => {
      if (!ativo) return;
      // Um erro numa atualização em segundo plano não apaga a lista que já está na tela.
      setEstado((atual) => (r.ok ? { tipo: "ok", lista: ordenar(r.dados.professores) } : atual.tipo === "ok" ? atual : { tipo: r.erro.tipo === "rede" ? "rede" : "erro" }));
    });
    return () => {
      ativo = false;
    };
  }, [atletaId, opcoes, tentativa, atualizar]);

  const tentarDeNovo = useCallback(() => {
    setEstado({ tipo: "carregando" });
    setTentativa((n) => n + 1);
  }, []);

  const retirar = useCallback(async () => {
    const alvo = retirando;
    if (!alvo) return;
    setRetirando(null);
    const r = await retirarConsentimento(atletaId, alvo.professor_id, opcoes);
    if (r.ok) {
      setErroRetirar(false);
      AccessibilityInfo.announceForAccessibility?.("Consentimento retirado.");
      setTentativa((n) => n + 1);
    } else if (r.erro.tipo === "nao_encontrado") {
      setTentativa((n) => n + 1); // sumiu: a lista recarrega sem ele
    } else {
      setErroRetirar(true);
    }
  }, [retirando, atletaId, opcoes]);

  return (
    <ScrollView testID="tela-consentimento" contentContainerStyle={styles.container}>
      <View style={styles.coluna}>
        {aoVoltar && (
          <Pressable testID="voltar" accessibilityRole="button" accessibilityLabel="Voltar" onPress={aoVoltar} style={comFoco(styles.voltar, styles.foco)}>
            <MaterialIcons name="arrow-back" size={tamanho.iconeMedio} color={tema.cor.destaque} accessible={false} />
            <Text style={styles.voltarTexto}>Voltar</Text>
          </Pressable>
        )}
        <Text accessibilityRole="header" style={styles.titulo}>
          Consentimento
        </Text>
        <Text style={styles.texto}>Quem pode ver os seus treinos.</Text>
        {avisoInexistente && <Faixa tipo="info" testID="faixa-inexistente" texto="Este pedido não existe mais." />}
        {erroRetirar && <Faixa tipo="erro" testID="faixa-erro-retirar" texto="Não foi possível retirar. Tente de novo." />}

        {estado.tipo === "carregando" && (
          <View>
            <Text accessibilityLiveRegion="polite" style={styles.texto}>
              Carregando...
            </Text>
            <EsqueletoPendentes />
          </View>
        )}
        {estado.tipo === "rede" && <Falha icone="wifi-off" texto="Não foi possível falar com o servidor" aoTentar={tentarDeNovo} styles={styles} tema={tema} />}
        {estado.tipo === "erro" && <Falha icone="error-outline" texto="Não foi possível carregar. Tente de novo mais tarde." styles={styles} tema={tema} />}
        {estado.tipo === "ok" && estado.lista.length === 0 && (
          <View testID="estado-vazio" style={styles.estado}>
            <MaterialIcons name="info-outline" size={tamanho.iconeEstado} color={tema.cor["texto-2"]} accessible={false} />
            <Text style={[styles.texto, { textAlign: "center" }]}>{TEXTO_VAZIO}</Text>
          </View>
        )}
        {estado.tipo === "ok" &&
          estado.lista.map((v) => (
            <CartaoProfessor key={v.professor_id} v={v} aoDar={() => aoAbrirTermo(v.professor_id)} aoRetirar={() => setRetirando(v)} styles={styles} tema={tema} />
          ))}
      </View>
      <DialogoRetirar vinculo={retirando} aoCancelar={() => setRetirando(null)} aoConfirmar={retirar} />
    </ScrollView>
  );
}

function CartaoProfessor({ v, aoDar, aoRetirar, styles, tema }: { v: Vinculo; aoDar: () => void; aoRetirar: () => void; styles: Estilos; tema: Tema }) {
  const consentido = v.consentimento;
  const estadoTexto = consentido ? `Consentido em ${dataCurta(v.consentimento_em)}` : "Aguardando você";
  return (
    <View testID={`professor-${v.professor_id}`} accessible accessibilityLabel={`${v.nome}, ${estadoTexto.toLowerCase()}`} style={styles.cartao}>
      <Text style={styles.nome}>{v.nome}</Text>
      <View style={styles.linhaEstado}>
        <MaterialIcons name={consentido ? "check-circle-outline" : "hourglass-empty"} size={tamanho.iconeMedio} color={tema.cor["texto-2"]} accessible={false} />
        <Text style={styles.estadoTexto}>{estadoTexto}</Text>
      </View>
      {!consentido && v.termo_desatualizado && <Text style={styles.legenda}>O termo mudou. Leia e dê o consentimento de novo.</Text>}
      {consentido ? (
        <Pressable testID={`retirar-${v.professor_id}`} accessibilityRole="button" accessibilityLabel={`Retirar consentimento de ${v.nome}`} onPress={aoRetirar} style={comFoco([styles.botao, styles.secundario], styles.foco)}>
          <Text style={styles.secundarioTexto}>Retirar consentimento</Text>
        </Pressable>
      ) : (
        <Pressable testID={`dar-${v.professor_id}`} accessibilityRole="button" accessibilityLabel={`Ler e dar consentimento a ${v.nome}`} onPress={aoDar} style={comFoco([styles.botao, styles.primario], styles.foco)}>
          <Text style={styles.primarioTexto}>Ler e dar consentimento</Text>
        </Pressable>
      )}
    </View>
  );
}

function Falha({ icone, texto, aoTentar, styles, tema }: { icone: "wifi-off" | "error-outline"; texto: string; aoTentar?: () => void; styles: Estilos; tema: Tema }) {
  return (
    <View testID="estado-erro" style={styles.estado}>
      <MaterialIcons name={icone} size={tamanho.iconeEstado} color={tema.cor.erro} accessible={false} />
      <Text accessibilityRole="alert" style={[styles.texto, { textAlign: "center" }]}>
        {texto}
      </Text>
      {aoTentar && (
        <Pressable testID="tentar-de-novo" accessibilityRole="button" onPress={aoTentar} style={comFoco([styles.botao, styles.primario, { alignSelf: "stretch" }], styles.foco)}>
          <Text style={styles.primarioTexto}>Tentar de novo</Text>
        </Pressable>
      )}
    </View>
  );
}

function DialogoRetirar({ vinculo, aoCancelar, aoConfirmar }: { vinculo: Vinculo | null; aoCancelar: () => void; aoConfirmar: () => void }) {
  const tema = useTema();
  const computador = useWindowDimensions().width >= larguraMargemGrande;
  const styles = useMemo(() => criarEstilosDialogo(tema, computador), [tema, computador]);
  const titulo = useRef<ComponentRef<typeof Text>>(null);
  useEffect(() => {
    if (!vinculo) return;
    const t = setTimeout(() => focar(titulo.current), 0);
    return () => clearTimeout(t);
  }, [vinculo]);
  return (
    <Modal visible={!!vinculo} transparent animationType="none" onRequestClose={aoCancelar} accessibilityViewIsModal>
      <View style={styles.fundo}>
        <View role="dialog" aria-modal aria-label="Retirar o consentimento?" testID="dialogo-retirar" style={styles.caixa}>
          <Text ref={titulo} {...FOCAVEL} accessibilityRole="header" style={styles.titulo}>
            Retirar o consentimento?
          </Text>
          <Text style={styles.texto}>
            {vinculo?.nome} deixa de ver os seus treinos a partir de agora. O que ele já gravou, como o tipo corrigido de um treino, fica. Você pode dar o
            consentimento de novo depois.
          </Text>
          <View style={styles.botoes}>
            <Pressable testID="cancelar-retirar" accessibilityRole="button" onPress={aoCancelar} style={comFoco([styles.botao, styles.primario], styles.foco)}>
              <Text style={styles.primarioTexto}>Cancelar</Text>
            </Pressable>
            <Pressable testID="confirmar-retirar" accessibilityRole="button" onPress={aoConfirmar} style={comFoco([styles.botao, styles.secundario], styles.foco)}>
              <Text style={styles.secundarioTexto}>Retirar</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

type Estilos = ReturnType<typeof criarEstilos>;

function criarEstilos({ cor }: Tema, margem: number) {
  return StyleSheet.create({
    container: { padding: margem, alignItems: "center" },
    coluna: { width: "100%", maxWidth: larguraConteudoMax, gap: espaco[3] },
    voltar: { minHeight: tamanho.botaoAltura, flexDirection: "row", alignItems: "center", gap: espaco[1], alignSelf: "flex-start" },
    voltarTexto: { ...fonte.botao, color: cor.destaque },
    titulo: { ...fonte["titulo-tela"], color: cor.texto },
    texto: { ...fonte.corpo, color: cor["texto-2"] },
    estado: { alignItems: "center", gap: espaco[3], paddingVertical: espaco[5] },
    cartao: { padding: espaco[4], gap: espaco[2], backgroundColor: cor.superficie, borderWidth: borda.fina, borderColor: cor.borda, borderRadius: raio.grande },
    nome: { ...fonte["titulo-secao"], color: cor.texto },
    linhaEstado: { flexDirection: "row", alignItems: "center", gap: espaco[2] },
    estadoTexto: { ...fonte["corpo-forte"], color: cor["texto-2"] },
    legenda: { ...fonte.legenda, color: cor["texto-2"] },
    botao: { minHeight: tamanho.botaoAltura, alignItems: "center", justifyContent: "center", borderRadius: raio.medio, paddingHorizontal: espaco[4] },
    primario: { backgroundColor: cor.destaque },
    primarioTexto: { ...fonte.botao, color: cor["sobre-destaque"] },
    secundario: { borderWidth: borda.fina, borderColor: cor["borda-forte"], backgroundColor: cor.superficie },
    secundarioTexto: { ...fonte.botao, color: cor.texto },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}

function criarEstilosDialogo({ cor }: Tema, computador: boolean) {
  return StyleSheet.create({
    fundo: { flex: 1, backgroundColor: "rgba(0,0,0,0.5)", justifyContent: computador ? "center" : "flex-end", alignItems: "center" },
    caixa: {
      width: "100%",
      maxWidth: 400,
      padding: espaco[4],
      gap: espaco[3],
      backgroundColor: cor.superficie,
      borderWidth: borda.fina,
      borderColor: cor.borda,
      borderTopLeftRadius: raio.grande,
      borderTopRightRadius: raio.grande,
      ...(computador ? { borderBottomLeftRadius: raio.grande, borderBottomRightRadius: raio.grande } : {}),
    },
    titulo: { ...fonte["titulo-secao"], color: cor.texto },
    texto: { ...fonte.corpo, color: cor["texto-2"] },
    botoes: { flexDirection: "row", gap: espaco[3] },
    botao: { flex: 1, minHeight: tamanho.botaoAltura, alignItems: "center", justifyContent: "center", borderRadius: raio.medio },
    primario: { backgroundColor: cor.destaque },
    primarioTexto: { ...fonte.botao, color: cor["sobre-destaque"] },
    secundario: { borderWidth: borda.fina, borderColor: cor["borda-forte"], backgroundColor: cor.superficie },
    secundarioTexto: { ...fonte.botao, color: cor.texto },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}
