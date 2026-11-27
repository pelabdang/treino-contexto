// Gera os PNG do app a partir dos SVG de docs/design/marca/ (identidade v3). Uso: node scripts/gerar-icones.mjs
// Usa o Chromium do Playwright (já é dependência de desenvolvimento); fundo transparente onde o SVG é transparente.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const aqui = dirname(fileURLToPath(import.meta.url));
const marca = join(aqui, "../../../docs/design/marca");
const saida = join(aqui, "../assets");

const fundoVolt = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024"><rect width="1024" height="1024" fill="#C6F432"/></svg>`;
const alvos = [
  ["icon.png", readFileSync(join(marca, "icone-app-1024.svg"), "utf8"), 1024],
  ["android-icon-foreground.png", readFileSync(join(marca, "icone-android-frente.svg"), "utf8"), 1024],
  ["android-icon-monochrome.png", readFileSync(join(marca, "icone-android-monocromatico.svg"), "utf8"), 1024],
  ["android-icon-background.png", fundoVolt, 1024],
  ["splash-icon.png", readFileSync(join(marca, "logo-pulso-simbolo.svg"), "utf8"), 1024],
  ["favicon.png", readFileSync(join(marca, "logo-pulso-simbolo.svg"), "utf8"), 96],
];

const navegador = await chromium.launch();
for (const [nome, svg, lado] of alvos) {
  const pagina = await navegador.newPage({ viewport: { width: lado, height: lado } });
  const corpo = svg.replace(/ width="\d+" height="\d+"/, ` width="${lado}" height="${lado}"`);
  await pagina.setContent(`<html><body style="margin:0;background:transparent">${corpo}</body></html>`);
  await pagina.screenshot({ path: join(saida, nome), omitBackground: true });
  await pagina.close();
  console.log("ok", nome);
}
await navegador.close();
