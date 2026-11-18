// Sessão do app (#502, ADR 0016, spec docs/design/telas/entrar.md). Guarda o token (cofre no celular, sessionStorage na web), pergunta
// à API quem é a pessoa ao abrir (`GET /sessao`) e entrega às telas um `fetch` que manda o Bearer. O id do atleta e do professor vem
// daqui. Um `401` em qualquer chamada limpa o acesso e leva a pessoa a "Seu acesso expirou". Nada do corpo das respostas vai a log.
import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";

import { config } from "../config";
import * as api from "./api";
import * as guarda from "./armazenamento";
import { destinoValido, type Papel } from "./destino";

export type EstadoSessao =
  | { tipo: "verificando" }
  /** `expirou`: mostra a faixa "Seu acesso expirou". `lembrar`: a guarda de rotas guarda o endereço pedido (não ao sair de propósito). */
  | { tipo: "sem_acesso"; expirou: boolean; lembrar: boolean }
  | { tipo: "sem_rede" }
  | { tipo: "dentro"; papel: Papel; atletaId: number | null; professorId: number | null; nome: string; trocaObrigatoria: boolean };

export type SessaoContexto = {
  estado: EstadoSessao;
  apiUrl: string;
  /** `fetch` que manda `Authorization: Bearer` (só para a URL da API) e trata `401` e `403 troca_de_senha_obrigatoria`. */
  fetch: typeof fetch;
  entrar: (email: string, senha: string) => Promise<api.ResultadoSessao<api.Entrou>>;
  /** Sai no aparelho na hora e avisa a API sem esperar. */
  sair: () => void;
  trocarSenha: (atual: string, nova: string) => Promise<api.ResultadoSessao<api.NovoAcesso>>;
  /** Refaz a verificação do acesso (tela "sem rede"). */
  verificarDeNovo: () => void;
  /** A guarda de rotas informa o caminho atual (usado quando o acesso expira). */
  registrarCaminho: (caminho: string) => void;
  lembrarDestino: (caminho: string) => void;
  /** Lê e apaga o endereço lembrado. */
  consumirDestino: () => Promise<string | null>;
};

const Contexto = createContext<SessaoContexto | null>(null);

export function useSessao(): SessaoContexto {
  const c = useContext(Contexto);
  if (!c) throw new Error("useSessao fora do SessaoProvider");
  return c;
}

/** Atleta que está dentro, para as telas do atleta. Se não for atleta, `atletaId` é 0 (a guarda de rotas nem chega a montar a tela). */
export function useAtleta() {
  const s = useSessao();
  const atletaId = s.estado.tipo === "dentro" ? (s.estado.atletaId ?? 0) : 0;
  return { apiUrl: s.apiUrl, atletaId, fetchFn: s.fetch };
}

/** Professor que está dentro, para a caixa do dia. `professorId` é `null` se a conta não for de professor. */
export function useProfessor() {
  const s = useSessao();
  const professorId = s.estado.tipo === "dentro" ? s.estado.professorId : null;
  return { apiUrl: s.apiUrl, professorId, fetchFn: s.fetch };
}

type Props = { children: ReactNode; apiUrl?: string; fetchBase?: typeof fetch };

function viraEstado(d: api.QuemSou | api.Entrou): EstadoSessao {
  if (d.papel !== "atleta" && d.papel !== "professor") return { tipo: "sem_acesso", expirou: false, lembrar: false };
  return {
    tipo: "dentro",
    papel: d.papel,
    atletaId: d.atleta_id ?? null,
    professorId: d.professor_id ?? null,
    nome: d.nome,
    trocaObrigatoria: d.troca_de_senha_obrigatoria,
  };
}

export function SessaoProvider({ children, apiUrl = config.apiUrl, fetchBase }: Props) {
  const [estado, setEstado] = useState<EstadoSessao>({ tipo: "verificando" });
  const token = useRef<string | null>(null);
  const caminho = useRef("/");
  const destino = useRef<string | null>(null);
  const ativo = useRef(true);
  useEffect(() => {
    ativo.current = true;
    return () => {
      ativo.current = false;
    };
  }, []);

  const base = useCallback<typeof fetch>((...a) => (fetchBase ?? globalThis.fetch)(...a), [fetchBase]);
  const mudar = useCallback((e: EstadoSessao) => {
    if (ativo.current) setEstado(e);
  }, []);

  const lembrarDestino = useCallback((c: string) => {
    if (!destinoValido(c)) return;
    destino.current = c;
    void guarda.gravarDestino(c);
  }, []);

  // O acesso deixou de valer (401 depois de entrar): guarda o endereço atual, limpa o token e mostra "Seu acesso expirou".
  const expirar = useCallback(
    (quem: string) => {
      if (token.current !== quem) return;
      token.current = null;
      lembrarDestino(caminho.current);
      void guarda.apagarTudo(true);
      mudar({ tipo: "sem_acesso", expirou: true, lembrar: false });
    },
    [lembrarDestino, mudar],
  );

  const fetchAut = useCallback<typeof fetch>(
    async (input, init) => {
      const t = token.current;
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : (input as Request).url;
      // O token só vai para a API do app, nunca para outro endereço.
      if (!t || !url.startsWith(apiUrl)) return base(input, init);
      const headers = new Headers(init?.headers);
      headers.set("Authorization", `Bearer ${t}`);
      const r = await base(input, { ...init, headers });
      if (r.status === 401) expirar(t);
      else if (r.status === 403) {
        try {
          const detail = ((await r.clone().json()) as { detail?: unknown }).detail;
          const tipo = Array.isArray(detail) ? (detail[0] as { type?: unknown } | undefined)?.type : null;
          if (tipo === "troca_de_senha_obrigatoria") {
            setEstado((e) => (e.tipo === "dentro" && !e.trocaObrigatoria ? { ...e, trocaObrigatoria: true } : e));
          }
        } catch {
          // 403 sem o corpo esperado: a tela mostra o erro genérico
        }
      }
      return r;
    },
    [apiUrl, base, expirar],
  );

  const verificar = useCallback(async () => {
    mudar({ tipo: "verificando" });
    const guardado = await guarda.lerToken();
    if (!guardado) {
      token.current = null;
      mudar({ tipo: "sem_acesso", expirou: false, lembrar: true });
      return;
    }
    const r = await api.quemSou({ baseUrl: apiUrl, fetch: base, token: guardado });
    if (r.ok) {
      token.current = guardado;
      mudar(viraEstado(r.dados));
    } else if (r.falha.motivo === "nao_autorizado") {
      token.current = null;
      void guarda.apagarTudo(true);
      mudar({ tipo: "sem_acesso", expirou: true, lembrar: true });
    } else {
      // Sem rede ou erro do servidor: não manda para a entrada, a pessoa pode estar logada só sem sinal.
      mudar({ tipo: "sem_rede" });
    }
  }, [apiUrl, base, mudar]);

  useEffect(() => {
    void verificar();
  }, [verificar]);

  const entrar = useCallback<SessaoContexto["entrar"]>(
    async (email, senha) => {
      const r = await api.entrar(email.trim(), senha, { baseUrl: apiUrl, fetch: base });
      if (r.ok) {
        token.current = r.dados.token;
        await guarda.gravarToken(r.dados.token);
        mudar(viraEstado(r.dados));
      }
      return r;
    },
    [apiUrl, base, mudar],
  );

  const sair = useCallback(() => {
    const t = token.current;
    token.current = null;
    destino.current = null;
    void guarda.apagarTudo(false);
    mudar({ tipo: "sem_acesso", expirou: false, lembrar: false });
    // Sem esperar e sem depender da rede: o token apagado já impede o uso neste aparelho.
    if (t) void api.sair({ baseUrl: apiUrl, fetch: base, token: t }).catch(() => undefined);
  }, [apiUrl, base, mudar]);

  const trocarSenha = useCallback<SessaoContexto["trocarSenha"]>(
    async (atual, nova) => {
      const t = token.current;
      const r = await api.trocarSenha(atual, nova, { baseUrl: apiUrl, fetch: base, token: t ?? undefined });
      if (r.ok) {
        // A API revoga todos os acessos e devolve um novo: o antigo não vale mais.
        token.current = r.dados.token;
        await guarda.gravarToken(r.dados.token);
        setEstado((e) => (e.tipo === "dentro" ? { ...e, trocaObrigatoria: false } : e));
      } else if (r.falha.motivo === "nao_autorizado" && t) {
        expirar(t);
      }
      return r;
    },
    [apiUrl, base, expirar],
  );

  const consumirDestino = useCallback(async () => {
    const d = destino.current ?? (await guarda.lerDestino());
    destino.current = null;
    void guarda.apagarDestino();
    return destinoValido(d) ? d : null;
  }, []);

  const valor = useMemo<SessaoContexto>(
    () => ({
      estado,
      apiUrl,
      fetch: fetchAut,
      entrar,
      sair,
      trocarSenha,
      verificarDeNovo: () => void verificar(),
      registrarCaminho: (c) => {
        caminho.current = c;
      },
      lembrarDestino,
      consumirDestino,
    }),
    [estado, apiUrl, fetchAut, entrar, sair, trocarSenha, verificar, lembrarDestino, consumirDestino],
  );
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export { Contexto as ContextoSessao };
