// Única leitura das variáveis de ambiente do app. O Expo troca
// `process.env.EXPO_PUBLIC_*` pelo valor na hora do bundle, então o acesso
// precisa ser direto (sem desestruturar process.env).
// O atleta e o professor NÃO vêm mais daqui: o identificador vem da sessão (`POST/GET /sessao`, ADR 0016, #502).
export const API_URL_PADRAO = "http://localhost:8000";

export type Config = {
  apiUrl: string;
};

export function lerConfig(apiUrl: string | undefined = process.env.EXPO_PUBLIC_API_URL): Config {
  return {
    apiUrl: apiUrl?.trim() ? apiUrl.trim().replace(/\/+$/, "") : API_URL_PADRAO,
  };
}

export const config: Config = lerConfig();
