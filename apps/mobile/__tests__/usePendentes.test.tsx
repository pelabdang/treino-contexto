import { render, screen, waitFor } from "@testing-library/react-native";
import { Text } from "react-native";

import { usePendentes } from "../src/checkin/usePendentes";

const resposta = (status: number, corpo?: unknown) => ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;

function Amostra({ ativo, f }: { ativo: boolean; f: typeof fetch }) {
  const n = usePendentes(ativo, "http://api.teste", 1, f);
  return <Text testID="n">{n}</Text>;
}

describe("usePendentes", () => {
  it("devolve o total de treinos esperando check-in", async () => {
    const f = jest.fn(async () => resposta(200, { dias: 7, pendentes: [], total: 3 })) as unknown as typeof fetch;
    await render(<Amostra ativo f={f} />);
    await waitFor(() => expect(screen.getByTestId("n").props.children).toBe(3));
    expect(String((f as jest.Mock).mock.calls[0][0])).toBe("http://api.teste/atletas/1/checkins/pendentes");
  });

  it("falha vira 0; inativo não chama a API", async () => {
    const quebra = jest.fn(async () => resposta(500, {})) as unknown as typeof fetch;
    await render(<Amostra ativo f={quebra} />);
    await waitFor(() => expect(quebra).toHaveBeenCalled());
    expect(screen.getByTestId("n").props.children).toBe(0);
    const parado = jest.fn() as unknown as typeof fetch;
    await render(<Amostra ativo={false} f={parado} />);
    expect(parado).not.toHaveBeenCalled();
  });
});
