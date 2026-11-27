// Aba "Conta": ajustes e manutenção, fora da frente do atleta. Atleta: Semana-padrão, Consentimento (com selo quando há pedido),
// Enviar arquivo FIT, Trocar senha e Sair. Professor: Trocar senha e Sair. Sair pede confirmação (diálogo com "Cancelar" primário).
import { MaterialIcons } from "@expo/vector-icons";
import { useMemo, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { BotaoEnviarFit } from "./BotaoEnviarFit";
import { DialogoSair } from "./DialogoSair";
import { comFoco } from "../tema/foco";
import { borda, espaco, fonte, larguraConteudoMax, raio, tamanho, useMargemTela, useTema, type Tema } from "../tema";

type Props = {
  nome: string;
  papel: "atleta" | "professor";
  /** Pedidos de professor aguardando resposta (selo no item Consentimento). */
  pedidos?: number;
  aoAbrirSemanaPadrao?: () => void;
  aoAbrirConsentimento?: () => void;
  aoTrocarSenha: () => void;
  aoSair: () => void;
  /** Enviar FIT (só atleta): conexão com a API. */
  envio?: { apiUrl: string; atletaId: number; fetchFn?: typeof fetch; aoEnviar?: () => void };
};

export function TelaConta({ nome, papel, pedidos = 0, aoAbrirSemanaPadrao, aoAbrirConsentimento, aoTrocarSenha, aoSair, envio }: Props) {
  const tema = useTema();
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
  const [saindo, setSaindo] = useState(false);
  return (
    <ScrollView testID="tela-conta" contentContainerStyle={styles.container}>
      <View style={styles.coluna}>
        <Text accessibilityRole="header" style={styles.titulo}>
          Conta
        </Text>
        <Text testID="conta-nome" style={styles.nome}>
          {nome}
        </Text>
        <View style={styles.lista}>
          {papel === "atleta" && aoAbrirSemanaPadrao && <Linha id="semana-padrao" icone="event" texto="Semana-padrão" aoPressionar={aoAbrirSemanaPadrao} styles={styles} tema={tema} />}
          {papel === "atleta" && aoAbrirConsentimento && (
            <Linha
              id="consentimento"
              icone="verified-user"
              texto="Consentimento"
              selo={pedidos}
              rotuloAcessivel={pedidos > 0 ? `Consentimento, ${pedidos} ${pedidos === 1 ? "pedido" : "pedidos"}` : "Consentimento"}
              aoPressionar={aoAbrirConsentimento}
              styles={styles}
              tema={tema}
            />
          )}
          <Linha id="trocar-senha" icone="lock-outline" texto="Trocar senha" aoPressionar={aoTrocarSenha} styles={styles} tema={tema} />
          <Linha id="sair" icone="logout" texto="Sair" aoPressionar={() => setSaindo(true)} styles={styles} tema={tema} ultima />
        </View>
        {papel === "atleta" && envio && (
          <View style={styles.envio}>
            <Text style={styles.rotuloSecao}>Enviar um treino</Text>
            <BotaoEnviarFit apiUrl={envio.apiUrl} atletaId={envio.atletaId} fetchFn={envio.fetchFn} aoEnviar={envio.aoEnviar} />
          </View>
        )}
      </View>
      <DialogoSair
        visivel={saindo}
        aoCancelar={() => setSaindo(false)}
        aoConfirmar={() => {
          setSaindo(false);
          aoSair();
        }}
      />
    </ScrollView>
  );
}

type Estilos = ReturnType<typeof criarEstilos>;

function Linha({ id, icone, texto, aoPressionar, selo = 0, rotuloAcessivel, ultima = false, styles, tema }: {
  id: string;
  icone: React.ComponentProps<typeof MaterialIcons>["name"];
  texto: string;
  aoPressionar: () => void;
  selo?: number;
  rotuloAcessivel?: string;
  ultima?: boolean;
  styles: Estilos;
  tema: Tema;
}) {
  return (
    <Pressable
      testID={`conta-${id}`}
      accessibilityRole="button"
      accessibilityLabel={rotuloAcessivel ?? texto}
      onPress={aoPressionar}
      style={comFoco([styles.linha, !ultima && styles.linhaDivisoria], styles.foco)}
    >
      <MaterialIcons name={icone} size={tamanho.iconeGrande} color={tema.cor["texto-2"]} accessible={false} />
      <Text style={styles.linhaTexto}>{texto}</Text>
      {selo > 0 && (
        <View testID={`conta-selo-${id}`} style={styles.selo}>
          <Text style={styles.seloTexto}>{selo === 1 ? "1 pedido" : `${selo} pedidos`}</Text>
        </View>
      )}
      <MaterialIcons name="chevron-right" size={tamanho.iconeMedio} color={tema.cor["texto-2"]} accessible={false} />
    </Pressable>
  );
}

function criarEstilos({ cor }: Tema, margem: number) {
  return StyleSheet.create({
    container: { padding: margem, alignItems: "center" },
    coluna: { width: "100%", maxWidth: larguraConteudoMax, gap: espaco[3] },
    titulo: { ...fonte["titulo-tela"], color: cor.texto },
    nome: { ...fonte.corpo, color: cor["texto-2"] },
    lista: { backgroundColor: cor.superficie, borderWidth: borda.fina, borderColor: cor.borda, borderRadius: raio.cartao, overflow: "hidden" },
    linha: { minHeight: tamanho.listaLinhaAltura, flexDirection: "row", alignItems: "center", gap: espaco[3], paddingHorizontal: espaco[4] },
    linhaDivisoria: { borderBottomWidth: borda.fina, borderBottomColor: cor.borda },
    linhaTexto: { ...fonte.corpo, color: cor.texto, flex: 1 },
    selo: { paddingHorizontal: espaco[2], paddingVertical: 2, borderRadius: raio.pilula, backgroundColor: cor["marca-suave"] },
    seloTexto: { ...fonte.legenda, color: cor.link, fontFamily: fonte["corpo-forte"].fontFamily },
    envio: { gap: espaco[2] },
    rotuloSecao: { ...fonte.rotulo, color: cor["texto-2"] },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: -2 },
  });
}
