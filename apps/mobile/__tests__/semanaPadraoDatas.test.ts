import { isoLocal, isoParaBr, isoParaBrCurto, lerDataBr, mascararData, proximaSegunda } from "../src/semanaPadrao/datas";

describe("datas da semana-padrão", () => {
  it("máscara dd/mm/aaaa", () => {
    expect(mascararData("")).toBe("");
    expect(mascararData("1")).toBe("1");
    expect(mascararData("150")).toBe("15/0");
    expect(mascararData("15042026")).toBe("15/04/2026");
    expect(mascararData("15/04/2026999")).toBe("15/04/2026");
    expect(mascararData("ab1")).toBe("1");
  });

  it("lê datas válidas e recusa as que não existem", () => {
    expect(lerDataBr("")).toEqual({ tipo: "vazia" });
    expect(lerDataBr("02/03/2026")).toEqual({ tipo: "ok", iso: "2026-03-02" });
    expect(lerDataBr("29/02/2028")).toEqual({ tipo: "ok", iso: "2028-02-29" });
    for (const ruim of ["31/02/2026", "29/02/2026", "00/01/2026", "10/13/2026", "1/1/2026", "02/03/26"]) {
      expect(lerDataBr(ruim)).toEqual({ tipo: "invalida" });
    }
  });

  it("formata", () => {
    expect(isoParaBr("2026-03-02")).toBe("02/03/2026");
    expect(isoParaBrCurto("2026-03-02")).toBe("02/03/26");
    expect(isoLocal(new Date(2026, 0, 5, 23, 59))).toBe("2026-01-05");
  });

  it("a próxima segunda é sempre depois de hoje", () => {
    // 2026-03-09 é segunda; 2026-03-10 terça; 2026-03-15 domingo.
    expect(isoLocal(proximaSegunda(new Date(2026, 2, 9)))).toBe("2026-03-16");
    expect(isoLocal(proximaSegunda(new Date(2026, 2, 10)))).toBe("2026-03-16");
    expect(isoLocal(proximaSegunda(new Date(2026, 2, 14)))).toBe("2026-03-16");
    expect(isoLocal(proximaSegunda(new Date(2026, 2, 15)))).toBe("2026-03-16");
  });
});
