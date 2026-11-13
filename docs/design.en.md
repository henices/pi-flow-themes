# Design principle: backgrounds carry state and theme hue, foregrounds carry identity

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

## UI layer: shared lightness and state distances, theme-specific background hues

All 19 tokens start from one shared baseline. The eight actual backgrounds (user/custom messages,
three tool boxes, selection, search, and scrollbar track) receive **one common** theme color shift:
30% of the official canvas color's CIE Lab a\\*/b\\*. To avoid overly bright panels on dark
canvases, when the user panel is more than 8 L\\* above the official canvas, the whole background
group drops by at most 4 L\\* rather than forcing identical contrast across themes. Applying one
vector to the whole group preserves relative lightness levels and pairwise ΔE. After quantisation
to 8-bit sRGB, `--check` requires actual versus computed-target L\\* drift ≤ 0.25 and pairwise
state-box ΔE drift ≤ 1.5. The other 11 divider, scrollbar-thumb, and thinking-border colors remain shared.

Solarized keeps **all 37 foreground tokens at official values** through explicit lightness targets:
its user/custom panels and scrollbar track use L\\* 19.5, its three tool boxes use 18, and selection /
search use 22.5 / 25.5. Every text level moves one official step brighter: base2 for body/titles,
base1 for secondary/tool output, and base0 for status lines/comments/URLs. Body text then measures
10.85:1 on user panels and 9.93:1 on selection, violet labels 3.04:1, tool titles 11.35:1, tool output
5.20:1, and red diff deletions 3.01:1. `--check` validates these explicit L\\* targets and absolute
state-box ΔE floors instead of the shared lightness baseline. The tradeoff is a smaller panel-to-canvas
ΔL\\* and weaker panel boundaries on brighter terminal backgrounds; official-foreground legibility
takes priority here.
Nord separately lowers the whole background group by 3 L\\* (user panels 24.5, tool boxes 24.2/25.3,
selection/search 27/30) while preserving their relative levels. Explicit-override themes are checked
against their target L\\* and absolute state-box ΔE floors.

| Element | Shared baseline (the first four rows vary by theme) | CIE L\\* |
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

Dark terminal backgrounds almost all fall in L\\* 0–22. The panel baseline is 27.5, with the small dark-canvas
adjustment above: on the brightest
canvas in the set (Catppuccin Frappé `#303446`, L\\* 22.0) they are still 5.5 L\\* brighter than the
background — just past the "you can tell it's a panel" line — and 27.5 brighter on pure black (the
same magnitude as pi's built-in dark on a black background). Terminals with backgrounds brighter
than L\\* 22 are outside the design envelope.
The image below shows every theme's actual UI backgrounds on its own official canvas (generated
with `--preview`):

![ui-layer](../preview/ui-layer.png)

The thinking-level border colors encode only the level: five levels, five colors, low-stimulation,
no alarm colors such as red or yellow, and identical across themes.

## Foreground layer: how bright a terminal background each theme supports

The foregrounds are official colors, but the canvas is the terminal's own background, so how bright
a background each theme stays readable on differs from theme to theme. `--check` recomputes every
canvas foreground against each background in the table above and reports the brightest background on
which everything still passes 3:1 / 4.5:1; on
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
borders) prefer hex values from the official palettes, with roles mapped per the original authors'
highlight definitions; the sources are documented in the comment block above each theme in
`build_themes.py`. When the official ramp has no suitable brighter step, two official colors from the
same theme are mixed in sRGB: Nord's tool output and readable red, Dracula's secondary/comments,
Miramare's status/comments, and Oceanic Next's and Material's status/comments. These mixes preserve
each palette's identity without importing hues from another theme.

## Readability fixes and remaining trade-offs

Earlier versions accepted low-contrast residuals through a `KNOWN` allowlist. User feedback prompted
fixes for every exception, and the allowlist has been removed. `--check` now strictly enforces body
text ≥ 4.5:1 and every other readable element ≥ 3:1 for every checked readable foreground/background
pair in all 25 themes.

- Coverage: Markdown and syntax tokens are currently measured only on the canvas; their combinations
  inside message panels and tool boxes are not yet fully checked. "Passes" therefore refers to the
  reported pairs, not every possible rendering combination. The changed One Dark / Tokyo Night comments
  and URLs were separately verified above 3:1 on those extra surfaces; complete panel coverage for the
  other themes remains follow-up work.
- One Dark body text measures 6.6:1 on canvas, below the 7:1 high-contrast bar, and 4.64:1 on its
  theme-tinted selection background, still above the body-text floor.
- The 3:1 floor for non-body elements does not mean all text reaches 4.5:1: some official Solarized
  status colors, Monokai quotes and tool output, and similar secondary elements remain in the 3–4.5:1
  range to preserve the original hierarchy.
- Text hierarchy: Dracula officially has just one gray (comment), so muted still equals dim after the
  readability lift and the three text levels collapse to two; One Dark's body vs. secondary text differ
  by only about ΔL\\* 5 (official fg and statusFg are close to begin with).
- Synthwave '84's body text is the official `colors.foreground` pure white `#FFFFFF` (upstream has
  no editor.foreground), among the brightest body text in the set.

Intentional role or value deviations (official colors, or documented mixes of two official colors
from the same theme; re-verified hex-by-hex against upstream on 2026-09-19):

- **Readability-driven**: One Dark on-panel text uses bright foreground `#D7DAE0`, and comments use
  statusFg (5.65:1 on canvas and at least 4.26:1 in message panels/tool boxes; wordBorder reaches only
  2.89:1 on message panels); Nord uses nord4 for body, nord6
  for elevated text, nord8 for secondary text, nord9 for status/comments/URLs, `#ACC0D5` for tool
  output (60% nord9 + 40% nord6, 5.92:1 in boxes), and `#C87D86` for error/diff deletion
  (80% nord11 + 20% nord6, at least 4.00:1 on canvas and 3.54:1 in boxes); Dracula uses `#8894B8`
  for muted/dim/comments (75% comment + 25% fg, 4.73:1) and fg for tool titles; Tokyo Night uses fg_dark
  for comments/URLs (8.10:1 on canvas and at least 5.38:1 in message panels/tool boxes; dark5 reaches
  only 2.80:1 on message panels) and red for diff deletion; Solarized uses the base2/base1/base0 ramp above;
  Monokai uses `editorLineNumber.activeForeground` `#C2C2BF` for tool titles and invalid red for diff
  deletion (at least 3.13:1 in boxes); Kanagawa uses waveRed for diff deletion and ui.special's
  springViolet1 for borders; Miramare uses orange for secondary/quotes/borders and `#938C7B` for
  status/comments (60% lightGrey + 40% fg, 4.55:1); Noctis uses official TEXT for in-box secondary
  text; Oceanic Next uses `#A7ADBA` for secondary text and `#86909C` for status/comments/URLs
  (an equal comment/base04 mix, 4.50:1); Material uses base04 for borders/tool titles and `#839DA8`
  for status/comments (an equal base03/base04 mix, 4.61:1); Catppuccin Frappé / Macchiato use overlay1
  for link URLs; Andromeda uses blue for labels because pink is too dark on panels.
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
