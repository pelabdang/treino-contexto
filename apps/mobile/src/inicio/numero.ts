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

/** Selo da linha de base: o primeiro cálculo que a API trouxe. Sem `linha_base` (ou sem valor), sem selo. */
export function seloDoNormal(a: Atividade): SeloNormal | null {
  const lb = a.linha_base;
  if (!lb || lb.estado !== "ok") return null;
  const metricas = lb.metricas.filter((m) => m.estado !== "sem_valor");
  const m = PREFERENCIA.map((c) => metricas.find((x) => x.chave === c)).find(Boolean) ?? metricas[0];
  if (!m) return null;
  if (m.estado === "dentro") return { tipo: "dentro", texto: "Dentro do seu normal" };
  if (m.estado === "fora") return { tipo: "fora", texto: `Fora do seu normal: ${m.diferenca_texto ?? m.texto}` };
  return { tipo: "aprendendo", texto: m.texto };
}

/** As três primeiras linhas do texto do feedback. */
export function primeirasLinhas(texto: string, n = 3): string {
  return texto.split("\n").filter((l) => l.trim().length > 0).slice(0, n).join("\n");
}
