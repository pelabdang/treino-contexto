// Campo de texto com rótulo visível (spec docs/design/telas/entrar.md). Com `secreto`, esconde o texto e mostra o botão "Ver" / "Esconder"
// (alvo de 48). O texto volta a ficar escondido quando a tela sai (o estado morre com o componente).
import { type ComponentRef, type Ref, useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, type TextInputProps, View } from "react-native";

import { comFoco } from "../tema/foco";
import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";

export type RefCampo = ComponentRef<typeof TextInput>;

type Props = {
  rotulo: string;
  valor: string;
  aoMudar: (texto: string) => void;
  secreto?: boolean;
  desligado?: boolean;
  /** Dica fixa abaixo do campo (por exemplo, "Pelo menos 10 caracteres."). */
  dica?: string;
  testID: string;
  /** Referência ao `TextInput`, para levar o foco ao campo com problema. */
  campoRef?: Ref<RefCampo>;
  aoEnviar?: () => void;
  teclaEnter?: TextInputProps["returnKeyType"];
} & Pick<TextInputProps, "autoComplete" | "keyboardType" | "autoCapitalize" | "autoCorrect" | "textContentType">;

export function CampoTexto({ rotulo, valor, aoMudar, secreto = false, desligado = false, dica, testID, campoRef, aoEnviar, teclaEnter, ...resto }: Props) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const [visivel, setVisivel] = useState(false);
  const [emFoco, setEmFoco] = useState(false);
  return (
    <View style={styles.bloco}>
      <Text style={styles.rotulo}>{rotulo}</Text>
      <View style={[styles.campo, emFoco && styles.campoFoco, desligado && styles.campoDesligado]}>
        <TextInput
          ref={campoRef}
          testID={testID}
          accessibilityLabel={rotulo}
          value={valor}
          onChangeText={aoMudar}
          editable={!desligado}
          secureTextEntry={secreto && !visivel}
          autoCapitalize="none"
          autoCorrect={false}
          returnKeyType={teclaEnter}
          onSubmitEditing={aoEnviar}
          onFocus={() => setEmFoco(true)}
          onBlur={() => setEmFoco(false)}
          placeholderTextColor={tema.cor["texto-2"]}
          style={styles.entrada}
          {...resto}
        />
        {secreto && (
          <Pressable
            testID={`${testID}-ver`}
            accessibilityRole="button"
            accessibilityLabel={visivel ? "Esconder a senha" : "Mostrar a senha"}
            accessibilityState={{ selected: visivel, disabled: desligado }}
            disabled={desligado}
            onPress={() => setVisivel((v) => !v)}
            style={comFoco(styles.ver, styles.foco)}
          >
            <Text style={styles.verTexto}>{visivel ? "Esconder" : "Ver"}</Text>
          </Pressable>
        )}
      </View>
      {dica ? <Text style={styles.dica}>{dica}</Text> : null}
    </View>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    bloco: { gap: espaco[1] },
    rotulo: { ...fonte.rotulo, color: cor.texto },
    campo: {
      minHeight: tamanho.botaoAltura,
      flexDirection: "row",
      alignItems: "center",
      borderWidth: borda.fina,
      borderColor: cor["borda-forte"],
      borderRadius: raio.medio,
      backgroundColor: cor.superficie,
    },
    campoFoco: { borderColor: cor.foco, borderWidth: borda.foco },
    campoDesligado: { backgroundColor: cor["superficie-2"] },
    entrada: { ...fonte.corpo, flex: 1, minHeight: tamanho.botaoAltura, paddingHorizontal: espaco[3], color: cor.texto, outlineStyle: "none" } as object,
    ver: { minWidth: tamanho.botaoAltura, height: tamanho.botaoAltura, alignItems: "center", justifyContent: "center", paddingHorizontal: espaco[3] },
    verTexto: { ...fonte.botao, color: cor.destaque },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: -2 },
    dica: { ...fonte.legenda, color: cor["texto-2"] },
  });
}
