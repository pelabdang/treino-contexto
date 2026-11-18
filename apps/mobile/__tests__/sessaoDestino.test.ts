import { caminhoDoPapel, destinoDepoisDeEntrar, destinoValido, inicioDoPapel } from "../src/sessao/destino";

describe("destino depois de entrar", () => {
  it("o atleta cai no início e o professor na caixa do dia", () => {
    expect(inicioDoPapel("atleta")).toBe("/");
    expect(inicioDoPapel("professor")).toBe("/caixa-do-dia");
  });

  it("só aceita caminho do próprio app (nunca endereço de fora)", () => {
    for (const ok of ["/", "/treino/107", "/checkin/5?origem=pendentes", "/semana-padrao"]) expect(destinoValido(ok)).toBe(true);
    for (const ruim of [
      null,
      undefined,
      "",
      "treino/1",
      "//outro.site/x",
      "https://outro.site",
      "/\\outro.site",
      "/ok://x",
      "/a\nb",
      "/entrar",
      "/entrar?x=1",
      "/trocar-senha",
    ]) {
      expect(destinoValido(ruim as string)).toBe(false);
    }
  });

  it("separa as telas por papel: a caixa é do professor, as demais do atleta", () => {
    expect(caminhoDoPapel("professor", "/caixa-do-dia")).toBe(true);
    expect(caminhoDoPapel("professor", "/")).toBe(false);
    expect(caminhoDoPapel("professor", "/treino/1")).toBe(false);
    expect(caminhoDoPapel("atleta", "/caixa-do-dia")).toBe(false);
    expect(caminhoDoPapel("atleta", "/treino/1")).toBe(true);
    expect(caminhoDoPapel("atleta", "/checkins-pendentes")).toBe(true);
    expect(caminhoDoPapel("professor", "/trocar-senha")).toBe(true);
  });

  it("volta ao endereço lembrado se for do papel; senão vai ao início do papel", () => {
    expect(destinoDepoisDeEntrar("atleta", "/treino/107")).toBe("/treino/107");
    expect(destinoDepoisDeEntrar("professor", "/treino/107")).toBe("/caixa-do-dia");
    expect(destinoDepoisDeEntrar("atleta", "https://outro.site")).toBe("/");
    expect(destinoDepoisDeEntrar("professor", null)).toBe("/caixa-do-dia");
  });
});
