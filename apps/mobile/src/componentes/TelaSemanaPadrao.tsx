// Tela da semana-padrão (#268). Spec: docs/design/telas/semana-padrao.md. Contrato: ADR 0011, itens 9 e 10.
// O app não conta nem decide nada além do formulário: "treinos reclassificados" e o histórico vêm da API.
import { MaterialIcons } from "@expo/vector-icons";
import type { ErroApi, SemanaPadrao, SemanaPadraoItem } from "@treino/api-client";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  BackHandler,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { buscarSemanaPadrao, gravarSemanaPadrao } from "../semanaPadrao/api";
import { isoLocal, isoParaBr, isoParaBrCurto, lerDataBr, mascararData, proximaSegunda } from "../semanaPadrao/datas";
import { borda, espaco, fonte, larguraConteudoMax, raio, tamanho, useMargemTela, useTema, type Tema } from "../tema";
import { EsqueletoSemanaPadrao } from "./Esqueleto";

type Modalidade = SemanaPadraoItem["modalidade"];
type Tipo = NonNullable<SemanaPadraoItem["tipo_treino"]>;
type DefinidoPor = "atleta" | "professor";
type Item = { dia: number; modalidade: Modalidade; tipo: Tipo | null };
type Formulario = { data: string; definidoPor: DefinidoPor; itens: Item[] };
type Icone = React.ComponentProps<typeof MaterialIcons>["name"];

type Props = {
  apiUrl: string;
  atletaId: number;
  /** Mostra o botão "Voltar" quando vier. */
  aoVoltar?: () => void;
  /** Troque nos testes. Padrão: o fetch global. */
  fetchFn?: typeof fetch;
  /** Troque nos testes. Padrão: a data do aparelho. */
  hojeFn?: () => Date;
};

const DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];
const MODALIDADES: { chave: Modalidade; nome: string; icone: Icone; cor: "corrida" | "natacao" | "ciclismo" }[] = [
  { chave: "corrida", nome: "Corrida", icone: "directions-run", cor: "corrida" },
  { chave: "natacao", nome: "Natação", icone: "pool", cor: "natacao" },
  { chave: "ciclismo", nome: "Ciclismo", icone: "directions-bike", cor: "ciclismo" },
];
const TIPOS: { chave: Tipo | null; nome: string }[] = [
  { chave: null, nome: "Sem tipo" },
  { chave: "leve", nome: "Leve" },
  { chave: "moderado", nome: "Moderado" },
  { chave: "longo", nome: "Longo" },
  { chave: "intervalado", nome: "Intervalado" },
  { chave: "fartlek", nome: "Fartlek" },
];
const modalidadeDe = (m: Modalidade) => MODALIDADES.find((x) => x.chave === m)!;
const tipoNome = (t: Tipo | null) => TIPOS.find((x) => x.chave === t)!.nome;
const diaMinusculo = (dia: number) => DIAS[dia - 1].toLowerCase();

type Carga =
  | { tipo: "carregando" }
  | { tipo: "ok"; dados: SemanaPadrao }
  | { tipo: "erro"; erro: ErroApi };

type Aviso = { tipo: "salvo" | "info" | "erro"; texto: string; apoio?: string };
type Folha = { tipo: "tipo"; dia: number; modalidade: Modalidade } | { tipo: "modalidade"; dia: number } | null;
type Dialogo = { tipo: "sair" } | { tipo: "copiar"; desde: string } | null;

function mensagemErroCarga(erro: ErroApi): string {
  switch (erro.tipo) {
    case "nao_encontrado":
      return "Atleta não encontrado";
    case "rede":
      return "Não foi possível falar com o servidor";
    default:
      return "Não foi possível carregar a semana-padrão. Tente de novo mais tarde.";
  }
}

function mensagemErroSalvar(erro: ErroApi): string {
  switch (erro.tipo) {
    case "nao_encontrado":
      return "Atleta não encontrado.";
    case "rede":
      return "Não foi possível falar com o servidor. Suas mudanças continuam aqui. Tente salvar de novo.";
    case "validacao":
      return "Algum dado da semana não foi aceito. Confira a data e os treinos de cada dia e tente de novo.";
    default:
      return "Não foi possível salvar. Tente de novo mais tarde.";
  }
}

function reclassificados(n: number): string {
  if (n === 0) return "Nenhum treino mudou de tipo.";
  if (n === 1) return "1 treino reclassificado.";
  return `${n} treinos reclassificados.`;
}

function textoDeSalvo(n: number, iso: string, hojeIso: string, encerrado: boolean): Aviso {
  const curto = isoParaBrCurto(iso);
  const apoio = `Treinos anteriores a ${curto} não foram alterados.`;
  if (encerrado) return { tipo: "salvo", texto: `Plano encerrado a partir de ${curto}. ${reclassificados(n)}`, apoio };
  if (iso > hojeIso) {
    return { tipo: "salvo", texto: `Semana salva. Ela passa a valer em ${curto}; nenhum treino muda até lá.`, apoio };
  }
  return { tipo: "salvo", texto: `Semana salva. ${reclassificados(n)}`, apoio };
}

const resumoDia = (n: number) => (n === 0 ? "Sem treino" : n === 1 ? "1 treino" : `${n} treinos`);

function itensDaApi(itens: SemanaPadraoItem[]): Item[] {
  return itens.map((i) => ({ dia: i.dia_semana, modalidade: i.modalidade, tipo: i.tipo_treino }));
}

/** Chave estável para saber se o formulário mudou (a ordem dos itens não conta). */
function chave(f: Formulario): string {
  const itens = [...f.itens].sort((a, b) => a.dia - b.dia || a.modalidade.localeCompare(b.modalidade));
  return JSON.stringify({ d: f.data, q: f.definidoPor, i: itens });
}

export function TelaSemanaPadrao({ apiUrl, atletaId, aoVoltar, fetchFn, hojeFn }: Props) {
  const tema = useTema();
  const margem = useMargemTela();
  const styles = useMemo(() => criarEstilos(tema, margem), [tema, margem]);
  const opcoes = useMemo(() => ({ baseUrl: apiUrl, fetch: fetchFn }), [apiUrl, fetchFn]);
  const [hoje] = useState(() => (hojeFn ? hojeFn() : new Date()));
  const hojeIso = isoLocal(hoje);

  const [carga, setCarga] = useState<Carga>({ tipo: "carregando" });
  const [tentativa, setTentativa] = useState(0);
  const [form, setForm] = useState<Formulario>({ data: isoParaBr(hojeIso), definidoPor: "atleta", itens: [] });
  const [base, setBase] = useState<string>("");
  const [montando, setMontando] = useState(false);
  const [aviso, setAviso] = useState<Aviso | null>(null);
  const [erroData, setErroData] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [folha, setFolha] = useState<Folha>(null);
  const [dialogo, setDialogo] = useState<Dialogo>(null);
  const campoData = useRef<React.ComponentRef<typeof TextInput>>(null);

  useEffect(() => {
    let ativo = true;
    buscarSemanaPadrao(atletaId, undefined, opcoes).then((r) => {
      if (!ativo) return;
      if (!r.ok) return setCarga({ tipo: "erro", erro: r.erro });
      const inicial: Formulario = {
        data: isoParaBr(hojeIso),
        definidoPor: r.dados.vigente?.definido_por ?? "atleta",
        itens: r.dados.vigente ? itensDaApi(r.dados.vigente.itens) : [],
      };
      setForm(inicial);
      setBase(chave(inicial));
      setCarga({ tipo: "ok", dados: r.dados });
    });
    return () => {
      ativo = false;
    };
  }, [atletaId, opcoes, hojeIso, tentativa]);

  const tentarDeNovo = () => {
    setCarga({ tipo: "carregando" });
    setTentativa((n) => n + 1);
  };

  const mudou = carga.tipo === "ok" && chave(form) !== base;

  // Mudança no formulário apaga o aviso anterior (ele fala do que foi salvo, não do que se está editando).
  const editar = (f: (atual: Formulario) => Formulario) => {
    setForm(f);
    setAviso(null);
  };

  const pedirVoltar = () => {
    if (mudou) setDialogo({ tipo: "sair" });
    else aoVoltar?.();
  };

  // Botão voltar do Android e fechar a aba na web: avisam das mudanças não salvas.
  useEffect(() => {
    const sub = BackHandler.addEventListener("hardwareBackPress", () => {
      if (!mudou) return false;
      setDialogo({ tipo: "sair" });
      return true;
    });
    return () => sub.remove();
  }, [mudou]);
  useEffect(() => {
    if (Platform.OS !== "web" || !mudou || typeof window === "undefined") return;
    const aviso = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", aviso);
    return () => window.removeEventListener("beforeunload", aviso);
  }, [mudou]);

  const leitura = lerDataBr(form.data);
  const dataIso = leitura.tipo === "ok" ? leitura.iso : null;
  const vigencias = carga.tipo === "ok" ? carga.dados.vigencias : [];
  const temVigente = carga.tipo === "ok" && carga.dados.vigente != null;
  const colide = dataIso !== null && vigencias.some((v) => v.vigente_desde === dataIso);
  const futura = dataIso !== null && dataIso > hojeIso;
  const semItens = form.itens.length === 0;

  const motivoDesligado: string | null = !mudou
    ? "Nada mudou ainda."
    : semItens && !temVigente
      ? "Adicione pelo menos um treino."
      : null;

  const salvar = async () => {
    if (salvando || motivoDesligado) return;
    if (leitura.tipo !== "ok") {
      setErroData(
        leitura.tipo === "vazia"
          ? "Digite a data em que a semana começa a valer."
          : "Digite uma data que exista, como 02/03/2026.",
      );
      campoData.current?.focus();
      return;
    }
    setErroData(null);
    setAviso(null);
    setSalvando(true);
    const iso = leitura.iso;
    const r = await gravarSemanaPadrao(
      atletaId,
      {
        vigente_desde: iso,
        definido_por: form.definidoPor,
        itens: form.itens.map((i) => ({ dia_semana: i.dia, modalidade: i.modalidade, tipo_treino: i.tipo })),
      },
      opcoes,
    );
    if (!r.ok) {
      setSalvando(false);
      setAviso({ tipo: "erro", texto: mensagemErroSalvar(r.erro) });
      return;
    }
    // A tela passa a mostrar o que a API devolveu (inclusive a ordem dos itens).
    const gravado: Formulario = {
      data: isoParaBr(r.dados.vigente_desde),
      definidoPor: r.dados.definido_por,
      itens: itensDaApi(r.dados.itens),
    };
    setForm(gravado);
    setBase(chave(gravado));
    setAviso(textoDeSalvo(r.dados.atividades_reaplicadas, iso, hojeIso, r.dados.itens.length === 0));
    setSalvando(false);
    // Atualiza o histórico e a vigente sem esconder o que está na tela.
    const nova = await buscarSemanaPadrao(atletaId, undefined, opcoes);
    if (nova.ok) setCarga({ tipo: "ok", dados: nova.dados });
  };

  const copiar = async (desde: string) => {
    setDialogo(null);
    const r = await buscarSemanaPadrao(atletaId, desde, opcoes);
    if (!r.ok || !r.dados.vigente) {
      setAviso({ tipo: "erro", texto: "Não foi possível copiar essa semana. Tente de novo." });
      return;
    }
    const v = r.dados.vigente;
    setForm((f) => ({ ...f, definidoPor: v.definido_por, itens: itensDaApi(v.itens) }));
    setAviso({
      tipo: "info",
      texto: `Semana de ${isoParaBrCurto(desde)} copiada. Salvar cria uma semana nova a partir de ${
        dataIso ? isoParaBrCurto(dataIso) : "a data escolhida"
      }.`,
    });
  };

  const tocarVigencia = (desde: string) => {
    if (mudou) setDialogo({ tipo: "copiar", desde });
    else void copiar(desde);
  };

  const adicionar = (dia: number, modalidade: Modalidade) => {
    editar((f) => ({ ...f, itens: [...f.itens, { dia, modalidade, tipo: null }] }));
    setFolha(null);
  };
  const remover = (dia: number, modalidade: Modalidade) =>
    editar((f) => ({ ...f, itens: f.itens.filter((i) => !(i.dia === dia && i.modalidade === modalidade)) }));
  const mudarTipo = (dia: number, modalidade: Modalidade, tipo: Tipo | null) => {
    editar((f) => ({
      ...f,
      itens: f.itens.map((i) => (i.dia === dia && i.modalidade === modalidade ? { ...i, tipo } : i)),
    }));
    setFolha(null);
  };
  const mudarData = (texto: string) => {
    setErroData(null);
    editar((f) => ({ ...f, data: mascararData(texto) }));
  };

  const vazio = carga.tipo === "ok" && !carga.dados.vigente && carga.dados.vigencias.length === 0 && !montando;
  const mostrarForm = carga.tipo === "ok" && !vazio;
  const encerra = mostrarForm && semItens && temVigente && mudou;

  return (
    <View style={styles.tela}>
      <ScrollView testID="rolagem-tela" contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        {aoVoltar && (
          <Pressable accessibilityRole="button" accessibilityLabel="Voltar" onPress={pedirVoltar} style={styles.voltar}>
            <MaterialIcons name="arrow-back" size={tamanho.iconeMedio} color={tema.cor.destaque} />
            <Text style={styles.voltarTexto}>Voltar</Text>
          </Pressable>
        )}
        <Text accessibilityRole="header" style={styles.titulo}>
          Semana-padrão
        </Text>
        {!vazio && carga.tipo !== "erro" && <Text style={styles.subtitulo}>O que você costuma treinar em cada dia</Text>}

        {carga.tipo === "carregando" && (
          <View>
            <Text accessibilityLiveRegion="polite" style={styles.texto}>
              Carregando a semana-padrão...
            </Text>
            <EsqueletoSemanaPadrao />
          </View>
        )}

        {carga.tipo === "erro" && (
          <View testID="estado-erro" style={styles.estado}>
            <MaterialIcons
              name={carga.erro.tipo === "rede" ? "wifi-off" : "error-outline"}
              size={tamanho.iconeEstado}
              color={tema.cor.erro}
              accessible={false}
            />
            <Text accessibilityRole="alert" style={styles.erro}>
              {mensagemErroCarga(carga.erro)}
            </Text>
            {carga.erro.tipo === "rede" && (
              <Pressable accessibilityRole="button" onPress={tentarDeNovo} style={styles.botaoPrimario}>
                <Text style={styles.botaoPrimarioTexto}>Tentar de novo</Text>
              </Pressable>
            )}
          </View>
        )}

        {vazio && (
          <View testID="estado-vazio" style={styles.estado}>
            <MaterialIcons name="event-note" size={tamanho.iconeEstado} color={tema.cor["texto-2"]} accessible={false} />
            <Text accessibilityRole="header" style={styles.estadoTitulo}>
              Você ainda não definiu sua semana-padrão
            </Text>
            <Text style={styles.estadoTexto}>
              Diga que treino você costuma fazer em cada dia. O app usa isso para comparar cada treino com os do mesmo
              tipo.
            </Text>
            <Pressable accessibilityRole="button" onPress={() => setMontando(true)} style={styles.botaoPrimario}>
              <Text style={styles.botaoPrimarioTexto}>Montar minha semana</Text>
            </Pressable>
          </View>
        )}

        {mostrarForm && (
          <View testID="formulario">
            <View style={styles.cartao}>
              <Text style={styles.cartaoTitulo}>Vale a partir de</Text>
              <TextInput
                ref={campoData}
                testID="campo-data"
                accessibilityLabel="Vale a partir de"
                value={form.data}
                onChangeText={mudarData}
                editable={!salvando}
                keyboardType="number-pad"
                inputMode="numeric"
                maxLength={10}
                placeholder="dd/mm/aaaa"
                placeholderTextColor={tema.cor["texto-2"]}
                style={[styles.campo, erroData ? { borderColor: tema.cor.erro } : null]}
              />
              {erroData && (
                <View style={styles.linhaAviso}>
                  <MaterialIcons name="error-outline" size={tamanho.iconeMedio} color={tema.cor.erro} accessible={false} />
                  <Text accessibilityRole="alert" style={[styles.legenda, { color: tema.cor.erro, flex: 1 }]}>
                    {erroData}
                  </Text>
                </View>
              )}
              <View style={styles.atalhos}>
                <Pressable
                  accessibilityRole="button"
                  disabled={salvando}
                  onPress={() => mudarData(isoParaBr(hojeIso))}
                  style={styles.botaoSecundario}
                >
                  <Text style={styles.botaoSecundarioTexto}>Hoje</Text>
                </Pressable>
                <Pressable
                  accessibilityRole="button"
                  disabled={salvando}
                  onPress={() => mudarData(isoParaBr(isoLocal(proximaSegunda(hoje))))}
                  style={styles.botaoSecundario}
                >
                  <Text style={styles.botaoSecundarioTexto}>Próxima segunda</Text>
                </Pressable>
              </View>
              <Text style={styles.legenda}>Os treinos antes desta data não mudam.</Text>
              {colide && (
                <View testID="aviso-data-existe" style={styles.linhaAviso}>
                  <MaterialIcons name="warning-amber" size={tamanho.iconeMedio} color={tema.cor.alerta} accessible={false} />
                  <Text style={[styles.legenda, { color: tema.cor.alerta, flex: 1 }]}>
                    Já existe uma semana que vale desde esta data. Salvar vai substituí-la.
                  </Text>
                </View>
              )}
              {futura && dataIso && (
                <View testID="aviso-data-futura" style={styles.linhaAviso}>
                  <MaterialIcons name="info-outline" size={tamanho.iconeMedio} color={tema.cor["texto-2"]} accessible={false} />
                  <Text style={[styles.legenda, { flex: 1 }]}>
                    Esta semana começa a valer em {isoParaBrCurto(dataIso)}. Até lá, nada muda.
                  </Text>
                </View>
              )}
            </View>

            <View style={styles.cartao}>
              <Text style={styles.cartaoTitulo}>Quem definiu</Text>
              <View accessibilityRole="radiogroup" accessibilityLabel="Quem definiu" style={styles.radios}>
                {(
                  [
                    ["atleta", "Eu"],
                    ["professor", "Treinador"],
                  ] as const
                ).map(([valor, nome]) => {
                  const marcado = form.definidoPor === valor;
                  return (
                    <Pressable
                      key={valor}
                      accessibilityRole="radio"
                      accessibilityState={{ checked: marcado, disabled: salvando }}
                      accessibilityLabel={nome}
                      disabled={salvando}
                      onPress={() => editar((f) => ({ ...f, definidoPor: valor }))}
                      style={[styles.radio, marcado ? styles.radioMarcado : styles.radioLivre]}
                    >
                      <MaterialIcons
                        name={marcado ? "radio-button-checked" : "radio-button-unchecked"}
                        size={tamanho.iconeGrande}
                        color={marcado ? tema.cor.destaque : tema.cor["texto-2"]}
                        accessible={false}
                      />
                      <Text style={styles.radioTexto}>{nome}</Text>
                    </Pressable>
                  );
                })}
              </View>
              <Text style={styles.legenda}>Só registra de quem é o plano. O app ainda não tem login.</Text>
            </View>

            <View style={styles.cartao}>
              <Text style={styles.cartaoTitulo}>Treinos de cada dia</Text>
              {DIAS.map((nome, idx) => {
                const dia = idx + 1;
                const doDia = form.itens.filter((i) => i.dia === dia);
                const faltam = MODALIDADES.filter((m) => !doDia.some((i) => i.modalidade === m.chave));
                return (
                  <View key={dia} testID={`dia-${dia}`} style={[styles.dia, idx > 0 && styles.diaDivisoria]}>
                    <View style={styles.diaCabecalho}>
                      <Text accessibilityRole="header" style={styles.diaNome}>
                        {nome}
                      </Text>
                      <Text style={styles.diaResumo}>{resumoDia(doDia.length)}</Text>
                    </View>
                    {doDia.map((item) => {
                      const mod = modalidadeDe(item.modalidade);
                      return (
                        <View
                          key={item.modalidade}
                          accessible
                          accessibilityLabel={`${nome}, ${mod.nome.toLowerCase()}, ${
                            item.tipo ? `tipo ${tipoNome(item.tipo).toLowerCase()}` : "sem tipo"
                          }`}
                          style={styles.item}
                        >
                          <View testID={`chip-${dia}-${item.modalidade}`} style={styles.chip}>
                            <MaterialIcons name={mod.icone} size={tamanho.iconePequeno} color={tema.cor[mod.cor]} accessible={false} />
                            <Text style={styles.chipTexto}>{mod.nome}</Text>
                          </View>
                          <Pressable
                            testID={`tipo-${dia}-${item.modalidade}`}
                            accessibilityRole="button"
                            accessibilityLabel={`Tipo do treino de ${mod.nome.toLowerCase()} ${
                              dia >= 6 ? "no" : "na"
                            } ${diaMinusculo(dia)}, ${tipoNome(item.tipo).toLowerCase()}, botão`}
                            disabled={salvando}
                            onPress={() => setFolha({ tipo: "tipo", dia, modalidade: item.modalidade })}
                            style={styles.seletor}
                          >
                            <Text style={styles.seletorTexto}>{tipoNome(item.tipo)}</Text>
                            <MaterialIcons name="expand-more" size={tamanho.iconeGrande} color={tema.cor["texto-2"]} accessible={false} />
                          </Pressable>
                          <Pressable
                            testID={`remover-${dia}-${item.modalidade}`}
                            accessibilityRole="button"
                            accessibilityLabel={`Remover ${mod.nome.toLowerCase()} de ${diaMinusculo(dia)}`}
                            disabled={salvando}
                            onPress={() => remover(dia, item.modalidade)}
                            style={styles.remover}
                          >
                            <MaterialIcons name="delete-outline" size={tamanho.iconeGrande} color={tema.cor.erro} accessible={false} />
                          </Pressable>
                        </View>
                      );
                    })}
                    {faltam.length > 0 && (
                      <Pressable
                        testID={`adicionar-${dia}`}
                        accessibilityRole="button"
                        accessibilityLabel={`Adicionar treino ${dia >= 6 ? "no" : "na"} ${diaMinusculo(dia)}`}
                        disabled={salvando}
                        onPress={() => setFolha({ tipo: "modalidade", dia })}
                        style={styles.adicionar}
                      >
                        <MaterialIcons name="add" size={tamanho.iconeMedio} color={tema.cor.destaque} accessible={false} />
                        <Text style={styles.adicionarTexto}>Adicionar treino</Text>
                      </Pressable>
                    )}
                  </View>
                );
              })}
            </View>

            {vigencias.length > 0 && (
              <View testID="historico" style={styles.cartao}>
                <Text style={styles.cartaoTitulo}>Semanas anteriores</Text>
                {vigencias.map((v) => {
                  const emVigor = carga.tipo === "ok" && carga.dados.vigente?.vigente_desde === v.vigente_desde;
                  const aindaNao = v.vigente_desde > hojeIso;
                  const quem = v.definido_por === "atleta" ? "Eu" : "Treinador";
                  const n = v.total_itens;
                  return (
                    <Pressable
                      key={v.vigente_desde}
                      testID={`vigencia-${v.vigente_desde}`}
                      accessibilityRole="button"
                      accessibilityLabel={`Semana desde ${isoParaBrCurto(v.vigente_desde)}${
                        emVigor ? ", em vigor" : aindaNao ? ", ainda não começou" : ""
                      }, ${quem}, ${n} ${n === 1 ? "treino" : "treinos"} por semana. Copiar para o formulário`}
                      disabled={salvando}
                      onPress={() => tocarVigencia(v.vigente_desde)}
                      style={({ pressed }) => [styles.vigencia, pressed && { backgroundColor: tema.cor["destaque-suave"] }]}
                    >
                      <View style={{ flex: 1 }}>
                        <View style={styles.vigenciaTopo}>
                          <Text style={styles.vigenciaData}>Desde {isoParaBrCurto(v.vigente_desde)}</Text>
                          {emVigor && <Text style={styles.selo}>Em vigor</Text>}
                          {!emVigor && aindaNao && <Text style={styles.selo}>Ainda não começou</Text>}
                        </View>
                        <Text style={styles.texto}>
                          {quem} · {n} {n === 1 ? "treino" : "treinos"} por semana
                        </Text>
                      </View>
                      <MaterialIcons name="chevron-right" size={tamanho.iconeGrande} color={tema.cor["texto-2"]} accessible={false} />
                    </Pressable>
                  );
                })}
              </View>
            )}
          </View>
        )}
      </ScrollView>

      {mostrarForm && (
        <View testID="barra-salvar" style={styles.barra}>
          <View style={styles.barraInterna}>
            {aviso && (
              <View
                testID="aviso"
                accessibilityRole={aviso.tipo === "erro" ? "alert" : undefined}
                accessibilityLiveRegion="polite"
                style={[
                  styles.aviso,
                  { backgroundColor: aviso.tipo === "erro" ? tema.cor["erro-suave"] : aviso.tipo === "salvo" ? tema.cor["sucesso-suave"] : tema.cor["destaque-suave"] },
                ]}
              >
                <MaterialIcons
                  name={aviso.tipo === "erro" ? "error-outline" : aviso.tipo === "salvo" ? "check-circle" : "info-outline"}
                  size={tamanho.iconeMedio}
                  color={aviso.tipo === "erro" ? tema.cor.erro : aviso.tipo === "salvo" ? tema.cor.sucesso : tema.cor.destaque}
                  accessible={false}
                />
                <View style={{ flex: 1 }}>
                  <Text style={styles.avisoTexto}>{aviso.texto}</Text>
                  {aviso.apoio && <Text style={styles.legenda}>{aviso.apoio}</Text>}
                </View>
              </View>
            )}
            {!aviso && motivoDesligado && <Text style={styles.legenda}>{motivoDesligado}</Text>}
            {!aviso && encerra && (
              <View style={styles.linhaAviso}>
                <MaterialIcons name="warning-amber" size={tamanho.iconeMedio} color={tema.cor.alerta} accessible={false} />
                <Text style={[styles.legenda, { color: tema.cor.alerta, flex: 1 }]}>
                  Sem nenhum treino, o plano acaba em {dataIso ? isoParaBrCurto(dataIso) : "a data escolhida"} e o app deixa
                  de usá-lo para classificar os treinos.
                </Text>
              </View>
            )}
            <Pressable
              testID="salvar"
              accessibilityRole="button"
              accessibilityState={{ disabled: !!motivoDesligado || salvando }}
              disabled={!!motivoDesligado || salvando}
              onPress={salvar}
              style={({ pressed }) => [
                styles.salvar,
                motivoDesligado || salvando
                  ? { backgroundColor: tema.cor["superficie-2"] }
                  : { backgroundColor: pressed ? tema.cor["destaque-pressionado"] : tema.cor.destaque },
              ]}
            >
              <Text
                style={[
                  styles.botaoPrimarioTexto,
                  { color: motivoDesligado || salvando ? tema.cor["texto-desligado"] : tema.cor["sobre-destaque"] },
                ]}
              >
                {salvando ? "Salvando..." : "Salvar semana"}
              </Text>
            </Pressable>
          </View>
        </View>
      )}

      <Opcoes
        aberta={folha?.tipo === "tipo"}
        titulo="Tipo do treino"
        apoio="Sem tipo: o app não define o tipo desse treino pela semana."
        fechar={() => setFolha(null)}
        styles={styles}
        tema={tema}
      >
        {folha?.tipo === "tipo" &&
          TIPOS.map((t) => {
            const atual = form.itens.find((i) => i.dia === folha.dia && i.modalidade === folha.modalidade)?.tipo ?? null;
            const marcado = atual === t.chave;
            return (
              <Pressable
                key={t.nome}
                accessibilityRole="radio"
                accessibilityState={{ checked: marcado }}
                accessibilityLabel={t.nome}
                onPress={() => mudarTipo(folha.dia, folha.modalidade, t.chave)}
                style={styles.opcao}
              >
                <MaterialIcons
                  name={marcado ? "radio-button-checked" : "radio-button-unchecked"}
                  size={tamanho.iconeGrande}
                  color={marcado ? tema.cor.destaque : tema.cor["texto-2"]}
                  accessible={false}
                />
                <Text style={styles.opcaoTexto}>{t.nome}</Text>
              </Pressable>
            );
          })}
      </Opcoes>

      <Opcoes aberta={folha?.tipo === "modalidade"} titulo="Qual modalidade?" fechar={() => setFolha(null)} styles={styles} tema={tema}>
        {folha?.tipo === "modalidade" &&
          MODALIDADES.filter((m) => !form.itens.some((i) => i.dia === folha.dia && i.modalidade === m.chave)).map((m) => (
            <Pressable
              key={m.chave}
              accessibilityRole="button"
              accessibilityLabel={m.nome}
              onPress={() => adicionar(folha.dia, m.chave)}
              style={styles.opcao}
            >
              <MaterialIcons name={m.icone} size={tamanho.iconeGrande} color={tema.cor[m.cor]} accessible={false} />
              <Text style={styles.opcaoTexto}>{m.nome}</Text>
            </Pressable>
          ))}
      </Opcoes>

      <Modal visible={dialogo !== null} transparent animationType="fade" onRequestClose={() => setDialogo(null)}>
        <View style={styles.fundoModal}>
          <View accessibilityViewIsModal style={styles.dialogo}>
            <Text accessibilityRole="header" style={styles.estadoTitulo}>
              {dialogo?.tipo === "copiar" ? "Copiar esta semana?" : "Sair sem salvar?"}
            </Text>
            <Text style={styles.texto}>
              {dialogo?.tipo === "copiar"
                ? `As mudanças que você fez serão trocadas pela semana de ${isoParaBrCurto(dialogo.desde)}.`
                : "As mudanças desta semana serão perdidas."}
            </Text>
            <Pressable accessibilityRole="button" onPress={() => setDialogo(null)} style={styles.botaoPrimario}>
              <Text style={styles.botaoPrimarioTexto}>Continuar editando</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              onPress={() => {
                const d = dialogo;
                if (d?.tipo === "copiar") void copiar(d.desde);
                else {
                  setDialogo(null);
                  aoVoltar?.();
                }
              }}
              style={styles.botaoSecundario}
            >
              <Text style={styles.botaoSecundarioTexto}>{dialogo?.tipo === "copiar" ? "Copiar" : "Sair sem salvar"}</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </View>
  );
}

/** Folha que sobe do pé com uma lista de opções (Esc ou voltar fecham). */
function Opcoes({
  aberta,
  titulo,
  apoio,
  fechar,
  children,
  styles,
  tema,
}: {
  aberta: boolean;
  titulo: string;
  apoio?: string;
  fechar: () => void;
  children: ReactNode;
  styles: Estilos;
  tema: Tema;
}) {
  // Esc fecha na web (o Modal do react-native-web também o faz; fechar duas vezes é inofensivo).
  useEffect(() => {
    if (!aberta || Platform.OS !== "web" || typeof document === "undefined") return;
    const tecla = (e: KeyboardEvent) => {
      if (e.key === "Escape") fechar();
    };
    document.addEventListener("keydown", tecla);
    return () => document.removeEventListener("keydown", tecla);
  }, [aberta, fechar]);
  return (
    <Modal visible={aberta} transparent animationType="slide" onRequestClose={fechar}>
      <Pressable accessibilityLabel="Fechar" style={styles.fundoModal} onPress={fechar}>
        <Pressable accessibilityViewIsModal style={styles.folha} onPress={() => {}}>
          <View style={styles.folhaTopo}>
            <Text accessibilityRole="header" style={styles.cartaoTitulo}>
              {titulo}
            </Text>
            <Pressable accessibilityRole="button" accessibilityLabel="Fechar" onPress={fechar} style={styles.fechar}>
              <MaterialIcons name="close" size={tamanho.iconeGrande} color={tema.cor["texto-2"]} accessible={false} />
            </Pressable>
          </View>
          {apoio && <Text style={styles.legenda}>{apoio}</Text>}
          {children}
        </Pressable>
      </Pressable>
    </Modal>
  );
}

type Estilos = ReturnType<typeof criarEstilos>;

function criarEstilos({ cor }: Tema, margem: number = espaco[4]) {
  return StyleSheet.create({
    tela: { flex: 1, backgroundColor: cor.fundo },
    container: {
      padding: margem,
      paddingBottom: espaco[6],
      flexGrow: 1,
      width: "100%",
      maxWidth: larguraConteudoMax + 2 * margem,
      alignSelf: "center",
    },
    voltar: {
      flexDirection: "row",
      alignItems: "center",
      alignSelf: "flex-start",
      gap: espaco[1],
      minHeight: tamanho.alvoMinimo,
      paddingRight: espaco[2],
    },
    voltarTexto: { ...fonte.botao, color: cor.destaque },
    titulo: { ...fonte["titulo-tela"], color: cor.texto },
    subtitulo: { ...fonte.corpo, color: cor["texto-2"], marginTop: espaco[1] },
    texto: { ...fonte.corpo, color: cor["texto-2"] },
    legenda: { ...fonte.legenda, color: cor["texto-2"] },
    erro: { ...fonte.corpo, color: cor.erro, textAlign: "center", marginBottom: espaco[3] },
    estado: { alignItems: "center", paddingVertical: espaco[7], gap: espaco[2] },
    estadoTitulo: { ...fonte["titulo-secao"], color: cor.texto, textAlign: "center" },
    estadoTexto: { ...fonte.corpo, color: cor["texto-2"], textAlign: "center", marginBottom: espaco[3] },
    botaoPrimario: {
      minHeight: tamanho.botaoAltura,
      justifyContent: "center",
      alignItems: "center",
      paddingHorizontal: espaco[4],
      borderRadius: raio.medio,
      backgroundColor: cor.destaque,
    },
    botaoPrimarioTexto: { ...fonte.botao, color: cor["sobre-destaque"] },
    botaoSecundario: {
      minHeight: tamanho.alvoMinimo,
      justifyContent: "center",
      alignItems: "center",
      paddingHorizontal: espaco[4],
      borderRadius: raio.medio,
      borderWidth: borda.fina,
      borderColor: cor["borda-forte"],
    },
    botaoSecundarioTexto: { ...fonte.botao, color: cor.destaque },
    cartao: {
      marginTop: espaco[4],
      padding: espaco[4],
      gap: espaco[2],
      borderRadius: raio.grande,
      borderWidth: borda.fina,
      borderColor: cor.borda,
      backgroundColor: cor.superficie,
    },
    cartaoTitulo: { ...fonte["titulo-secao"], color: cor.texto },
    campo: {
      ...fonte.corpo,
      minHeight: tamanho.botaoAltura,
      paddingHorizontal: espaco[3],
      borderRadius: raio.medio,
      borderWidth: borda.fina,
      borderColor: cor["borda-forte"],
      color: cor.texto,
      backgroundColor: cor.superficie,
    },
    atalhos: { flexDirection: "row", flexWrap: "wrap", gap: espaco[2] },
    linhaAviso: { flexDirection: "row", alignItems: "flex-start", gap: espaco[2] },
    radios: { flexDirection: "row", gap: espaco[3] },
    radio: {
      flex: 1,
      flexDirection: "row",
      alignItems: "center",
      gap: espaco[2],
      minHeight: tamanho.botaoAltura,
      paddingHorizontal: espaco[3],
      borderRadius: raio.medio,
    },
    radioMarcado: { backgroundColor: cor["destaque-suave"], borderWidth: borda.foco, borderColor: cor.destaque },
    radioLivre: { borderWidth: borda.fina, borderColor: cor["borda-forte"] },
    radioTexto: { ...fonte.corpo, color: cor.texto },
    dia: { paddingVertical: espaco[2], gap: espaco[2] },
    diaDivisoria: { borderTopWidth: borda.fina, borderTopColor: cor.borda, paddingTop: espaco[3] },
    diaCabecalho: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
    diaNome: { ...fonte["titulo-secao"], color: cor.texto },
    diaResumo: { ...fonte.rotulo, color: cor["texto-2"] },
    item: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: espaco[2] },
    chip: {
      flexDirection: "row",
      alignItems: "center",
      gap: espaco[1],
      minHeight: tamanho.botaoAltura,
      minWidth: 100,
      paddingHorizontal: espaco[2],
    },
    chipTexto: { ...fonte.rotulo, color: cor.texto },
    seletor: {
      flex: 1,
      minWidth: 120,
      flexDirection: "row",
      alignItems: "center",
      justifyContent: "space-between",
      minHeight: tamanho.botaoAltura,
      paddingHorizontal: espaco[3],
      borderRadius: raio.medio,
      borderWidth: borda.fina,
      borderColor: cor["borda-forte"],
    },
    seletorTexto: { ...fonte.corpo, color: cor.texto },
    remover: {
      width: tamanho.alvoMinimo,
      height: tamanho.alvoMinimo,
      alignItems: "center",
      justifyContent: "center",
    },
    adicionar: {
      flexDirection: "row",
      alignItems: "center",
      alignSelf: "flex-start",
      gap: espaco[1],
      minHeight: tamanho.alvoMinimo,
      paddingRight: espaco[2],
    },
    adicionarTexto: { ...fonte.botao, color: cor.destaque },
    vigencia: {
      flexDirection: "row",
      alignItems: "center",
      minHeight: tamanho.listaLinhaAltura,
      paddingVertical: espaco[2],
      borderBottomWidth: borda.fina,
      borderBottomColor: cor.borda,
    },
    vigenciaTopo: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: espaco[2] },
    vigenciaData: { ...fonte["corpo-forte"], color: cor.texto },
    selo: {
      ...fonte.legenda,
      color: cor.destaque,
      paddingHorizontal: espaco[2],
      borderRadius: raio.pilula,
      borderWidth: borda.fina,
      borderColor: cor.destaque,
    },
    // Na web larga a barra acompanha a coluna do conteúdo (720 mais as margens), centralizada.
    barra: {
      width: "100%",
      maxWidth: larguraConteudoMax + 2 * margem,
      alignSelf: "center",
      borderTopWidth: borda.fina,
      borderTopColor: cor.borda,
      backgroundColor: cor.superficie,
    },
    barraInterna: {
      width: "100%",
      padding: margem,
      gap: espaco[2],
    },
    aviso: { flexDirection: "row", gap: espaco[2], padding: espaco[3], borderRadius: raio.medio },
    avisoTexto: { ...fonte.corpo, color: cor.texto },
    salvar: {
      minHeight: tamanho.botaoAltura,
      justifyContent: "center",
      alignItems: "center",
      borderRadius: raio.medio,
    },
    fundoModal: { flex: 1, justifyContent: "flex-end", backgroundColor: "rgba(0,0,0,0.4)" },
    folha: {
      width: "100%",
      maxWidth: larguraConteudoMax,
      alignSelf: "center",
      padding: espaco[4],
      gap: espaco[1],
      borderTopLeftRadius: raio.grande,
      borderTopRightRadius: raio.grande,
      backgroundColor: cor.superficie,
    },
    folhaTopo: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
    fechar: { width: tamanho.alvoMinimo, height: tamanho.alvoMinimo, alignItems: "center", justifyContent: "center" },
    opcao: {
      flexDirection: "row",
      alignItems: "center",
      gap: espaco[3],
      minHeight: tamanho.listaLinhaAltura,
    },
    opcaoTexto: { ...fonte.corpo, color: cor.texto },
    dialogo: {
      margin: margem,
      padding: espaco[4],
      gap: espaco[3],
      borderRadius: raio.grande,
      backgroundColor: cor.superficie,
      alignSelf: "center",
      width: "90%",
      maxWidth: 480,
      marginBottom: espaco[7],
    },
  });
}
