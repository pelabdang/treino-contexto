// Termo de consentimento (#503, spec docs/design/telas/consentimento.md): o texto vem da API (versão, texto e `provisorio`); o app registra
// a versão que o atleta leu. "Li e concordo" não vem marcado e liga o botão "Dar consentimento". Sem "aceitar tudo".
import { MaterialIcons } from "@expo/vector-icons";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { buscarProfessores, buscarTermo, darConsentimento, type Termo } from "../consentimento/api";
import { comFoco } from "../tema/foco";
import { EsqueletoPendentes } from "./Esqueleto";
import { Faixa } from "./Faixa";
import { borda, espaco, fonte, larguraConteudoMax, raio, tamanho, useMargemTela, useTema, type Tema } from "../tema";

type Props = {
  apiUrl: string;
  atletaId: number;
  professorId: number;
  aoVoltar: () => void;
  /** Depois de salvar: volta à lista (que recarrega). */
  aoConcluir: () => void;
  /** O vínculo não existe mais (404). */
  aoInexistente: () => void;
  fetchFn?: typeof fetch;
};

type Estado = { tipo: "carregando" } | { tipo: "ok"; termo: Termo; nome: string } | { tipo: "erro" };
type Aviso = "rede" | "mudou" | "servidor" | null;

export const TEXTO_PROVISORIO = "Este texto é provisório. Ainda não foi revisto por quem entende de lei e vale só para o piloto.";

export function TelaTermo({ apiUrl, atletaId, professorId, aoVoltar, aoConcluir, aoInexistente, fetchFn }: Props) {
  const tema = useTema();
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
  const [estado, setEstado] = useState<Estado>({ tipo: "carregando" });
  const [tentativa, setTentativa] = useState(0);
  const [marcado, setMarcado] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [aviso, setAviso] = useState<Aviso>(null);
  const opcoes = useMemo(() => ({ baseUrl: apiUrl, fetch: fetchFn }), [apiUrl, fetchFn]);

  useEffect(() => {
    let ativo = true;
    Promise.all([buscarTermo(opcoes), buscarProfessores(atletaId, opcoes)]).then(([t, p]) => {
      if (!ativo) return;
      if (!t.ok || !p.ok) return setEstado({ tipo: "erro" });
      const v = p.dados.professores.find((x) => x.professor_id === professorId);
      if (!v) return aoInexistente();
      setEstado({ tipo: "ok", termo: t.dados, nome: v.nome });
    });
    return () => {
      ativo = false;
    };
    // `aoInexistente` muda a cada render da rota; só a busca depende de tentativa, ids e opções.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [atletaId, professorId, opcoes, tentativa]);

  const recarregar = useCallback(() => {
    setEstado({ tipo: "carregando" });
    setTentativa((n) => n + 1);
  }, []);

  const dar = useCallback(async () => {
    if (estado.tipo !== "ok" || !marcado || salvando) return;
    setAviso(null);
    setSalvando(true);
    const r = await darConsentimento(atletaId, professorId, estado.termo.versao, opcoes);
    setSalvando(false);
    if (r.ok) {
      aoConcluir();
    } else if (r.erro.tipo === "nao_encontrado") {
      aoInexistente();
    } else if (r.erro.tipo === "http" && r.erro.status === 409) {
      // O termo mudou enquanto lia: recarrega e desmarca a caixa.
      setMarcado(false);
      setAviso("mudou");
      setTentativa((n) => n + 1);
    } else {
      setAviso(r.erro.tipo === "rede" ? "rede" : "servidor");
    }
  }, [estado, marcado, salvando, atletaId, professorId, opcoes, aoConcluir, aoInexistente]);

  const podeDar = estado.tipo === "ok" && marcado && !salvando;

  return (
    <ScrollView testID="tela-termo" contentContainerStyle={styles.container}>
      <View style={styles.coluna}>
        <Pressable testID="voltar" accessibilityRole="button" accessibilityLabel="Voltar" onPress={aoVoltar} style={comFoco(styles.voltar, styles.foco)}>
          <MaterialIcons name="arrow-back" size={tamanho.iconeMedio} color={tema.cor.link} accessible={false} />
          <Text style={styles.voltarTexto}>Voltar</Text>
        </Pressable>
        <Text accessibilityRole="header" style={styles.titulo}>
          Termo de consentimento
        </Text>

        {aviso === "mudou" && <Faixa tipo="info" testID="faixa-mudou" texto="O texto do termo mudou. Leia de novo antes de dar o consentimento." />}

        {estado.tipo === "carregando" && (
          <View>
            <Text accessibilityLiveRegion="polite" style={styles.texto}>
              Carregando o termo...
            </Text>
            <EsqueletoPendentes />
          </View>
        )}
        {estado.tipo === "erro" && (
          <View testID="estado-erro" style={styles.estado}>
            <MaterialIcons name="error-outline" size={tamanho.iconeEstado} color={tema.cor.erro} accessible={false} />
            <Text accessibilityRole="alert" style={[styles.texto, { textAlign: "center" }]}>
              Não foi possível carregar o termo. Tente de novo.
            </Text>
            <Pressable testID="tentar-de-novo" accessibilityRole="button" onPress={recarregar} style={comFoco([styles.botao, styles.primario, { alignSelf: "stretch" }], styles.foco)}>
              <Text style={styles.primarioTexto}>Tentar de novo</Text>
            </Pressable>
          </View>
        )}
        {estado.tipo === "ok" && (
          <>
            {estado.termo.provisorio && (
              <View testID="faixa-provisorio" accessible accessibilityRole="alert" style={styles.provisorio}>
                <MaterialIcons name="warning-amber" size={tamanho.iconeGrande} color={tema.cor.alerta} accessible={false} />
                <View style={{ flex: 1 }}>
                  <Text style={styles.provisorioTitulo}>Texto provisório</Text>
                  <Text style={styles.provisorioTexto}>{TEXTO_PROVISORIO}</Text>
                </View>
              </View>
            )}
            <Text style={styles.texto}>
              Você está dando permissão a: <Text style={styles.nome}>{estado.nome}</Text>.
            </Text>
            {/* O texto vem inteiro da API, sem cortar nem recolher; cada quebra de linha vira um parágrafo. */}
            <View testID="texto-termo" style={{ gap: espaco[3] }}>
              {estado.termo.texto
                .split(/\r?\n+/)
                .filter((p) => p.trim())
                .map((p, i) => (
                  <Text key={i} style={styles.corpo}>
                    {p}
                  </Text>
                ))}
            </View>
            <Pressable
              testID="li-e-concordo"
              accessibilityRole="checkbox"
              accessibilityState={{ checked: marcado, disabled: salvando }}
              disabled={salvando}
              onPress={() => setMarcado((m) => !m)}
              style={comFoco(styles.caixa, styles.foco)}
            >
              <MaterialIcons name={marcado ? "check-box" : "check-box-outline-blank"} size={tamanho.iconeGrande} color={marcado ? tema.cor.link : tema.cor["borda-forte"]} accessible={false} />
              <Text style={styles.caixaTexto}>Li e concordo</Text>
            </Pressable>
            {aviso === "rede" && <Faixa tipo="erro" testID="faixa-erro" texto="Não foi possível salvar. Tente de novo." />}
            {aviso === "servidor" && <Faixa tipo="erro" testID="faixa-erro" texto="Algo deu errado do nosso lado. Tente de novo mais tarde." />}
            <Pressable
              testID="dar-consentimento"
              accessibilityRole="button"
              accessibilityState={{ disabled: !podeDar, busy: salvando }}
              disabled={!podeDar}
              onPress={dar}
              style={comFoco([styles.botao, podeDar ? styles.primario : styles.desligado], styles.foco)}
            >
              <Text style={podeDar ? styles.primarioTexto : styles.desligadoTexto}>{salvando ? "Salvando..." : "Dar consentimento"}</Text>
            </Pressable>
          </>
        )}
      </View>
    </ScrollView>
  );
}

function criarEstilos({ cor }: Tema, margem: number) {
  return StyleSheet.create({
    container: { padding: margem, alignItems: "center" },
    coluna: { width: "100%", maxWidth: larguraConteudoMax, gap: espaco[3] },
    voltar: { minHeight: tamanho.botaoAltura, flexDirection: "row", alignItems: "center", gap: espaco[1], alignSelf: "flex-start" },
    voltarTexto: { ...fonte.botao, color: cor.link },
    titulo: { ...fonte["titulo-tela"], color: cor.texto },
    texto: { ...fonte.corpo, color: cor["texto-2"] },
    corpo: { ...fonte.corpo, color: cor.texto },
    nome: { ...fonte["corpo-forte"], color: cor.texto },
    estado: { alignItems: "center", gap: espaco[3], paddingVertical: espaco[5] },
    provisorio: { flexDirection: "row", gap: espaco[2], padding: espaco[3], borderRadius: raio.bloco, borderWidth: borda.fina, borderColor: cor.alerta, backgroundColor: cor["alerta-suave"] },
    provisorioTitulo: { ...fonte["corpo-forte"], color: cor.alerta },
    provisorioTexto: { ...fonte.corpo, color: cor.alerta },
    caixa: { minHeight: tamanho.botaoAltura, flexDirection: "row", alignItems: "center", gap: espaco[2] },
    caixaTexto: { ...fonte.corpo, color: cor.texto, flex: 1 },
    botao: { minHeight: tamanho.botaoAltura, alignItems: "center", justifyContent: "center", borderRadius: raio.botao, paddingHorizontal: espaco[4] },
    primario: { backgroundColor: cor.botao },
    primarioTexto: { ...fonte.botao, color: cor["sobre-botao"] },
    desligado: { backgroundColor: cor["superficie-2"] },
    desligadoTexto: { ...fonte.botao, color: cor["texto-desligado"] },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}
