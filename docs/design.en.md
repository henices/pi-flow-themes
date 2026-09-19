# Design principle: the background carries state, the foreground carries identity

> 中文：[design.md](design.md) · Back to [README.en.md](../README.en.md)


Three metrics are used below; here is what they mean:

- **Contrast ratio `N:1`** — WCAG relative-luminance contrast: how much brighter or darker the
  foreground is than its background. 1:1 is the same color; 3:1 is the minimum legibility bar for UI
  elements and large text; 4.5:1 is the bar for body text; 7:1 and up counts as high contrast. This
  collection's criteria: body text ≥ 4.5, every other readable element ≥ 3.
- **CIE L\\*** — perceptual lightness, 0 = pure black, 100 = pure white, on a scale that is linear to
  the human eye. Two backgrounds need a ΔL\\* of about 5 before you can reliably tell "this is a
  panel".
- **ΔE** — the overall perceptual difference between two colors (lightness + hue + saturation). ~2 is
  just noticeable, above 10 is separable at a glance, and above 20 the colors are clearly different.

Every number in this document can be recomputed with `python3 build_themes.py --measure`; pass it a
few hex values and it prints pairwise contrast / ΔE / ΔL\\*.

pi has no global background token: the canvas is the terminal's own background color, and a theme
only controls what is drawn on top of it. Upstream palettes typically define a dozen-odd colors and
editor roles, while pi has 56 tokens, 19 of which are UI surfaces that don't exist in an editor: the
user message box, three tool status boxes, selection, search, dividers, scrollbar, and the seven
thinking-level borders.

## UI layer: one set of constants shared by all 25

These 19 tokens are identical across all 25 themes, matching the architecture of pi's built-in dark
theme — backgrounds express state, not theme identity.

| Element | Value | CIE L\\* |
|---|---|---|
| User message box, custom message box | `#414141` | 27.5 |
| Tool running | `#3E4049` (slightly cool gray; ΔE 6 from the user box — noticeable, not attention-grabbing) | 27.2 |
| Tool success / failure | `#2E4931` / `#61373A` | 28.3 (ΔE 20 / 20 from the user box, 36 between the two — separable at a glance) |
| Selection / search highlight | `#474747` / `#4E4E4E` | 30 / 33 |
| Dividers, code block border, thinking off | `#575757` | 37 |
| Scrollbar thumb, thinking minimal | `#727272` | 48 |
| thinking low → max | `#5EA190` `#6E96AA` `#8985B7` `#AB85B7` `#B66D9D` | teal → blue → blue-violet → purple → magenta |

The lightness targets come from measured default backgrounds of mainstream terminals (the defaults
in each terminal's source):

| Terminal / scheme | Background | L\\* |
|---|---|---|
| kitty, Windows Terminal Vintage / Ottosson | `#000000` | 0 |
| Windows Terminal Campbell | `#0C0C0C` | 3 |
| Alacritty default, VS Code Dark Modern terminal pane | `#181818` | 8 |
| GNOME dark, VS Code Dark+ | `#1E1E1E` | 11 |
| Konsole Breeze | `#232627` | 15 |
| Ghostty default, One Half Dark | `#282C34` | 18 |
| WezTerm default, GNOME Tango dark | `#333333` / `#2E3436` | 21 |
| The 25 schemes' own canvases in this set | Rosé Pine `#191724` … Catppuccin Frappé `#303446` | 8.5–22.0 |

Dark terminal backgrounds almost all fall in L\\* 0–22. Panels are pinned at 27.5: on the brightest
canvas in the set (Catppuccin Frappé `#303446`, L\\* 22.0) they are still 5.5 L\\* brighter than the
background — just past the "you can tell it's a panel" line — and 27.5 brighter on pure black (the
same magnitude as pi's built-in dark on a black background). Terminals with backgrounds brighter
than L\\* 22 are outside the design envelope.
The image below shows this layer as actually rendered on each background (generated with
`--preview`):

![ui-layer](../preview/ui-layer.png)

The thinking-level border colors encode only the level: five levels, five colors, low-stimulation,
no alarm colors such as red or yellow, and identical across themes.

## Foreground layer: how bright a terminal background each theme supports

The foregrounds are official colors, but the canvas is the terminal's own background, so how bright
a background each theme stays readable on differs from theme to theme. `--check` recomputes every
canvas foreground against each background in the table above and reports the brightest background on
which everything still passes 3:1 / 4.5:1 (excluding colors already listed under known costs); on
brighter backgrounds, the first casualties are the theme's secondary foregrounds — dim / borders /
comments — while body text is unaffected.

| Brightest supported background | Themes |
|---|---|
| L\\* 21–22 (WezTerm `#333333`, GNOME Tango, their own canvases) | One Dark Pro, Nord, Tokyo Night, Catppuccin Frappé / Macchiato, Everforest, Miramare, Moonlight, Oceanic Next, Synthwave '84, Material |
| L\\* 18 (Ghostty `#282C34`, One Half Dark) | Gruvbox, Solarized, ayu Mirage, Melange, Noctis Bordo / Sereno, Snazzy, Dracula (own canvas 17.3) |
| L\\* 15–16 (Konsole Breeze `#232627`) | Catppuccin Mocha, Kanagawa, Monokai, GitHub Dark, Andromeda |
| L\\* 11 (GNOME dark, VS Code Dark+ `#1E1E1E`) | Rosé Pine (its pine keywords and muted gray fall below 3:1 on brighter backgrounds) |

## Foreground layer: official colors first

The remaining 37 tokens (body / secondary / status line, syntax, markdown, status colors, accent,
borders) in principle use only hex values from the official palettes, with roles mapped per the
original authors' highlight definitions; the sources are documented in the comment block above each
theme in `build_themes.py`. The single custom foreground is Solarized's tool title `#B3BAB3`: the
official base1 reaches only 3.72:1 on the shared success box while the next step up, base2, jumps to
8.11:1; the in-between color lands at 5.01:1.

Known costs of sticking to official colors (`--check` lists these; left unfixed on purpose):

- Comments and the status line sit at 2.2–3.0:1 in One Dark / Nord / Tokyo Night / Solarized /
  Miramare / Oceanic Next / Material, below the 3:1 legibility line — the original authors made
  comments dark by design; that is what these schemes look like.
- Some official reds run dark against the deep tool-box backgrounds: the diff deletion colors of
  Nord / Solarized / Monokai / Gruvbox / Andromeda / Noctis measure 2.1–3.0:1, Solarized's violet
  tags 2.3:1, Kanagawa's oniViolet tags and autumnGreen 2.9:1 — all slightly below 3:1.
- Body text passes the 4.5:1 legibility line on every canvas, but two schemes miss the 7:1
  high-contrast bar: One Dark at 6.6:1 and Solarized (base1) at 5.6:1. There are exceptions on the
  shared panel / selection backgrounds: Solarized's base1 is 3.8:1 on the user message box and 3.5:1
  on selection, and One Dark's body text is 4.4:1 on selection — these gray panels are brighter than
  the canvas, and the official body colors have no brighter step to swap in.
- Dracula's tool title uses official pink, 4.16:1 on the shared success box, slightly below the
  4.5:1 body-text line; the bold command text is still crisp.
- Text hierarchy: Dracula officially has just one gray (comment), so muted equals dim and the three
  text levels collapse to two; One Dark's and Solarized's body vs. secondary text differ by only
  about ΔL\\* 5 (their official fg vs. statusFg and base1 vs. base0 are close to begin with).
- Synthwave '84's body text is the official `colors.foreground` pure white `#FFFFFF` (upstream has
  no editor.foreground), the brightest body text in the set.

Intentional role or value deviations (all still official colors of the theme — only the roles differ
from upstream; re-verified hex-by-hex against upstream on 2026-09-19):

- **Readability-driven**: Nord body text uses nord6 and secondary text nord4 (pi needs three text
  levels and Nord has no middle gray); Solarized body text uses base1 (base0 is too dark in
  terminals) and the tool title uses the in-between color described above; Kanagawa diff deletion
  uses waveRed (autumnRed is only 2.1:1 inside the box) and borders use ui.special's springViolet1
  (upstream's divider is a background color); One Dark's on-panel text uses its bright foreground
  `#D7DAE0`; Miramare's secondary text, blockquotes, and borders use orange (the official Grey
  `#444444` is unreadable on a terminal canvas and upstream has no secondary text level); Noctis's
  in-box secondary text uses official TEXT (comment is only 2.3:1 inside the box); Oceanic Next's
  secondary text uses `#A7ADBA` from the official extended palette; Material's borders and tool
  title use base04 (base03 is the comment color, too dark; base05 `#EEFFFF` is glaring as a title;
  base0D is 4.32:1 inside the box); Monokai's tool title uses official
  `editorLineNumber.activeForeground` `#C2C2BF` (fg `#F8F8F2` is glaring as a title, and the accent
  green would match the success box); Catppuccin Frappé / Macchiato link URLs use overlay1 (the
  overlay0 that Mocha uses is 2.9:1 on these two brighter canvases); Tokyo Night diff deletion uses
  red (upstream's diff foreground git.delete `#914C54` is too dark inside the box); Andromeda tags
  use blue (pink is 2.84:1 on panels).
- **pi has no matching role, so a nearby official role of the same theme is used**: all three
  Catppuccin themes use lavender for titles and mauve for list bullets (upstream blue / teal);
  Andromeda uses cyan for list bullets (upstream yellow); Synthwave '84 swaps link text / URL
  relative to upstream (green / yellow, so the URL gets the quieter of the two), and warning uses
  yellow (upstream's editorWarning is success-green); One Dark Pro uses cyan for operators (upstream
  has cyan only for logical / arithmetic operators; the generic keyword.operator is fg); Oceanic
  Next uses fg for punctuation (upstream teal); Melange / Miramare take diff foregrounds from the
  official b/c scales (upstream renders diffs as background blocks, while pi's diff is foreground
  text inside a shared box).
- **Upstream itself has version drift**: ayu Mirage follows mirage.yaml at the head of the
  ayu-colors repo (the npm-published ayu 8.0.1 still carries old values, e.g. the function color
  `#FFD173`); Solarized's green uses the canonical `#859900` (the vim file enables the
  "experimental" green `#719E07`); Andromeda's comments drop the upstream `cc` alpha.
