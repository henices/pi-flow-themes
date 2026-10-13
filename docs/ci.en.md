# Verification: one-shot check.sh and pi's own loader

> 中文：[ci.md](ci.md) · Back to [README.en.md](../README.en.md)

## One-shot verification (no CI service required)

All checks collapse into one self-contained script, `ci/check.sh` (~8 s): (1) two consecutive
builds must be byte-identical (determinism); (2) inside a git worktree, `themes/` must match a fresh
build (uncommitted changes fail; skipped outside git); (3) the full `--check` gate; (4) all 25 themes
loaded through pi's own validator + loader (`PI_VERSION=…` to pin another version, needs node ≥
22.19; `node_modules/` is cached and gitignored). The script doesn't care who invokes it:

- **Local**: `git config core.hooksPath .githooks` — the full pipeline then runs before every
  `git push` (`.githooks/pre-push`).
- **Always-on machine**: cron / systemd timer runs `ci/check.sh` in a clone; wire failures to
  mail / ntfy.
- **Hosted on another forge**: GitLab CI, Woodpecker, Forgejo Actions, etc. — a single
  `run: ci/check.sh` step is all they need.

## Cross-check with pi's own loader
This is what to do when the pi binary isn't available in the sandbox;
`validateThemeJson` is the same validator pi wires into its loader at startup (the loader's second
argument is a `TerminalColorMode`, so `"truecolor"`, not an appearance):

```bash
npm install --ignore-scripts --no-save @earendil-works/pi-coding-agent@1.2.0
node --input-type=module -e '
const P="./node_modules/@earendil-works/pi-coding-agent/dist/modes/interactive/theme/";
const {loadThemeFromPath,setThemeJsonValidator}=await import(P+"theme.js");
// pi 1.2.0 renamed theme-json.js to theme-schema.js (same validateThemeJson signature)
const V=(await import("node:fs")).existsSync(P+"theme-schema.js")?"theme-schema.js":"theme-json.js";
const {validateThemeJson}=await import(P+V);
setThemeJsonValidator(validateThemeJson);
for (const f of (await import("node:fs")).readdirSync("themes")) loadThemeFromPath("themes/"+f,"truecolor");
console.log("ok")'
```
