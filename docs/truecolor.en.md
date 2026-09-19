# 24-bit color must work end to end

> 中文：[truecolor.md](truecolor.md) · Back to [README.en.md](../README.en.md)


The tool status boxes in these themes are dark, low-saturation colors; once quantized down to 256
colors they visibly distort: the done box turns teal (`#005F5F`) and the error box gray (`#5F5F5F`).
pi's built-in dark theme suffers the same way. There are two gates in the chain:

1. **pi itself.** pi emits 24-bit color when `COLORTERM` is `truecolor` or `24bit`. When the variable
   is empty, versions 0.37 and later still assume truecolor (except `screen*`, `linux`, `dumb`, and
   Terminal.app), while older versions fall back to 256 colors. Docker does not pass the host's
   `COLORTERM` into the container, so explicitly running `export COLORTERM=truecolor` in the shell
   that launches pi is the safest option.
2. **tmux / screen in the middle.** If tmux doesn't know the outer terminal supports RGB, it
   downscales the 24-bit color pi emits to 256 colors on its own — same symptoms as above. Add two
   lines to `.tmux.conf` and restart the tmux server:

   ```
   set -g default-terminal "tmux-256color"
   set -as terminal-features ",xterm*:RGB"     # on tmux < 3.2 use: set -ga terminal-overrides ",xterm*:Tc"
   ```

To verify: in the shell running pi (inside the pane, if you use tmux), run
`printf '\e[48;2;46;73;49m green \e[0m'`. If the swatch is green, you have 24-bit color end to end.
