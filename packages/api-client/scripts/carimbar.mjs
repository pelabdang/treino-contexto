// Depois do openapi-typescript: grava no topo de src/schema.d.ts o sha256 do openapi.json usado.
// O teste do pytest (test_contrato_cliente.py) compara esse carimbo com o openapi.json versionado.
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";

const raiz = new URL("..", import.meta.url);
const hash = createHash("sha256").update(readFileSync(new URL("openapi.json", raiz))).digest("hex");
const arquivo = new URL("src/schema.d.ts", raiz);
const corpo = readFileSync(arquivo, "utf8").replace(/^\/\/ openapi-sha256: .*\n/, "");
writeFileSync(arquivo, `// openapi-sha256: ${hash}\n${corpo}`);
console.log(`carimbo openapi-sha256: ${hash}`);
