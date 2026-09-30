# 24 位色必须全程打通

> English: [truecolor.en.md](truecolor.en.md) · 返回 [README](../README.md)


主题里的工具状态盒是低饱和的深色，一旦被量化成 256 色就会失真：done 盒变青（`#005F5F`），
error 盒变灰（`#5F5F5F`）。pi 内置的 dark 主题同样受影响。链路上有两道闸：

1. **pi 本身**。`COLORTERM` 为 `truecolor` 或 `24bit` 时发 24 位色，0.99 起 `TERM` 以 `-direct`
   结尾（如 `xterm-direct`）同样算。该变量为空时，0.37 及以后的版本
   仍假定真彩（`screen*`、`linux`、`dumb`、Terminal.app 除外），更老的版本会退到 256 色。
   docker 不会把宿主的 `COLORTERM` 传进容器，所以在启动 pi 的 shell 里显式
   `export COLORTERM=truecolor` 最稳妥。若 pi 对终端能力的判断本身出错，可用设置强制：
   settings.json 的 `"terminal": {"trueColor": true}`，或环境变量 `PI_TRUE_COLOR=1`。注意
   这两条覆盖到 0.99.0 才对自定义主题生效（此前会被忽略、主题仍按 256 色渲染），本仓库的
   25 套主题需要 pi ≥ 0.99.0 才能靠强制设置兜底。
2. **中间的 tmux / screen**。tmux 若不知道外层终端支持 RGB，会把 pi 发出的 24 位色自行降成 256 色，
   症状与上面一样。`.tmux.conf` 里加两行后重启 tmux server：

   ```
   set -g default-terminal "tmux-256color"
   set -as terminal-features ",xterm*:RGB"     # tmux < 3.2 用 set -ga terminal-overrides ",xterm*:Tc"
   ```

验证：在跑 pi 的那个 shell（tmux 用户就在 pane 里）执行 `printf '\e[48;2;46;73;49m green \e[0m'`，
色块是绿的就说明全程 24 位色。
