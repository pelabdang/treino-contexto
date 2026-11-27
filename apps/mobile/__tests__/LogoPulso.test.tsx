import { render, screen } from "@testing-library/react-native";
import { useColorScheme } from "react-native";

import { LogoPulso } from "../src/componentes/LogoPulso";

jest.mock("react-native/Libraries/Utilities/useColorScheme", () => ({ default: jest.fn() }));
// O desenho nativo não expõe as cores; troca o SVG por Views com as mesmas props.
jest.mock("react-native-svg", () => {
  const { View } = require("react-native");
  const Falso = (props: object) => <View {...props} />;
  return { __esModule: true, default: Falso, Rect: (p: object) => <View testID="quadrado" {...p} />, Polyline: (p: object) => <View testID="linha" {...p} /> };
});
const esquema = useColorScheme as unknown as jest.Mock;

describe("LogoPulso", () => {
  it("desenha o símbolo no tamanho pedido", async () => {
    esquema.mockReturnValue("light");
    await render(<LogoPulso tamanho={64} />);
    const logo = screen.getByTestId("logo-pulso", { includeHiddenElements: true });
    expect(logo.props.width).toBe(64);
    expect(logo.props.height).toBe(64);
    expect(logo.props.viewBox).toBe("0 0 128 128");
  });

  it("claro: quadrado volt e linha em tinta", async () => {
    esquema.mockReturnValue("light");
    await render(<LogoPulso />);
    expect(screen.getByTestId("quadrado", { includeHiddenElements: true }).props.fill).toBe("#C6F432");
    expect(screen.getByTestId("linha", { includeHiddenElements: true }).props.stroke).toBe("#12200A");
  });

  it("escuro: volt do tema escuro", async () => {
    esquema.mockReturnValue("dark");
    await render(<LogoPulso />);
    expect(screen.getByTestId("quadrado", { includeHiddenElements: true }).props.fill).toBe("#D2FF3C");
    expect(screen.getByTestId("linha", { includeHiddenElements: true }).props.stroke).toBe("#121A05");
  });

  it("é decorativo para o leitor de tela", async () => {
    esquema.mockReturnValue("light");
    await render(<LogoPulso />);
    expect(screen.queryByTestId("logo-pulso")).toBeNull();
    expect(screen.getByTestId("logo-pulso", { includeHiddenElements: true }).props.accessible).toBe(false);
  });
});
