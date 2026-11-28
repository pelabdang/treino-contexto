import { dataDaLista, horaCurta, rotuloDoDia } from "../src/chat/hora";
import { caminhoDoPapel } from "../src/sessao/destino";

const agora = new Date(2025, 2, 20, 18, 0, 0); // quinta, 20/03/2025

describe("horas e dias do chat", () => {
  it("a hora é o recorte do texto da API, sem converter fuso", () => {
    expect(horaCurta("2025-03-20T14:32:10-03:00")).toBe("14:32");
    expect(horaCurta("")).toBe("");
  });
  it("hoje, ontem e dia curto", () => {
    expect(rotuloDoDia("2025-03-20T14:32:10-03:00", agora)).toBe("hoje");
    expect(rotuloDoDia("2025-03-19T20:10:00-03:00", agora)).toBe("ontem");
    expect(rotuloDoDia("2025-03-14T07:45:00-03:00", agora)).toBe("sex 14/03");
    expect(rotuloDoDia("", agora)).toBe("");
  });
  it("data da lista", () => {
    expect(dataDaLista("2025-03-20T14:32:10-03:00", agora)).toBe("hoje, 14:32");
    expect(dataDaLista("2025-03-19T20:10:00-03:00", agora)).toBe("ontem, 20:10");
    expect(dataDaLista("2025-03-12T07:45:00-03:00", agora)).toBe("qua 12/03, 07:45");
  });
  it("o chat é do atleta: o professor não abre", () => {
    expect(caminhoDoPapel("atleta", "/chat")).toBe(true);
    expect(caminhoDoPapel("atleta", "/chat/conversas")).toBe(true);
    expect(caminhoDoPapel("professor", "/chat")).toBe(false);
  });
});
