// Load every themes/flow-*.json through pi's own schema validator + loader — the same code path
// pi runs at startup. Run from the repo root (ci/check.sh does).
// Usage: node ci/pi-validate.mjs [pi-package dist/modes/interactive/theme dir]
// The loader's second argument is a TerminalColorMode ("truecolor" | "256color"), not an
// appearance; "truecolor" matches the 24-bit chain these themes are designed for
// (docs/truecolor.md). "dark" is not a valid value and silently fell back to 256-color output.
import { existsSync, readdirSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";

const dir =
  process.argv[2] ??
  "node_modules/@earendil-works/pi-coding-agent/dist/modes/interactive/theme/";
const { loadThemeFromPath, setThemeJsonValidator } = await import(
  pathToFileURL(resolve(dir, "theme.js")).href
);
const { validateThemeJson } = await import(
  // pi 1.2.0 renamed theme-json.js → theme-schema.js (validateThemeJson signature unchanged);
  // pick by file existence so PI_VERSION can be either side of 1.2.0. A missing validator in
  // both names still throws below and fails the check.
  pathToFileURL(
    resolve(dir, existsSync(resolve(dir, "theme-schema.js")) ? "theme-schema.js" : "theme-json.js"),
  ).href
);
setThemeJsonValidator(validateThemeJson);

const files = readdirSync("themes").filter((f) => f.startsWith("flow-"));
for (const f of files) loadThemeFromPath(`themes/${f}`, "truecolor");
console.log(`pi loader: ${files.length}/${files.length} themes ok`);
