# 校验：一键 check.sh 与 pi 加载器复核

> English: [ci.en.md](ci.en.md) · 返回 [README](../README.md)

## 一键校验（不依赖任何 CI 服务）

全部检查收敛为一个自包含脚本 `ci/check.sh`，约 8 秒跑完：① 两次构建 sha1 一致（确定性）；
② git 工作树内校验 `themes/` 与 `THEMES` 同步（改动未提交即失败，非 git 目录自动跳过）；③ `--check`
全量把关；④ pi 校验器 + 加载器实测 25 套（`PI_VERSION=…` 可换版本，需 node ≥ 22.19；`node_modules/`
已缓存并 gitignore）。脚本不关心谁来调它，触发方式随意：

- **本地**：`git config core.hooksPath .githooks`，之后每次 `git push` 前自动全量跑（`.githooks/pre-push`）。
- **常驻机器**：cron / systemd timer 定时在克隆里跑 `ci/check.sh`，失败时接邮件 / ntfy 通知。
- **托管在别的 forge**：GitLab CI、Woodpecker、Forgejo Actions 等都只需一步 `run: ci/check.sh`。

## 用 pi 自己的加载器复核
这是沙箱里没有 pi 二进制时的做法；`validateThemeJson` 就是 pi 启动时接进加载器的那个校验器：

```bash
npm install --omit=dev --ignore-scripts @earendil-works/pi-coding-agent@0.85.1
node --input-type=module -e '
const P="./node_modules/@earendil-works/pi-coding-agent/dist/modes/interactive/theme/";
const {loadThemeFromPath,setThemeJsonValidator}=await import(P+"theme.js");
const {validateThemeJson}=await import(P+"theme-json.js");
setThemeJsonValidator(validateThemeJson);
for (const f of (await import("node:fs")).readdirSync("themes")) loadThemeFromPath("themes/"+f,"dark");
console.log("ok")'
```
