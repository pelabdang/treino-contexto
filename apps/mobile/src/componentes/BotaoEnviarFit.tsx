import { enviarAtividadeFit, type ArquivoFit, type ErroApi } from "@treino/api-client";
import * as DocumentPicker from "expo-document-picker";
import { useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";

type Props = {
  apiUrl: string;
  atletaId: number;
  /** Chamado depois de um envio com sucesso (201 ou 200). */
  aoEnviar?: () => void;
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

export function BotaoEnviarFit({ apiUrl, atletaId, aoEnviar, fetchFn }: Props) {
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
        style={[styles.botao, enviando && styles.desligado]}
      >
        <Text style={styles.botaoTexto}>Enviar arquivo FIT</Text>
      </Pressable>
      {enviando && (
        <View style={styles.linha}>
          <ActivityIndicator />
          <Text style={styles.texto}>Enviando...</Text>
        </View>
      )}
      {estado.tipo === "sucesso" && <Text style={styles.sucesso}>{estado.mensagem}</Text>}
      {estado.tipo === "erro" && <Text style={styles.erro}>{estado.mensagem}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  caixa: { marginBottom: 16, gap: 8 },
  botao: { alignSelf: "flex-start", paddingVertical: 10, paddingHorizontal: 16, borderRadius: 8, backgroundColor: "#1b6ca8" },
  desligado: { opacity: 0.5 },
  botaoTexto: { color: "#fff", fontWeight: "600" },
  linha: { flexDirection: "row", alignItems: "center", gap: 8 },
  texto: { fontSize: 16, color: "#444" },
  sucesso: { fontSize: 16, color: "#1b7a3a" },
  erro: { fontSize: 16, color: "#b00020" },
});
