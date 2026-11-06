import { enviarAtividadeFit, type ArquivoFit, type ErroApi } from "@treino/api-client";
import * as DocumentPicker from "expo-document-picker";
import { useMemo, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";

import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";

type Props = {
  apiUrl: string;
  atletaId: number;
  /** Chamado depois de um envio com sucesso (201 ou 200). */
  aoEnviar?: () => void;
  /** "secundario" (padrão, guia visual) com dados na tela; "primario" no estado vazio. */
  variante?: "primario" | "secundario";
  /** Troque nos testes. Padrão: o fetch global. */
  fetchFn?: typeof fetch;
};

type Estado =
  | { tipo: "parado" }
  | { tipo: "enviando" }
  | { tipo: "sucesso"; mensagem: string }
  | { tipo: "erro"; mensagem: string };

export function mensagemErroEnvio(erro: ErroApi): string {
  switch (erro.tipo) {
    case "rede":
      return "Não foi possível falar com o servidor. Verifique a conexão e tente de novo.";
    case "nao_encontrado":
      return erro.detalhe.detail || "Atleta não encontrado";
    case "http":
      return erro.detail || "Não foi possível enviar o arquivo. Tente de novo mais tarde.";
    default:
      return "Escolha um arquivo .fit para enviar.";
  }
}

export function BotaoEnviarFit({ apiUrl, atletaId, aoEnviar, fetchFn, variante = "secundario" }: Props) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema), [tema]);
  const [estado, setEstado] = useState<Estado>({ tipo: "parado" });

  async function escolherEEnviar() {
    let escolha: DocumentPicker.DocumentPickerResult;
    try {
      escolha = await DocumentPicker.getDocumentAsync({ type: "*/*", copyToCacheDirectory: true });
    } catch {
      setEstado({ tipo: "erro", mensagem: "Não foi possível abrir o seletor de arquivos." });
      return;
    }
    if (escolha.canceled || escolha.assets.length === 0) return;
    const asset = escolha.assets[0];
    // Na web o seletor entrega o `File`; no celular, o `uri` do arquivo.
    const arquivo: ArquivoFit = asset.file ?? { uri: asset.uri, name: asset.name, type: asset.mimeType };

    setEstado({ tipo: "enviando" });
    const r = await enviarAtividadeFit(atletaId, arquivo, { baseUrl: apiUrl, fetch: fetchFn, nome: asset.name });
    if (r.ok) {
      setEstado({ tipo: "sucesso", mensagem: r.dados.criada ? "Atividade adicionada" : "Essa atividade já estava aqui" });
      aoEnviar?.();
    } else {
      setEstado({ tipo: "erro", mensagem: mensagemErroEnvio(r.erro) });
    }
  }

  const enviando = estado.tipo === "enviando";
  return (
    <View style={styles.caixa}>
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ disabled: enviando }}
        disabled={enviando}
        onPress={escolherEEnviar}
        style={({ pressed }) => [
          styles.botao,
          variante === "secundario" && styles.botaoSecundario,
          pressed &&
            (variante === "primario"
              ? { backgroundColor: tema.cor["destaque-pressionado"] }
              : { backgroundColor: tema.cor["destaque-suave"] }),
          enviando && styles.desligado,
        ]}
      >
        <Text style={[styles.botaoTexto, variante === "secundario" && styles.botaoTextoSecundario, enviando && styles.botaoTextoDesligado]}>Enviar arquivo FIT</Text>
      </Pressable>
      {enviando && (
        <View style={styles.linha}>
          <ActivityIndicator color={tema.cor.destaque} />
          <Text style={styles.texto}>Enviando...</Text>
        </View>
      )}
      {estado.tipo === "sucesso" && <Text style={styles.sucesso}>{estado.mensagem}</Text>}
      {estado.tipo === "erro" && <Text style={styles.erro}>{estado.mensagem}</Text>}
    </View>
  );
}

function criarEstilos({ cor }: Tema) {
  return StyleSheet.create({
    caixa: { marginBottom: espaco[4], gap: espaco[2] },
    botao: {
      alignSelf: "flex-start",
      minHeight: tamanho.botaoAltura,
      justifyContent: "center",
      paddingHorizontal: espaco[4],
      borderRadius: raio.medio,
      backgroundColor: cor.destaque,
    },
    botaoSecundario: { backgroundColor: cor.superficie, borderWidth: borda.fina, borderColor: cor["borda-forte"] },
    botaoTextoSecundario: { color: cor.destaque },
    desligado: { backgroundColor: cor["superficie-2"], borderWidth: 0 },
    botaoTexto: { ...fonte.botao, color: cor["sobre-destaque"] },
    botaoTextoDesligado: { color: cor["texto-desligado"] },
    linha: { flexDirection: "row", alignItems: "center", gap: espaco[2] },
    texto: { ...fonte.corpo, color: cor["texto-2"] },
    sucesso: { ...fonte.corpo, color: cor.sucesso },
    erro: { ...fonte.corpo, color: cor.erro },
  });
}
