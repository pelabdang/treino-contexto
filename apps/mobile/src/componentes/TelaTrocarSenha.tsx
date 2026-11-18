// Tela "Trocar a senha" (#502, spec docs/design/telas/entrar.md). Duas ocasiões: primeiro acesso (senha provisória do operador: não dá para
// pular, sem "Voltar") e voluntária. O app só confere campo vazio e "as duas senhas novas iguais"; a regra da senha é da API (422).
import { MaterialIcons } from "@expo/vector-icons";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AccessibilityInfo, Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from "react-native";

import type { Falha, NovoAcesso, ResultadoSessao } from "../sessao/api";
import { comFoco } from "../tema/foco";
import { CampoTexto, type RefCampo } from "./CampoTexto";
import { Faixa } from "./Faixa";
import { borda, espaco, fonte, larguraMargemGrande, raio, tamanho, useMargemTela, useTema, type Tema } from "../tema";

type Props = {
  /** Primeiro acesso: sem "Voltar". */
  primeiroAcesso?: boolean;
  aoTrocar: (atual: string, nova: string) => Promise<ResultadoSessao<NovoAcesso>>;
  /** Depois de "Continuar" (início do papel no primeiro acesso, ou volta). */
  aoConcluir: () => void;
  aoVoltar?: () => void;
};

export const TEXTO_ATUAL_ERRADA = "A senha de agora não confere.";
export const TEXTO_NOVA_INVALIDA = "A senha nova precisa de pelo menos 10 caracteres e ser diferente da de agora.";
export const TEXTO_DIFERENTES = "As duas senhas novas não são iguais.";
export const TEXTO_SEM_REDE = "Não foi possível salvar. Tente de novo.";

type Erro = "atual" | "nova" | "diferentes" | "rede" | "servidor" | null;

function erroDe(f: Falha): Erro {
  if (f.motivo === "invalido") return f.tipo === "senha_atual_incorreta" ? "atual" : "nova";
  if (f.motivo === "rede") return "rede";
  return "servidor";
}

export function TelaTrocarSenha({ primeiroAcesso = false, aoTrocar, aoConcluir, aoVoltar }: Props) {
  const tema = useTema();
  const margem = useMargemTela();
  const larga = useWindowDimensions().width >= larguraMargemGrande;
  const styles = useMemo(() => criarEstilos(tema, margem, larga), [tema, margem, larga]);
  const [atual, setAtual] = useState("");
  const [nova, setNova] = useState("");
  const [repetida, setRepetida] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [salvo, setSalvo] = useState(false);
  const [erro, setErro] = useState<Erro>(null);
  const campoAtual = useRef<RefCampo>(null);
  const campoNova = useRef<RefCampo>(null);
  const campoRepetida = useRef<RefCampo>(null);
  const montada = useRef(true);
  useEffect(() => {
    montada.current = true;
    return () => {
      montada.current = false;
    };
  }, []);

  const pronto = atual.length > 0 && nova.length > 0 && repetida.length > 0;
  const podeSalvar = pronto && !salvando;

  const salvar = useCallback(async () => {
    if (!podeSalvar) return;
    if (nova !== repetida) {
      setErro("diferentes");
      setTimeout(() => campoRepetida.current?.focus(), 0);
      return;
    }
    setErro(null);
    setSalvando(true);
    const r = await aoTrocar(atual, nova);
    if (!montada.current) return;
    setSalvando(false);
    if (r.ok) {
      setAtual("");
      setNova("");
      setRepetida("");
      setSalvo(true);
      AccessibilityInfo.announceForAccessibility?.("Senha trocada.");
      return;
    }
    const e = erroDe(r.falha);
    setErro(e);
    // O foco vai ao campo com problema.
    setTimeout(() => (e === "atual" ? campoAtual : e === "nova" ? campoNova : e === "diferentes" ? campoRepetida : campoAtual).current?.focus(), 0);
  }, [podeSalvar, nova, repetida, aoTrocar, atual]);

  const textoErro =
    erro === "atual" ? TEXTO_ATUAL_ERRADA : erro === "nova" ? TEXTO_NOVA_INVALIDA : erro === "diferentes" ? TEXTO_DIFERENTES : erro === "rede" ? TEXTO_SEM_REDE : erro === "servidor" ? "Algo deu errado do nosso lado. Tente de novo mais tarde." : null;

  return (
    <ScrollView testID="tela-trocar-senha" keyboardShouldPersistTaps="handled" contentContainerStyle={styles.container}>
      <View style={styles.cartao}>
        {!primeiroAcesso && aoVoltar && !salvo && (
          <Pressable testID="voltar" accessibilityRole="button" accessibilityLabel="Voltar" onPress={aoVoltar} style={comFoco(styles.voltar, styles.foco)}>
            <MaterialIcons name="arrow-back" size={tamanho.iconeGrande} color={tema.cor.destaque} accessible={false} />
            <Text style={styles.voltarTexto}>Voltar</Text>
          </Pressable>
        )}
        <Text accessibilityRole="header" style={styles.titulo}>
          Trocar a senha
        </Text>
        {salvo ? (
          <>
            <View testID="senha-trocada" accessibilityLiveRegion="polite" style={styles.sucesso}>
              <MaterialIcons name="check-circle" size={tamanho.iconeGrande} color={tema.cor.sucesso} accessible={false} />
              <Text style={styles.sucessoTexto}>Senha trocada.</Text>
            </View>
            <Pressable testID="continuar" accessibilityRole="button" onPress={aoConcluir} style={comFoco(styles.botao, styles.foco)}>
              <Text style={styles.botaoTexto}>Continuar</Text>
            </Pressable>
          </>
        ) : (
          <>
            <Text style={styles.texto}>
              {primeiroAcesso ? "Sua senha foi criada para o primeiro acesso. Escolha uma senha só sua." : "Escolha uma senha só sua."}
            </Text>
            <CampoTexto testID="campo-senha-atual" rotulo="Senha de agora" valor={atual} aoMudar={setAtual} secreto desligado={salvando} campoRef={campoAtual} autoComplete="current-password" textContentType="password" teclaEnter="next" aoEnviar={() => campoNova.current?.focus()} />
            <CampoTexto testID="campo-senha-nova" rotulo="Senha nova" valor={nova} aoMudar={setNova} secreto desligado={salvando} campoRef={campoNova} autoComplete="new-password" textContentType="newPassword" dica="Pelo menos 10 caracteres." teclaEnter="next" aoEnviar={() => campoRepetida.current?.focus()} />
            <CampoTexto testID="campo-senha-repetida" rotulo="Repita a senha nova" valor={repetida} aoMudar={setRepetida} secreto desligado={salvando} campoRef={campoRepetida} autoComplete="new-password" textContentType="newPassword" teclaEnter="done" aoEnviar={salvar} />
            {textoErro && <Faixa tipo="erro" testID="faixa-erro" texto={textoErro} />}
            <Pressable
              testID="botao-salvar"
              accessibilityRole="button"
              accessibilityState={{ disabled: !podeSalvar, busy: salvando }}
              disabled={!podeSalvar}
              onPress={salvar}
              style={comFoco([styles.botao, !podeSalvar && styles.botaoDesligado], styles.foco)}
            >
              <Text style={[styles.botaoTexto, !podeSalvar && styles.botaoTextoDesligado]}>{salvando ? "Salvando..." : "Salvar a senha nova"}</Text>
            </Pressable>
          </>
        )}
      </View>
    </ScrollView>
  );
}

function criarEstilos({ cor }: Tema, margem: number, larga: boolean) {
  return StyleSheet.create({
    container: { flexGrow: 1, padding: margem, paddingTop: larga ? espaco[6] : margem },
    cartao: {
      width: "100%",
      maxWidth: 420,
      alignSelf: larga ? "center" : "stretch",
      gap: espaco[3],
      ...(larga ? { padding: espaco[5], backgroundColor: cor.superficie, borderWidth: borda.fina, borderColor: cor.borda, borderRadius: raio.grande } : {}),
    },
    voltar: { minHeight: tamanho.botaoAltura, flexDirection: "row", alignItems: "center", gap: espaco[1], alignSelf: "flex-start" },
    voltarTexto: { ...fonte.botao, color: cor.destaque },
    titulo: { ...fonte["titulo-tela"], color: cor.texto },
    texto: { ...fonte.corpo, color: cor["texto-2"] },
    sucesso: { flexDirection: "row", alignItems: "center", gap: espaco[2], padding: espaco[3], borderRadius: raio.medio, backgroundColor: cor["sucesso-suave"], borderWidth: borda.fina, borderColor: cor.sucesso },
    sucessoTexto: { ...fonte["corpo-forte"], color: cor.sucesso },
    botao: { minHeight: tamanho.botaoAltura, alignItems: "center", justifyContent: "center", borderRadius: raio.medio, backgroundColor: cor.destaque, paddingHorizontal: espaco[4] },
    botaoDesligado: { backgroundColor: cor["superficie-2"] },
    botaoTexto: { ...fonte.botao, color: cor["sobre-destaque"] },
    botaoTextoDesligado: { color: cor["texto-desligado"] },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}
