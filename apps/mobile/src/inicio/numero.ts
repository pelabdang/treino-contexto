// Textos do cartão "Último treino" a partir do que a API já mandou (spec v3, "Número do treino"). O app não formata pace nem calcula
// métrica: só escolhe qual texto pronto mostrar.
import type { Atividade, MetricaLinhaBase } from "@treino/api-client";

export type NumeroTreino = { valor: string; unidade: string | null; rotulo: string };

/** "4:11 min/km" -> { valor: "4:11", unidade: "min/km" }. */
function separar(texto: string): { valor: string; unidade: string | null } {
  const m = texto.match(/^(\S+)\s+(.+)$/);
  return m ? { valor: m[1], unidade: m[2] } : { valor: texto, unidade: null };
}

/** Corrida intervalada: melhor tiro (menor pace entre os blocos de esforço); outras corridas: pace médio; resto: duração. */
export function numeroDoTreino(a: Atividade): NumeroTreino {
  if (a.modalidade === "corrida" && a.tipo_treino === "intervalado") {
    const blocos = (a.esforcos?.blocos ?? []).filter((b) => b.categoria === "esforco" && b.pace && typeof b.pace_s_km === "number");
    if (blocos.length > 0) {
      const melhor = blocos.reduce((x, y) => ((y.pace_s_km as number) < (x.pace_s_km as number) ? y : x));
      return { ...separar(melhor.pace as string), rotulo: "Melhor tiro" };
    }
  }
  if (a.modalidade === "corrida" && a.pace_medio) return { ...separar(a.pace_medio), rotulo: "Pace médio" };
  return { valor: a.duracao, unidade: null, rotulo: "Duração" };
}

/** Distância, duração e FC média, só o que existe. */
export function linhaDeApoio(a: Atividade): string {
  return [a.distancia, a.duracao, a.fc_media ? `FC média ${a.fc_media} bpm` : null].filter(Boolean).join(" · ");
}

export type SeloNormal = { tipo: "dentro" | "fora" | "aprendendo"; texto: string };

const PREFERENCIA: MetricaLinhaBase["chave"][] = ["melhor_pace", "pace_medio", "fc_media"];

type EstadoNormal = "fora" | "dentro" | "aprendendo";

/** Métricas com valor, na ordem de preferência (as que a preferência não cita vêm depois, na ordem da API). */
function metricasOrdenadas(a: Atividade): MetricaLinhaBase[] {
  const lb = a.linha_base;
  if (!lb || lb.estado !== "ok") return [];
  const com = lb.metricas.filter((m) => m.estado !== "sem_valor");
  const rank = (m: MetricaLinhaBase) => {
    const i = PREFERENCIA.indexOf(m.chave);
    return i === -1 ? PREFERENCIA.length : i;
  };
  return [...com].sort((x, y) => rank(x) - rank(y));
}

/**
 * Estado do selo pela regra `normal_treino@1` ([[metricas/normal-treino]]): alguma métrica fora, o treino está fora; senão alguma dentro,
 * dentro; senão aprendendo; sem `linha_base` ok ou sem métrica com valor, `null`. É a mesma regra da lista (`normal_estado`).
 */
export function estadoDoNormal(a: Atividade): EstadoNormal | null {
  const ms = metricasOrdenadas(a);
  if (ms.some((m) => m.estado === "fora")) return "fora";
  if (ms.some((m) => m.estado === "dentro")) return "dentro";
  if (ms.some((m) => m.estado === "aprendendo")) return "aprendendo";
  return null;
}

/**
 * Selo da linha de base. O TIPO segue o `normal_estado` da lista quando ele vem (mesma conta do cartão da lista, para o mesmo treino
 * nunca mudar de selo entre telas); sem ele, a regra acima. O TEXTO vem da API: em "fora", a diferença da primeira métrica fora;
 * em "aprendendo", o texto da primeira métrica aprendendo; em "dentro", frase fixa.
 */
export function seloDoNormal(a: Atividade, normalEstado?: EstadoNormal | null): SeloNormal | null {
  const tipo = normalEstado === undefined ? estadoDoNormal(a) : normalEstado;
  if (!tipo) return null;
  const ms = metricasOrdenadas(a);
  if (tipo === "dentro") return { tipo, texto: "Dentro do seu normal" };
  if (tipo === "fora") {
    const m = ms.find((x) => x.estado === "fora");
    return { tipo, texto: `Fora do seu normal${m ? `: ${m.diferenca_texto ?? m.texto}` : ""}` };
  }
  const m = ms.find((x) => x.estado === "aprendendo");
  return { tipo, texto: m?.texto ?? "Aprendendo" };
}

/** As três primeiras linhas do texto do feedback. */
export function primeirasLinhas(texto: string, n = 3): string {
  return texto.split("\n").filter((l) => l.trim().length > 0).slice(0, n).join("\n");
}
