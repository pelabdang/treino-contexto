// Navegação por abas (UX, auditoria da Lia docs/design/auditoria-ux-e-inicio-do-atleta.md): na base no celular, menu à esquerda no
// computador (a partir de 600). Atleta: Início, Treinos, Evolução, Conta. Professor: Caixa do dia, Conta. Estado em ícone e palavra;
// a aba ativa tem fundo suave além da cor; o selo da Conta é um número com texto para o leitor de tela.
import { MaterialIcons } from "@expo/vector-icons";
import { useMemo } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import type { Papel } from "../sessao/destino";
import { comFoco } from "../tema/foco";
import { borda, espaco, fonte, raio, tamanho, useTema, type Tema } from "../tema";

export type Aba = { rota: string; rotulo: string; icone: React.ComponentProps<typeof MaterialIcons>["name"] };

export const ABAS_ATLETA: Aba[] = [
  { rota: "index", rotulo: "Início", icone: "home" },
  { rota: "treinos", rotulo: "Treinos", icone: "fitness-center" },
  { rota: "evolucao", rotulo: "Evolução", icone: "show-chart" },
  { rota: "conta", rotulo: "Conta", icone: "person" },
];
export const ABAS_PROFESSOR: Aba[] = [
  { rota: "caixa-do-dia", rotulo: "Caixa do dia", icone: "inbox" },
  { rota: "conta", rotulo: "Conta", icone: "person" },
];
export const abasDoPapel = (papel: Papel): Aba[] => (papel === "professor" ? ABAS_PROFESSOR : ABAS_ATLETA);

type Props = {
  abas: Aba[];
  ativa: string;
  aoEscolher: (rota: string) => void;
  /** Menu à esquerda (computador) em vez da barra na base. */
  lateral: boolean;
  /** Selo numérico por rota (por exemplo, pedidos de consentimento na Conta). */
  selos?: Record<string, number>;
};

export function BarraDeAbas({ abas, ativa, aoEscolher, lateral, selos = {} }: Props) {
  const tema = useTema();
  const styles = useMemo(() => criarEstilos(tema, lateral), [tema, lateral]);
  return (
    <View testID={lateral ? "menu-lateral" : "barra-de-abas"} accessibilityRole="tablist" style={styles.barra}>
      {abas.map((a) => {
        const marcada = a.rota === ativa;
        const selo = selos[a.rota] ?? 0;
        return (
          <Pressable
            key={a.rota}
            testID={`aba-${a.rota}`}
            accessibilityRole="tab"
            accessibilityState={{ selected: marcada }}
            accessibilityLabel={selo > 0 ? `${a.rotulo}, ${selo} ${selo === 1 ? "pedido" : "pedidos"}` : a.rotulo}
            onPress={() => aoEscolher(a.rota)}
            style={comFoco([styles.aba, marcada && styles.abaMarcada], styles.foco)}
          >
            <View>
              <MaterialIcons name={a.icone} size={tamanho.iconeGrande} color={marcada ? tema.cor.destaque : tema.cor["texto-2"]} accessible={false} />
              {selo > 0 && (
                <View testID={`selo-${a.rota}`} style={styles.selo}>
                  <Text style={styles.seloTexto}>{selo}</Text>
                </View>
              )}
            </View>
            <Text style={[styles.rotulo, marcada && styles.rotuloMarcado]}>{a.rotulo}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

function criarEstilos({ cor }: Tema, lateral: boolean) {
  return StyleSheet.create({
    barra: lateral
      ? { width: 200, paddingVertical: espaco[4], paddingHorizontal: espaco[3], gap: espaco[1], backgroundColor: cor.superficie, borderRightWidth: borda.fina, borderRightColor: cor.borda }
      : { flexDirection: "row", backgroundColor: cor.superficie, borderTopWidth: borda.fina, borderTopColor: cor.borda },
    aba: lateral
      ? { flexDirection: "row", alignItems: "center", gap: espaco[3], minHeight: tamanho.botaoAltura, paddingHorizontal: espaco[3], borderRadius: raio.medio }
      : { flex: 1, minHeight: 56, alignItems: "center", justifyContent: "center", gap: 2, paddingVertical: espaco[1] },
    abaMarcada: { backgroundColor: cor["destaque-suave"] },
    rotulo: { ...fonte.rotulo, color: cor["texto-2"] },
    rotuloMarcado: { color: cor.destaque, fontFamily: fonte["corpo-forte"].fontFamily },
    selo: { position: "absolute", top: -4, right: -10, minWidth: 18, height: 18, borderRadius: 9, paddingHorizontal: 4, alignItems: "center", justifyContent: "center", backgroundColor: cor.destaque },
    seloTexto: { ...fonte.legenda, lineHeight: 16, color: cor["sobre-destaque"], fontFamily: fonte["corpo-forte"].fontFamily },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: -2 },
  });
}
