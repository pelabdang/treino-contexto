// Tela "Entrar" (#502, spec docs/design/telas/entrar.md). E-mail e senha; sem cadastro, sem "lembrar de mim". Palavras simples:
// nada de "autenticação", "sessão" ou "token". A faixa de 401 é a mesma para e-mail que não existe, senha errada e conta desativada.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AccessibilityInfo, Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from "react-native";

import type { Entrou, Falha, ResultadoSessao } from "../sessao/api";
import { comFoco } from "../tema/foco";
import { CampoTexto, type RefCampo } from "./CampoTexto";
import { Faixa } from "./Faixa";
import { LogoPulso } from "./LogoPulso";
import { borda, espaco, fonte, larguraMargemGrande, raio, tamanho, useMargemTela, useTema, type Tema } from "../tema";

type Props = {
  /** Veio de outra tela porque o acesso deixou de valer: faixa neutra no alto. */
  expirou?: boolean;
  /** Saiu de propósito: a tela abre limpa e anuncia "Você saiu." (leitor de tela). */
  saiu?: boolean;
  aoEntrar: (email: string, senha: string) => Promise<ResultadoSessao<Entrou>>;
  /** Chamada depois de entrar com sucesso. A rota decide para onde ir: quando a sessão muda, a própria rota segue. */
  aoConcluir?: (entrou: Entrou) => void;
  /** Relógio dos testes. */
  agora?: () => number;
};

export const TEXTO_EXPIROU = "Seu acesso expirou. Entre de novo.";
export const TEXTO_CREDENCIAIS = "E-mail ou senha incorretos. Confira e tente de novo.";
export const TEXTO_REDE = "Não foi possível falar com o servidor. Confira a conexão e tente de novo.";
export const TEXTO_SERVIDOR = "Algo deu errado do nosso lado. Tente de novo mais tarde.";

/** "5 minutos", "1 minuto", "40 segundos": o tempo que a API mandou, em palavras. */
export function tempoEmPalavras(segundos: number): string {
  if (segundos < 60) return segundos === 1 ? "1 segundo" : `${segundos} segundos`;
  const min = Math.ceil(segundos / 60);
  return min === 1 ? "1 minuto" : `${min} minutos`;
}

type Aviso = { tipo: "credenciais" } | { tipo: "rede" } | { tipo: "servidor" } | { tipo: "espere"; ate: number; segundos: number };

const ESPERA_PADRAO_S = 60;

export function TelaEntrar({ expirou = false, saiu = false, aoEntrar, aoConcluir, agora = Date.now }: Props) {
  const tema = useTema();
  const margem = useMargemTela();
  const larga = useWindowDimensions().width >= larguraMargemGrande;
  const styles = useMemo(() => criarEstilos(tema, margem, larga), [tema, margem, larga]);
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [entrando, setEntrando] = useState(false);
  const [aviso, setAviso] = useState<Aviso | null>(null);
  const [, relogio] = useState(0);
  const campoSenha = useRef<RefCampo>(null);
  const campoEmail = useRef<RefCampo>(null);
  const montada = useRef(true);
  useEffect(() => {
    montada.current = true;
    return () => {
      montada.current = false;
    };
  }, []);

  useEffect(() => {
    if (saiu) AccessibilityInfo.announceForAccessibility?.("Você saiu.");
  }, [saiu]);

  // Contagem da espera do 429: o botão volta quando o tempo que a API mandou passa.
  const espera = aviso?.tipo === "espere" ? aviso : null;
  useEffect(() => {
    if (!espera) return;
    const t = setInterval(() => {
      if (agora() >= espera.ate) {
        setAviso(null);
        clearInterval(t);
      } else {
        relogio((n) => n + 1);
      }
    }, 1000);
    return () => clearInterval(t);
  }, [espera, agora]);

  const esperando = !!espera && agora() < espera.ate;
  const pronto = email.trim().length > 0 && senha.length > 0;
  const podeEnviar = pronto && !entrando && !esperando;

  const enviar = useCallback(async () => {
    if (!podeEnviar) return;
    setAviso(null);
    setEntrando(true);
    const r = await aoEntrar(email, senha);
    if (!montada.current) return;
    setEntrando(false);
    if (r.ok) {
      aoConcluir?.(r.dados);
      return;
    }
    const f: Falha = r.falha;
    if (f.motivo === "espere") {
      const segundos = f.espereS > 0 ? f.espereS : ESPERA_PADRAO_S;
      setAviso({ tipo: "espere", segundos, ate: agora() + segundos * 1000 });
    } else if (f.motivo === "rede") setAviso({ tipo: "rede" });
    else if (f.motivo === "servidor" || f.motivo === "invalido") setAviso({ tipo: "servidor" });
    else {
      // 401: a senha é apagada, o e-mail fica e o foco vai para a senha. Nos outros erros a pessoa não errou nada: o que digitou fica.
      setAviso({ tipo: "credenciais" });
      setSenha("");
      setTimeout(() => campoSenha.current?.focus(), 0);
    }
  }, [podeEnviar, aoEntrar, email, senha, aoConcluir, agora]);

  return (
    <ScrollView testID="tela-entrar" keyboardShouldPersistTaps="handled" contentContainerStyle={styles.container}>
      <View style={styles.cartao}>
        {expirou && !aviso && <Faixa tipo="info" testID="faixa-expirou" texto={TEXTO_EXPIROU} />}
        <View style={styles.logo}>
          <LogoPulso tamanho={48} />
        </View>
        <Text accessibilityRole="header" style={styles.titulo}>
          Entrar
        </Text>
        <Text style={styles.texto}>Use o e-mail e a senha do seu cadastro.</Text>
        <CampoTexto
          testID="campo-email"
          rotulo="E-mail"
          valor={email}
          aoMudar={setEmail}
          desligado={entrando}
          campoRef={campoEmail}
          autoComplete="email"
          keyboardType="email-address"
          textContentType="emailAddress"
          teclaEnter="next"
          aoEnviar={() => campoSenha.current?.focus()}
        />
        <CampoTexto
          testID="campo-senha"
          rotulo="Senha"
          valor={senha}
          aoMudar={setSenha}
          secreto
          desligado={entrando}
          campoRef={campoSenha}
          autoComplete="current-password"
          textContentType="password"
          teclaEnter="done"
          aoEnviar={enviar}
        />
        {aviso?.tipo === "credenciais" && <Faixa tipo="erro" testID="faixa-erro" texto={TEXTO_CREDENCIAIS} />}
        {aviso?.tipo === "rede" && <Faixa tipo="erro" testID="faixa-erro" texto={TEXTO_REDE} />}
        {aviso?.tipo === "servidor" && <Faixa tipo="erro" testID="faixa-erro" texto={TEXTO_SERVIDOR} />}
        {aviso?.tipo === "espere" && (
          <Faixa tipo="info" testID="faixa-espere" texto={`Muitas tentativas. Espere ${tempoEmPalavras(aviso.segundos)} e tente de novo.`} />
        )}
        <Pressable
          testID="botao-entrar"
          accessibilityRole="button"
          accessibilityState={{ disabled: !podeEnviar, busy: entrando }}
          disabled={!podeEnviar}
          onPress={enviar}
          style={podeEnviar ? comFoco(styles.botao, styles.foco) : [styles.botao, styles.botaoDesligado]}
        >
          <Text style={[styles.botaoTexto, !podeEnviar && styles.botaoTextoDesligado]}>{entrando ? "Entrando..." : "Entrar"}</Text>
        </Pressable>
        <Text style={styles.texto}>Esqueceu a senha? Fale com quem convidou você para o piloto: ele cria uma senha nova para você.</Text>
      </View>
    </ScrollView>
  );
}

function criarEstilos({ cor }: Tema, margem: number, larga: boolean) {
  return StyleSheet.create({
    container: { flexGrow: 1, padding: margem, paddingTop: larga ? espaco[6] : margem },
    // Computador: cartão de até 420, centrado na horizontal e no alto da área (com o teclado aberto o botão precisa ficar à vista).
    cartao: {
      width: "100%",
      maxWidth: 420,
      alignSelf: larga ? "center" : "stretch",
      gap: espaco[3],
      ...(larga ? { padding: espaco[5], backgroundColor: cor.superficie, borderWidth: borda.fina, borderColor: cor.borda, borderRadius: raio.cartao } : {}),
    },
    logo: { alignItems: "flex-start" },
    titulo: { ...fonte["titulo-tela"], color: cor.texto },
    texto: { ...fonte.corpo, color: cor["texto-2"] },
    botao: { minHeight: tamanho.botaoAltura, alignItems: "center", justifyContent: "center", borderRadius: raio.botao, backgroundColor: cor.botao, paddingHorizontal: espaco[4] },
    botaoDesligado: { backgroundColor: cor["superficie-2"] },
    botaoTexto: { ...fonte.botao, color: cor["sobre-botao"] },
    botaoTextoDesligado: { color: cor["texto-desligado"] },
    foco: { outlineWidth: borda.foco, outlineStyle: "solid", outlineColor: cor.foco, outlineOffset: 2 },
  });
}
