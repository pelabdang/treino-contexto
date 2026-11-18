import { Platform } from "react-native";

const mockCofre = new Map<string, string>();
jest.mock("expo-secure-store", () => ({
  getItemAsync: async (k: string) => mockCofre.get(k) ?? null,
  setItemAsync: async (k: string, v: string) => void mockCofre.set(k, v),
  deleteItemAsync: async (k: string) => void mockCofre.delete(k),
}));

import { apagarTudo, gravarDestino, gravarToken, lerDestino, lerToken } from "../src/sessao/armazenamento";

const original = Platform.OS;
afterEach(() => {
  Platform.OS = original;
  mockCofre.clear();
});

describe("armazenamento do acesso", () => {
  it("no celular guarda no mockCofre do aparelho", async () => {
    Platform.OS = "ios";
    await gravarToken("token-sintetico-1");
    await gravarDestino("/treino/1");
    expect(mockCofre.get("treino.acesso")).toBe("token-sintetico-1");
    expect(await lerToken()).toBe("token-sintetico-1");
    expect(await lerDestino()).toBe("/treino/1");
  });

  it("na web guarda em sessionStorage (nunca no mockCofre nem em localStorage)", async () => {
    Platform.OS = "web";
    const guardado = new Map<string, string>();
    const sessionStorage = {
      getItem: (k: string) => guardado.get(k) ?? null,
      setItem: (k: string, v: string) => void guardado.set(k, v),
      removeItem: (k: string) => void guardado.delete(k),
    };
    Object.defineProperty(globalThis, "sessionStorage", { value: sessionStorage, configurable: true });
    await gravarToken("token-sintetico-2");
    expect(guardado.get("treino.acesso")).toBe("token-sintetico-2");
    expect(mockCofre.size).toBe(0);
    expect(await lerToken()).toBe("token-sintetico-2");
    await apagarTudo();
    expect(await lerToken()).toBeNull();
  });

  it("sair apaga o acesso e o endereço lembrado; expirar mantém o endereço", async () => {
    Platform.OS = "ios";
    await gravarToken("t");
    await gravarDestino("/treino/1");
    await apagarTudo(true);
    expect(await lerToken()).toBeNull();
    expect(await lerDestino()).toBe("/treino/1");
    await apagarTudo();
    expect(await lerDestino()).toBeNull();
  });

  it("nunca lança: se o cofre falha, lê vazio", async () => {
    Platform.OS = "ios";
    const spy = jest.spyOn(mockCofre, "get").mockImplementation(() => {
      throw new Error("sem mockCofre");
    });
    expect(await lerToken()).toBeNull();
    spy.mockRestore();
  });
});
