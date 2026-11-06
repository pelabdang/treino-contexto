// Verifica que a web exportada abre renderizada (#218): o HTML precisa trazer o <script>
// do bundle e o lang pt-BR. Uso: npm run verificar:web
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const saida = mkdtempSync(join(tmpdir(), "web-"));
try {
  execFileSync("npx", ["expo", "export", "--platform", "web", "--output-dir", saida], {
    stdio: "inherit",
    env: { ...process.env, CI: "1" },
  });
  const html = readFileSync(join(saida, "index.html"), "utf8");
  const falhas = [];
  if (!/<script[^>]+src="[^"]*_expo\/static\/js\/web\/entry-[^"]+\.js"/.test(html)) {
    falhas.push("sem o <script> do bundle (entry-*.js)");
  }
  if (!html.includes('lang="pt-BR"')) falhas.push('sem lang="pt-BR"');
  if (falhas.length) {
    console.error(`FALHOU: index.html ${falhas.join("; ")}. Veja src/app/+html.tsx (headNodes e bodyNodes).`);
    process.exit(1);
  }
  console.log("OK: index.html traz o script do bundle e lang pt-BR.");
} finally {
  rmSync(saida, { recursive: true, force: true });
}
