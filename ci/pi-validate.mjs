// Load every themes/flow-*.json through pi's own schema validator + loader — the same code path
// pi runs at startup. Run from the repo root (ci/check.sh does).
// Usage: node ci/pi-validate.mjs [pi-package dist/modes/interactive/theme dir]
import { readdirSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const dir =
  process.argv[2] ??
  "node_modules/@earendil-works/pi-coding-agent/dist/modes/interactive/theme/";
const { loadThemeFromPath, setThemeJsonValidator } = await import(
  pathToFileURL(resolve(dir, "theme.js")).href
);
const { validateThemeJson } = await import(
  pathToFileURL(resolve(dir, "theme-json.js")).href
);
setThemeJsonValidator(validateThemeJson);

const files = readdirSync("themes").filter((f) => f.startsWith("flow-"));
for (const f of files) loadThemeFromPath(`themes/${f}`, "dark");
console.log(`pi loader: ${files.length}/${files.length} themes ok`);
