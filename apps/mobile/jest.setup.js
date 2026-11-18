// Área segura nos testes: sem a view nativa, o hook devolve margens zero (mock que o próprio pacote traz).
jest.mock("react-native-safe-area-context", () => require("react-native-safe-area-context/jest/mock").default);
