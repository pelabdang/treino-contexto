import { render, screen } from "@testing-library/react-native";

import Inicio from "../src/app/index";

describe("tela inicial", () => {
  it("mostra o título e o texto provisório", async () => {
    await render(<Inicio />);
    expect(screen.getByText("Evolução dos tiros de 1 km")).toBeTruthy();
    expect(screen.getByText(/Em construção/)).toBeTruthy();
  });
});
