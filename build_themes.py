#!/usr/bin/env python3
"""pi-flow-themes: pi themes from official palettes (hand-mapped roles, script-assembled JSON).

Principle: 背景承载状态, 前景承载个性.
  * UI (background/structural) layer  = one shared set (UI below): user/tool panels,
    green/red state boxes, selection, search, lines, scrollbar, and the thinking-level ramp
    (input-box border) — identical on every theme.
    Neutral gray pinned at CIE L* >= 27.5 so it reads on any dark terminal background
    (pi has no background token: the canvas is whatever the terminal paints).
  * Identity (foreground) layer       = the palette's official colors only, mapped to pi
    tokens by the theme author's own role definitions (cited per theme).

Usage:
  python3 build_themes.py            # write themes/flow-*.json
  python3 build_themes.py --check    # + contrast report (FLOOR + KNOWN allowlist), canvas ceiling per
                                     #   terminal background, sources/theme-sources.json completeness,
                                     #   near-duplicate report; exit 1 on any unexpected finding
  python3 build_themes.py --preview  # + preview/handwritten.png (all themes) and
                                     #   preview/ui-layer.png (shared UI layer on each terminal bg)
  python3 build_themes.py --measure  # metrics cited in README and docs/design.md: UI layer L*, state-box dE,
                                     #   panel dL* per terminal bg, full per-theme contrast table
  python3 build_themes.py --measure '#2E4931' '#414141' ...   # L* of each hex + pairwise contrast / dE
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "themes"
SOURCES = ROOT / "sources" / "theme-sources.json"   # locked upstream refs, one entry per theme
SCHEMA = ("https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/"
          "src/modes/interactive/theme/theme-schema.json")

# ---------------------------------------------------------------- shared UI layer
# Terminal canvas range this must survive (defaults measured from each terminal's source, CIE L*):
#   kitty / Windows Terminal Vintage 0 · WT Campbell 3 · Alacritty & VS Code Dark Modern panel 8 ·
#   GNOME dark & VS Code Dark+ 11 · Konsole Breeze 15 · Ghostty & One Half Dark 18 ·
#   WezTerm & GNOME Tango dark 21 · the 25 palettes' own canvases 8.5–22.0 (Catppuccin Frappé).
# Panels sit at L* 27.5: dL* >= 5.5 on the brightest canvas in range (22), 27.5 on pure black.
TERMINALS = [  # (label, default background) — rows of preview/ui-layer.png
    ("kitty / Windows Terminal Vintage", "#000000"),
    ("Windows Terminal Campbell", "#0C0C0C"),
    ("Alacritty / VS Code Dark Modern terminal", "#181818"),
    ("GNOME dark / VS Code Dark+", "#1E1E1E"),
    ("Konsole Breeze", "#232627"),
    ("Ghostty / One Half Dark", "#282C34"),
    ("WezTerm default", "#333333"),
    ("GNOME Tango dark", "#2E3436"),
]
UI = {
    "userMessageBg": "#414141", "customMessageBg": "#414141",                              # L* 27.5, neutral
    # pending carries a state signal too: same L*, faint cool tint (hue 225, 8%), dE 6 vs the
    # user panel — the same distance pi's own dark theme uses between its user and pending boxes.
    "toolPendingBg": "#3E4049",
    # success: hue 125 (true green; the earlier hue-150 tint read bluish on cool canvases).
    # error: hue 355 at 28% (a* +19) so it reads red rather than brown, still L* 28.3.
    "toolSuccessBg": "#2E4931", "toolErrorBg": "#61373A",                                   # dE vs user panel 20 / 20
    "selectedBg": "#474747", "searchMatchBg": "#4E4E4E",                                    # L* 30 / 33
    "borderMuted": "#575757", "mdCodeBlockBorder": "#575757", "mdHr": "#575757",            # L* 37
    "scrollbarTrack": "#414141", "scrollbarThumb": "#727272",                               # L* 27.5 / 48
    "thinkingOff": "#575757", "thinkingMinimal": "#727272",
    # thinking level = input-box border. Fixed across themes (user decision): five distinct hues,
    # teal -> blue -> violet -> purple -> magenta, low-stimulus, never red/yellow (alarm hues).
    "thinkingLow": "#5EA190", "thinkingMedium": "#6E96AA", "thinkingHigh": "#8985B7",
    "thinkingXhigh": "#AB85B7", "thinkingMax": "#B66D9D",
}

# foreground tokens that default to another *token* ("@name") unless the theme says otherwise
# (palette names may coincide with token names, e.g. rose-pine "muted"/"text": "@" disambiguates)
DEFAULTS = {
    "userMessageText": "@text", "customMessageText": "@text", "toolTitle": "@text",
    "searchMatchText": "@text", "mdCodeBlock": "@text",
    "toolOutput": "@muted", "toolDiffContext": "@muted", "mdQuote": "@muted", "thinkingText": "@muted",
    "mdQuoteBorder": "@dim", "mdLinkUrl": "@dim",
    "toolDiffAdded": "@success", "toolDiffRemoved": "@error", "bashMode": "@warning",
    "borderAccent": "@accent", "mdListBullet": "@accent", "mdLink": "@accent",
}
RAMP = ("thinkingLow", "thinkingMedium", "thinkingHigh", "thinkingXhigh", "thinkingMax")   # in UI
TOKENS = [  # pi theme-schema order
    "accent", "border", "borderAccent", "borderMuted", "success", "error", "warning", "muted", "dim",
    "text", "thinkingText", "selectedBg", "scrollbarTrack", "scrollbarThumb", "searchMatchBg",
    "searchMatchText", "userMessageBg", "userMessageText", "customMessageBg", "customMessageText",
    "customMessageLabel", "toolPendingBg", "toolSuccessBg", "toolErrorBg", "toolTitle", "toolOutput",
    "mdHeading", "mdLink", "mdLinkUrl", "mdCode", "mdCodeBlock", "mdCodeBlockBorder", "mdQuote",
    "mdQuoteBorder", "mdHr", "mdListBullet", "toolDiffAdded", "toolDiffRemoved", "toolDiffContext",
    "syntaxComment", "syntaxKeyword", "syntaxFunction", "syntaxVariable", "syntaxString", "syntaxNumber",
    "syntaxType", "syntaxOperator", "syntaxPunctuation", "thinkingOff", "thinkingMinimal", *RAMP, "bashMode",
]

# ---------------------------------------------------------------- themes
# Each theme: official palette (hex verified against the upstream source) and a role map using
# palette names; tokens not listed fall through DEFAULTS.
THEMES = {
    # Binaryify/OneDark-Pro tokenColors + joshdick/onedark.vim. Panel text uses the palette's
    # bright fg (#D7DAE0): the body fg is a muted gray-blue that washes out on gray panels.
    "flow-one-dark-pro": dict(
        bg="#282C34",
        palette={"fg": "#ABB2BF", "fgBright": "#D7DAE0", "statusFg": "#9DA5B4", "wordBorder": "#7F848E",
                 "comment": "#5C6370", "red": "#E06C75", "green": "#98C379", "yellow": "#E5C07B",
                 "orange": "#D19A66", "blue": "#61AFEF", "purple": "#C678DD", "cyan": "#56B6C2"},
        roles={"text": "fg", "muted": "statusFg", "dim": "wordBorder", "accent": "blue", "border": "blue",
               "borderAccent": "cyan", "success": "green", "error": "red", "warning": "yellow",
               "userMessageText": "fgBright", "customMessageText": "fgBright", "toolTitle": "fgBright",
               "searchMatchText": "fgBright", "toolOutput": "fg", "customMessageLabel": "purple",
               "mdHeading": "red", "mdLink": "blue", "mdLinkUrl": "cyan", "mdCode": "green", "mdListBullet": "blue",
               "syntaxComment": "comment", "syntaxKeyword": "purple", "syntaxFunction": "blue",
               "syntaxVariable": "red", "syntaxString": "green", "syntaxNumber": "orange", "syntaxType": "yellow",
               "syntaxOperator": "cyan", "syntaxPunctuation": "fg"},
        info="#3A3A2E"),

    # nordtheme.com/docs/colors-and-palettes + nordtheme/vim. text=nord6 (elevated) / muted=nord4 (base):
    # pi needs a 3-step hierarchy and Nord has no gray between nord3 and nord4.
    "flow-nord": dict(
        bg="#2E3440",
        palette={"nord3": "#4C566A", "nord3_bright": "#616E88", "nord4": "#D8DEE9", "nord6": "#ECEFF4",
                 "nord7": "#8FBCBB", "nord8": "#88C0D0", "nord9": "#81A1C1", "nord10": "#5E81AC",
                 "nord11": "#BF616A", "nord13": "#EBCB8B", "nord14": "#A3BE8C", "nord15": "#B48EAD"},
        roles={"text": "nord6", "muted": "nord4", "dim": "nord3_bright", "accent": "nord8", "border": "nord10",
               "success": "nord14", "error": "nord11", "warning": "nord13", "toolTitle": "nord8",
               "customMessageLabel": "nord15",
               "mdHeading": "nord8", "mdCode": "nord7", "mdQuoteBorder": "nord10",
               "syntaxComment": "nord3_bright", "syntaxKeyword": "nord9", "syntaxFunction": "nord8",
               "syntaxVariable": "nord4", "syntaxString": "nord14", "syntaxNumber": "nord15", "syntaxType": "nord7",
               "syntaxOperator": "nord9", "syntaxPunctuation": "nord4"},
        info="#45443A"),

    # spec.draculatheme.com (syntax + markup §2.2) + dracula/vim. Dracula has one gray: comment.
    "flow-dracula": dict(
        bg="#282A36",
        palette={"fg": "#F8F8F2", "comment": "#6272A4", "pink": "#FF79C6", "purple": "#BD93F9", "cyan": "#8BE9FD",
                 "green": "#50FA7B", "orange": "#FFB86C", "red": "#FF5555", "yellow": "#F1FA8C"},
        roles={"text": "fg", "muted": "comment", "dim": "comment", "accent": "purple", "border": "comment",
               "borderAccent": "pink", "success": "green", "error": "red", "warning": "orange",
               "customMessageLabel": "purple", "toolTitle": "pink", "toolOutput": "fg", "toolDiffContext": "fg",
               "mdHeading": "purple", "mdLink": "pink", "mdLinkUrl": "cyan", "mdCode": "green",
               "mdListBullet": "cyan", "mdQuote": "yellow",
               "syntaxComment": "comment", "syntaxKeyword": "pink", "syntaxFunction": "green", "syntaxVariable": "fg",
               "syntaxString": "yellow", "syntaxNumber": "purple", "syntaxType": "cyan", "syntaxOperator": "pink",
               "syntaxPunctuation": "fg"},
        info="#3D3A2E"),

    # morhetz/gruvbox colors/gruvbox.vim highlight links (dark medium).
    "flow-gruvbox": dict(
        bg="#282828",
        palette={"gray": "#928374", "light0": "#FBF1C7", "light1": "#EBDBB2", "light3": "#BDAE93",
                 "light4": "#A89984", "red": "#FB4934", "green": "#B8BB26", "yellow": "#FABD2F", "blue": "#83A598",
                 "purple": "#D3869B", "aqua": "#8EC07C", "orange": "#FE8019", "neutral_blue": "#458588"},
        roles={"text": "light1", "muted": "light3", "dim": "light4", "accent": "orange", "border": "neutral_blue",
               "borderAccent": "aqua", "success": "green", "error": "red", "warning": "yellow",
               "searchMatchText": "light0", "customMessageLabel": "purple", "toolOutput": "light4",
               "mdHeading": "green", "mdLink": "gray", "mdLinkUrl": "purple", "mdCode": "aqua",
               "mdListBullet": "gray", "mdQuote": "gray",
               "syntaxComment": "gray", "syntaxKeyword": "red", "syntaxFunction": "green", "syntaxVariable": "blue",
               "syntaxString": "green", "syntaxNumber": "purple", "syntaxType": "yellow",
               "syntaxOperator": "light1", "syntaxPunctuation": "light1"},
        info="#32302F"),

    # catppuccin/catppuccin docs/style-guide.md (Code Editors table) + catppuccin/nvim.
    "flow-catppuccin-mocha": dict(
        bg="#1E1E2E",
        palette={"overlay0": "#6C7086", "overlay1": "#7F849C", "overlay2": "#9399B2", "subtext0": "#A6ADC8",
                 "subtext1": "#BAC2DE", "text": "#CDD6F4", "lavender": "#B4BEFE", "blue": "#89B4FA",
                 "sapphire": "#74C7EC", "sky": "#89DCEB", "teal": "#94E2D5", "green": "#A6E3A1",
                 "yellow": "#F9E2AF", "peach": "#FAB387", "red": "#F38BA8", "mauve": "#CBA6F7", "pink": "#F5C2E7"},
        roles={"text": "text", "muted": "subtext0", "dim": "overlay1", "accent": "blue", "border": "overlay0",
               "success": "green", "error": "red", "warning": "yellow", "customMessageLabel": "mauve",
               "mdHeading": "lavender", "mdLinkUrl": "overlay0", "mdCode": "teal", "mdQuote": "subtext1",
               "mdQuoteBorder": "mauve", "mdListBullet": "mauve", "bashMode": "peach",
               "syntaxComment": "overlay2", "syntaxKeyword": "mauve", "syntaxFunction": "blue",
               "syntaxVariable": "text", "syntaxString": "green", "syntaxNumber": "peach", "syntaxType": "yellow",
               "syntaxOperator": "sky", "syntaxPunctuation": "overlay2"},
        info="#3A3728"),

    # folke/tokyonight.nvim groups/base.lua + treesitter.lua + colors/init.lua (night).
    "flow-tokyo-night": dict(
        bg="#1A1B26",
        palette={"fg": "#C0CAF5", "fg_dark": "#A9B1D6", "dark5": "#737AA2", "dark3": "#545C7E",
                 "comment": "#565F89", "blue": "#7AA2F7", "blue0": "#3D59A1", "blue1": "#2AC3DE", "blue5": "#89DDFF",
                 "cyan": "#7DCFFF", "magenta": "#BB9AF7", "purple": "#9D7CD8", "orange": "#FF9E64",
                 "yellow": "#E0AF68", "green": "#9ECE6A", "green1": "#73DACA", "teal": "#1ABC9C",
                 "red": "#F7768E", "red1": "#DB4B4B"},
        roles={"text": "fg", "muted": "fg_dark", "dim": "dark5", "accent": "blue", "border": "blue",
               "borderAccent": "cyan", "success": "green", "error": "red1", "warning": "yellow",
               "customMessageLabel": "magenta", "toolDiffRemoved": "red",
               "mdHeading": "blue", "mdLink": "teal", "mdLinkUrl": "comment", "mdCode": "green",
               "mdQuoteBorder": "dark3", "mdListBullet": "blue5",
               "syntaxComment": "comment", "syntaxKeyword": "purple", "syntaxFunction": "blue", "syntaxVariable": "fg",
               "syntaxString": "green", "syntaxNumber": "orange", "syntaxType": "blue1", "syntaxOperator": "blue5",
               "syntaxPunctuation": "fg_dark"},
        info="#33342A"),

    # altercation/vim-colors-solarized. text=base1 (emphasized content) for TUI legibility;
    # toolTitle is the sole custom foreground: the palette jumps from base1 (3.72:1 on the shared
    # success box) to base2 (8.11:1), so use their 35% sRGB mix for a balanced 5.01:1.
    "flow-solarized-dark": dict(
        bg="#002B36",
        palette={"base01": "#586E75", "base0": "#839496", "base1": "#93A1A1", "base2": "#EEE8D5",
                 "yellow": "#B58900", "orange": "#CB4B16", "red": "#DC322F", "magenta": "#D33682",
                 "violet": "#6C71C4", "blue": "#268BD2", "cyan": "#2AA198", "green": "#859900"},
        roles={"text": "base1", "muted": "base0", "dim": "base01", "accent": "blue", "border": "blue",
               "borderAccent": "cyan", "success": "green", "error": "red", "warning": "yellow",
               "searchMatchText": "base2", "customMessageLabel": "violet", "toolTitle": "#B3BAB3",
               "mdHeading": "orange", "mdLink": "violet", "mdCode": "cyan", "mdListBullet": "blue",
               "syntaxComment": "base01", "syntaxKeyword": "green", "syntaxFunction": "blue",
               "syntaxVariable": "blue", "syntaxString": "cyan", "syntaxNumber": "cyan", "syntaxType": "yellow",
               "syntaxOperator": "green", "syntaxPunctuation": "base0"},
        info="#2B3A2A"),

    # microsoft/vscode extensions/theme-monokai tokenColors (original Monokai values). toolTitle =
    # fgSubtle (editorLineNumber.activeForeground, 5.56:1 in boxes): fg #F8F8F2 glares at L* 97 and
    # the accent green would sit on the green success box.
    "flow-monokai": dict(
        bg="#272822",
        palette={"fg": "#F8F8F2", "fgSubtle": "#C2C2BF", "lineNumber": "#90908A", "comment": "#88846F",
                 "focus": "#75715E", "focusBorder": "#99947C", "pink": "#F92672", "orange": "#FD971F",
                 "yellow": "#E6DB74", "green": "#A6E22E", "cyan": "#66D9EF", "purple": "#AE81FF",
                 "invalid": "#F44747"},
        roles={"text": "fg", "muted": "fgSubtle", "dim": "lineNumber", "accent": "green", "border": "focusBorder",
               "borderAccent": "cyan", "success": "green", "error": "invalid", "warning": "yellow",
               "toolTitle": "fgSubtle",
               "customMessageLabel": "purple", "toolOutput": "lineNumber", "toolDiffContext": "lineNumber",
               "toolDiffRemoved": "pink",
               "mdHeading": "green", "mdLink": "purple", "mdLinkUrl": "yellow", "mdCode": "orange",
               "mdQuote": "focus", "mdQuoteBorder": "focus", "mdListBullet": "green",
               "syntaxComment": "comment", "syntaxKeyword": "pink", "syntaxFunction": "green", "syntaxVariable": "fg",
               "syntaxString": "yellow", "syntaxNumber": "purple", "syntaxType": "cyan", "syntaxOperator": "pink",
               "syntaxPunctuation": "fg"},
        info="#3B3A2A"),

    # rebelot/kanagawa.nvim themes.lua (wave) + highlights. diff-removed uses waveRed (syn.special2):
    # vcs.removed autumnRed is 2.1:1 inside boxes.
    "flow-kanagawa": dict(
        bg="#1F1F28",
        palette={"sumiInk6": "#54546D", "waveBlue2": "#2D4F67", "fujiWhite": "#DCD7BA", "oldWhite": "#C8C093",
                 "fujiGray": "#727169", "springViolet1": "#938AA9", "springViolet2": "#9CABCA",
                 "oniViolet": "#957FB8", "crystalBlue": "#7E9CD8", "springBlue": "#7FB4CA", "waveAqua2": "#7AA89F",
                 "springGreen": "#98BB6C", "autumnGreen": "#76946A", "boatYellow2": "#C0A36E",
                 "carpYellow": "#E6C384", "sakuraPink": "#D27E99", "waveRed": "#E46876", "samuraiRed": "#E82424",
                 "roninYellow": "#FF9E3B"},
        roles={"text": "fujiWhite", "muted": "oldWhite", "dim": "fujiGray", "accent": "crystalBlue",
               "border": "springViolet1", "borderAccent": "springBlue",   # border = ui.special (waveBlue2 is a bg, 1.9:1)
               "success": "springGreen",
               "error": "samuraiRed", "warning": "roninYellow", "customMessageLabel": "oniViolet",
               "toolDiffAdded": "autumnGreen", "toolDiffRemoved": "waveRed",
               "mdHeading": "crystalBlue", "mdLink": "springBlue", "mdCode": "springGreen",
               "mdQuoteBorder": "sumiInk6", "mdListBullet": "springViolet1", "bashMode": "carpYellow",
               "syntaxComment": "fujiGray", "syntaxKeyword": "oniViolet", "syntaxFunction": "crystalBlue",
               "syntaxVariable": "fujiWhite", "syntaxString": "springGreen", "syntaxNumber": "sakuraPink",
               "syntaxType": "waveAqua2", "syntaxOperator": "boatYellow2", "syntaxPunctuation": "springViolet2"},
        info="#49443C"),

    # rose-pine/neovim lua/rose-pine.lua + config.lua groups (main).
    "flow-rose-pine": dict(
        bg="#191724",
        palette={"muted": "#6E6A86", "subtle": "#908CAA", "text": "#E0DEF4", "love": "#EB6F92", "gold": "#F6C177",
                 "rose": "#EBBCBA", "pine": "#31748F", "foam": "#9CCFD8", "iris": "#C4A7E7", "leaf": "#95B1AC"},
        roles={"text": "text", "muted": "subtle", "dim": "muted", "accent": "rose", "border": "muted",
               "borderAccent": "foam", "success": "leaf", "error": "love", "warning": "gold",
               "customMessageLabel": "iris", "toolDiffAdded": "foam",
               "mdHeading": "foam", "mdLink": "foam", "mdLinkUrl": "iris", "mdCode": "rose", "mdListBullet": "pine",
               "syntaxComment": "subtle", "syntaxKeyword": "pine", "syntaxFunction": "rose", "syntaxVariable": "text",
               "syntaxString": "gold", "syntaxNumber": "gold", "syntaxType": "foam", "syntaxOperator": "subtle",
               "syntaxPunctuation": "subtle"},
        info="#3A3428"),

    # ---------------------------------------------------- expansion set (docs/plans/authoritative-theme-expansion.md)

    # ayu-theme/ayu-colors themes/mirage.yaml, colors resolved by the official generator
    # (src/generated/mirage.ts). toolTitle = common.accent.tint.
    "flow-ayu-mirage": dict(
        bg="#242936",
        palette={"fg": "#CCCAC2", "gray2": "#AFB7C1", "comment": "#6E7C8F", "red": "#F28779",
                 "pink": "#F29E74", "orange": "#FFA659", "peach": "#D9BE98", "yellow": "#FFCD66",
                 "green": "#D5FF80", "teal": "#95E6CB", "indigo": "#5CCFE6", "blue": "#73D0FF",
                 "purple": "#DFBFFF", "accentTint": "#FFCC66", "vcsAdded": "#87D96C", "uiError": "#FF6666"},
        roles={"text": "fg", "muted": "gray2", "dim": "comment", "accent": "accentTint", "border": "blue",
               "success": "vcsAdded", "error": "uiError", "warning": "orange", "toolTitle": "accentTint",
               "customMessageLabel": "purple",
               "mdHeading": "red", "mdLink": "blue", "mdLinkUrl": "teal", "mdCode": "teal", "mdListBullet": "orange",
               "syntaxComment": "comment", "syntaxKeyword": "orange", "syntaxFunction": "yellow",
               "syntaxVariable": "fg", "syntaxString": "green", "syntaxNumber": "purple", "syntaxType": "blue",
               "syntaxOperator": "pink", "syntaxPunctuation": "fg"},
        info="#3D3A2E"),

    # catppuccin/palette (frappe) + catppuccin/nvim role assignments, same mapping as mocha
    # (Comment/Delimiter = overlay2, quote = subtext1). mdLinkUrl stays on dim = overlay1: mocha's
    # overlay0 is 2.87:1 on this lighter canvas.
    "flow-catppuccin-frappe": dict(
        bg="#303446",
        palette={"overlay1": "#838BA7", "overlay2": "#949CBB", "subtext0": "#A5ADCE", "subtext1": "#B5BFE2",
                 "text": "#C6D0F5", "lavender": "#BABBF1",
                 "blue": "#8CAAEE", "sapphire": "#85C1DC", "sky": "#99D1DB", "teal": "#81C8BE",
                 "green": "#A6D189", "yellow": "#E5C890", "peach": "#EF9F76", "red": "#E78284",
                 "mauve": "#CA9EE6", "flamingo": "#EEBEBE"},
        roles={"text": "text", "muted": "subtext0", "dim": "overlay1", "accent": "blue", "border": "overlay1",
               "success": "green", "error": "red", "warning": "yellow", "customMessageLabel": "mauve",
               "mdHeading": "lavender", "mdCode": "teal", "mdQuote": "subtext1",
               "mdQuoteBorder": "mauve", "mdListBullet": "mauve", "bashMode": "peach",
               "syntaxComment": "overlay2", "syntaxKeyword": "mauve", "syntaxFunction": "blue",
               "syntaxVariable": "text", "syntaxString": "green", "syntaxNumber": "peach", "syntaxType": "yellow",
               "syntaxOperator": "sky", "syntaxPunctuation": "overlay2"},
        info="#3A3728"),

    # catppuccin/palette (macchiato) + catppuccin/nvim role assignments, same mapping as mocha
    # (Comment/Delimiter = overlay2, quote = subtext1); mdLinkUrl on dim = overlay1 like frappe.
    "flow-catppuccin-macchiato": dict(
        bg="#24273A",
        palette={"overlay1": "#8087A2", "overlay2": "#939AB7", "subtext0": "#A5ADCB", "subtext1": "#B8C0E0",
                 "text": "#CAD3F5", "lavender": "#B7BDF8",
                 "blue": "#8AADF4", "sapphire": "#7DC4E4", "sky": "#91D7E3", "teal": "#8BD5CA",
                 "green": "#A6DA95", "yellow": "#EED49F", "peach": "#F5A97F", "red": "#ED8796",
                 "mauve": "#C6A0F6", "flamingo": "#F0C6C6"},
        roles={"text": "text", "muted": "subtext0", "dim": "overlay1", "accent": "blue", "border": "overlay1",
               "success": "green", "error": "red", "warning": "yellow", "customMessageLabel": "mauve",
               "mdHeading": "lavender", "mdCode": "teal", "mdQuote": "subtext1",
               "mdQuoteBorder": "mauve", "mdListBullet": "mauve", "bashMode": "peach",
               "syntaxComment": "overlay2", "syntaxKeyword": "mauve", "syntaxFunction": "blue",
               "syntaxVariable": "text", "syntaxString": "green", "syntaxNumber": "peach", "syntaxType": "yellow",
               "syntaxOperator": "sky", "syntaxPunctuation": "overlay2"},
        info="#3A3728"),

    # sainnhe/everforest autoload/everforest.vim (dark medium) + colors/everforest.vim highlight groups.
    # toolTitle = blue (Identifier): 4.57:1 in boxes, the author's own UI-accent-adjacent voice.
    "flow-everforest": dict(
        bg="#2D353B",
        palette={"fg": "#D3C6AA", "grey0": "#7A8478", "grey1": "#859289", "grey2": "#9DA9A0",
                 "red": "#E67E80", "orange": "#E69875", "yellow": "#DBBC7F", "green": "#A7C080",
                 "aqua": "#83C092", "blue": "#7FBBB3", "purple": "#D699B6"},
        roles={"text": "fg", "muted": "grey2", "dim": "grey1", "accent": "blue", "border": "grey1",
               "borderAccent": "aqua", "success": "green", "error": "red", "warning": "yellow",
               "toolTitle": "blue", "customMessageLabel": "purple",
               "mdHeading": "orange", "mdLink": "purple", "mdLinkUrl": "blue", "mdCode": "green",
               "mdQuoteBorder": "grey1", "mdListBullet": "red",
               "syntaxComment": "grey1", "syntaxKeyword": "red", "syntaxFunction": "green", "syntaxVariable": "blue",
               "syntaxString": "green", "syntaxNumber": "purple", "syntaxType": "yellow", "syntaxOperator": "orange",
               "syntaxPunctuation": "fg"},
        info="#3A3C33"),

    # primer/github-vscode-theme src/classic (dark): scales reverse for dark (primer.js), so e.g.
    # keyword = dark red[6] = light red[3]. toolTitle = the constant/support blue; functions are
    # `entity.name` = purple[6] (blue is support/constant only).
    "flow-github-dark": dict(
        bg="#24292E",
        palette={"fg": "#E1E4E8", "fgMuted": "#959DA5", "comment": "#6A737D", "blue": "#79B8FF",
                 "string": "#9ECBFF", "purple": "#B392F0", "orange": "#FFAB70", "red": "#F97583",
                 "green": "#85E89D", "redSoft": "#FDAEB7"},
        roles={"text": "fg", "muted": "fgMuted", "dim": "comment", "accent": "blue", "border": "comment",
               "success": "green", "error": "red", "warning": "orange", "toolTitle": "blue",
               "customMessageLabel": "purple", "toolDiffRemoved": "redSoft",
               "mdHeading": "blue", "mdLink": "blue", "mdLinkUrl": "comment", "mdCode": "blue",
               "mdQuote": "green", "mdListBullet": "orange",
               "syntaxComment": "comment", "syntaxKeyword": "red", "syntaxFunction": "purple",
               "syntaxVariable": "orange", "syntaxString": "string", "syntaxNumber": "blue",
               "syntaxType": "purple", "syntaxOperator": "fg", "syntaxPunctuation": "fg"},
        info="#33342A"),

    # savq/melange-nvim lua/melange/palettes/dark.lua + colors/melange.lua groups.
    # Diffs are background-based upstream (d.green/d.red); pi needs fg, so use the b/c ramps.
    # Delimiter (syntaxPunctuation) is d.yellow by design: delimiters sit low. toolTitle = Function yellow.
    "flow-melange": dict(
        bg="#292522",
        palette={"fg": "#ECE1D7", "com": "#C1A78E", "ui": "#867462",
                 "bRed": "#D47766", "bYellow": "#EBC06D", "bGreen": "#85B695", "bCyan": "#89B3B6",
                 "bBlue": "#A3A9CE", "bMagenta": "#CF9BC2", "cRed": "#BD8183", "cYellow": "#E49B5D",
                 "cGreen": "#78997A", "cCyan": "#7B9695", "cBlue": "#7F91B2", "cMagenta": "#B380B0",
                 "dYellow": "#8B7449"},
        roles={"text": "fg", "muted": "com", "dim": "ui", "accent": "bYellow", "border": "ui",
               "borderAccent": "bYellow", "success": "bGreen", "error": "cRed", "warning": "bYellow",
               "toolTitle": "bYellow", "customMessageLabel": "bMagenta",
               "toolDiffAdded": "bGreen", "toolDiffRemoved": "cRed",
               "mdHeading": "cYellow", "mdLink": "bBlue", "mdLinkUrl": "cBlue", "mdCode": "bCyan",
               "mdQuoteBorder": "ui", "mdListBullet": "dYellow",
               "syntaxComment": "com", "syntaxKeyword": "cYellow", "syntaxFunction": "bYellow",
               "syntaxVariable": "fg", "syntaxString": "bBlue", "syntaxNumber": "bMagenta",
               "syntaxType": "cCyan", "syntaxOperator": "bRed", "syntaxPunctuation": "dYellow"},
        info="#3A3428"),

    # franbach/miramare colors/miramare.vim. mdQuote is Grey upstream (unreadable on terminal canvas),
    # falls back to @muted=orange; that and the dark comment are the author's low-contrast look.
    "flow-miramare": dict(
        bg="#2A2426",
        palette={"fg": "#E6D6AC", "grey": "#444444", "lightGrey": "#5B5B5B", "red": "#E68183",
                 "orange": "#E39B7B", "yellow": "#D9BB80", "green": "#87AF87", "cyan": "#87C095",
                 "blue": "#89BEBA", "purple": "#D3A0BC"},
        roles={"text": "fg", "muted": "orange", "dim": "lightGrey", "accent": "orange", "border": "orange",
               "success": "green", "error": "red", "warning": "yellow", "toolTitle": "yellow",
               "customMessageLabel": "purple",
               "mdHeading": "red", "mdLink": "purple", "mdLinkUrl": "blue", "mdCode": "green",
               "mdQuoteBorder": "orange", "mdListBullet": "red",
               "syntaxComment": "lightGrey", "syntaxKeyword": "red", "syntaxFunction": "green",
               "syntaxVariable": "blue", "syntaxString": "green", "syntaxNumber": "purple", "syntaxType": "yellow",
               "syntaxOperator": "orange", "syntaxPunctuation": "fg"},
        info="#3A342A"),

    # atomiks/moonlight-vscode-theme src/colors.ts + moonlight.json + ui.json. toolTitle = textLink sky.
    "flow-moonlight": dict(
        bg="#222436",
        palette={"text": "#C8D3F5", "gray9": "#B4C2F0", "gray8": "#A9B8E8", "desatGray": "#979BB6",
                 "satGray": "#7A88CF", "red": "#FF757F", "darkRed": "#FF5370", "orange": "#FF966C",
                 "yellow": "#FFC777", "green": "#C3E88D", "lightTeal": "#7AF8CA", "cyan": "#78DBFF",
                 "sky": "#60BDFF", "blue": "#7CAFFF", "indigo": "#AF9FFF", "purple": "#C4A2FF"},
        roles={"text": "text", "muted": "desatGray", "dim": "satGray", "accent": "blue", "border": "satGray",
               "success": "green", "error": "darkRed", "warning": "yellow", "toolTitle": "sky",
               "customMessageLabel": "purple",
               "mdHeading": "lightTeal", "mdLink": "sky", "mdLinkUrl": "cyan", "mdCode": "cyan",
               "mdQuoteBorder": "indigo", "mdListBullet": "blue",
               "syntaxComment": "satGray", "syntaxKeyword": "indigo", "syntaxFunction": "blue",
               "syntaxVariable": "text", "syntaxString": "lightTeal", "syntaxNumber": "orange",
               "syntaxType": "yellow", "syntaxOperator": "cyan", "syntaxPunctuation": "gray8"},
        info="#33342A"),

    # liviuschera/noctis themes/bordo.json. toolTitle: the UI accent pink is 4.37:1 in boxes -> text.
    # toolOutput/diffContext: comment is 2.3:1 in boxes -> official TEXT. toolDiffRemoved = TAG
    # (markup.deleted.diff).
    "flow-noctis-bordo": dict(
        bg="#322A2D",
        palette={"text": "#CBBEC2", "comment": "#8B747C", "description": "#BB778F", "keyword": "#DF769B", "variable": "#E4B781",
                 "annotation": "#D67E5C", "constant": "#D5971A", "tag": "#E66533", "string": "#49E9A6",
                 "number": "#7060EB", "func": "#16A3B6", "support": "#49D6E9", "misc": "#49ACE9",
                 "invalid": "#E3541C", "error": "#E34E1C", "warning": "#E69533", "vcsAdded": "#16B673",
                 "uiAccent": "#F18EB0"},
        roles={"text": "text", "muted": "description", "dim": "comment", "accent": "uiAccent", "border": "comment",
               "success": "vcsAdded", "error": "error", "warning": "warning", "customMessageLabel": "uiAccent",
               "toolOutput": "text", "toolDiffContext": "text", "toolDiffRemoved": "tag",
               "mdHeading": "keyword", "mdLink": "support", "mdCode": "annotation", "mdQuote": "constant",
               "mdListBullet": "keyword",
               "syntaxComment": "comment", "syntaxKeyword": "keyword", "syntaxFunction": "func",
               "syntaxVariable": "variable", "syntaxString": "string", "syntaxNumber": "number",
               "syntaxType": "support", "syntaxOperator": "misc", "syntaxPunctuation": "text"},
        info="#3C3033"),

    # liviuschera/noctis themes/sereno.json. toolTitle = the UI accent cyan (textLink) 5.57:1 in boxes.
    # toolOutput/diffContext: comment is 2.4:1 in boxes -> official TEXT. toolDiffRemoved = TAG
    # (markup.deleted.diff).
    "flow-noctis-sereno": dict(
        bg="#062E32",
        palette={"text": "#B2CACD", "comment": "#5B858B", "description": "#929EA0", "keyword": "#DF769B", "variable": "#E4B781",
                 "annotation": "#D67E5C", "constant": "#D5971A", "tag": "#E66533", "string": "#49E9A6",
                 "number": "#7060EB", "func": "#16A3B6", "support": "#49D6E9", "misc": "#49ACE9",
                 "invalid": "#E3541C", "error": "#E34E1C", "warning": "#E69533", "vcsAdded": "#16B673",
                 "uiAccent": "#40D4E7"},
        roles={"text": "text", "muted": "description", "dim": "comment", "accent": "uiAccent", "border": "comment",
               "success": "vcsAdded", "error": "error", "warning": "warning", "toolTitle": "uiAccent",
               "customMessageLabel": "keyword", "toolOutput": "text", "toolDiffContext": "text",
               "toolDiffRemoved": "tag",
               "mdHeading": "keyword", "mdLink": "support", "mdCode": "annotation", "mdQuote": "constant",
               "mdListBullet": "keyword",
               "syntaxComment": "comment", "syntaxKeyword": "keyword", "syntaxFunction": "func",
               "syntaxVariable": "variable", "syntaxString": "string", "syntaxNumber": "number",
               "syntaxType": "support", "syntaxOperator": "misc", "syntaxPunctuation": "text"},
        info="#2C3A2A"),

    # voronianski/oceanic-next-color-scheme Oceanic Next.tmTheme + the official extended palette
    # (base04 #A7ADBA for muted/border; comment #65737E stays as the author's deliberately dark comment).
    "flow-oceanic-next": dict(
        bg="#1B2B34",
        palette={"fg": "#CDD3DE", "fgDim": "#A7ADBA", "comment": "#65737E", "red": "#EC5F67", "orange": "#F99157",
                 "yellow": "#FAC863", "green": "#99C794", "teal": "#5FB3B3", "blue": "#6699CC",
                 "purple": "#C594C5", "magenta": "#BB80B3"},
        roles={"text": "fg", "muted": "fgDim", "dim": "comment", "accent": "blue", "border": "fgDim",
               "success": "green", "error": "red", "warning": "yellow", "customMessageLabel": "purple",
               "mdHeading": "green", "mdLink": "blue", "mdCode": "green", "mdListBullet": "red",
               "toolDiffAdded": "green", "toolDiffRemoved": "red",
               "syntaxComment": "comment", "syntaxKeyword": "purple", "syntaxFunction": "blue",
               "syntaxVariable": "fg", "syntaxString": "green", "syntaxNumber": "orange", "syntaxType": "yellow",
               "syntaxOperator": "teal", "syntaxPunctuation": "fg"},
        info="#2F3A33"),

    # robb0wen/synthwave-vscode themes/synthwave-color-theme.json. toolTitle = Function cyan.
    "flow-synthwave84": dict(
        bg="#262335",
        palette={"text": "#FFFFFF", "comment": "#848BBD", "punct": "#B6B1B1", "red": "#FE4450",
                 "orange": "#FF8B39", "yellow": "#FEDE5D", "green": "#72F1B8", "cyan": "#36F9F6",
                 "blue": "#2EE2FA", "pink": "#FF7EDB", "coral": "#F97E72"},
        roles={"text": "text", "muted": "punct", "dim": "comment", "accent": "pink", "border": "comment",
               "success": "green", "error": "red", "warning": "yellow", "toolTitle": "cyan",
               "customMessageLabel": "pink",
               "mdHeading": "pink", "mdLink": "green", "mdLinkUrl": "yellow", "mdCode": "cyan",
               "mdQuoteBorder": "comment", "mdListBullet": "pink", "toolDiffRemoved": "coral",
               "syntaxComment": "comment", "syntaxKeyword": "yellow", "syntaxFunction": "cyan",
               "syntaxVariable": "pink", "syntaxString": "orange", "syntaxNumber": "coral", "syntaxType": "red",
               "syntaxOperator": "yellow", "syntaxPunctuation": "punct"},
        info="#3C3040"),

    # EliverLara/Andromeda themes/Andromeda-color-theme.json. toolTitle = the UI accent cyan
    # (tab.activeBorder, list.activeSelectionForeground). Comment drops its 80% alpha.
    "flow-andromeda": dict(
        bg="#23262E",
        palette={"fg": "#D5CED9", "comment": "#A0A1A7", "lineNr": "#746F77", "cyan": "#00E8C6",
                 "orange": "#F39C12", "yellow": "#FFE66D", "pink": "#FF00AA", "hotPink": "#F92672",
                 "purple": "#C74DED", "blue": "#7CB7FF", "red": "#EE5D43", "green": "#96E072",
                 "error": "#FC644D", "warning": "#FF9F2E"},
        roles={"text": "fg", "muted": "comment", "dim": "lineNr", "accent": "cyan", "border": "lineNr",
               "success": "green", "error": "error", "warning": "warning", "toolTitle": "cyan",
               "customMessageLabel": "blue", "toolDiffRemoved": "red",
               "mdHeading": "pink", "mdLink": "blue", "mdLinkUrl": "lineNr", "mdCode": "green",
               "mdQuote": "comment", "mdListBullet": "cyan",
               "syntaxComment": "comment", "syntaxKeyword": "purple", "syntaxFunction": "yellow",
               "syntaxVariable": "cyan", "syntaxString": "green", "syntaxNumber": "orange", "syntaxType": "yellow",
               "syntaxOperator": "red", "syntaxPunctuation": "fg"},
        info="#33324A"),

    # tinted-theming/schemes base16/material.yaml + the Base16 styling spec role table.
    # toolTitle: base0D functions blue is 4.32:1 in boxes; base05 #EEFFFF glares at L* 99 -> base04
    # (spec "Dark Foreground", 5.91:1). border = base04: base03 (2.4:1) is the author's comment colour,
    # too dark for a structural frame.
    "flow-material": dict(
        bg="#263238",
        palette={"base03": "#546E7A", "base04": "#B2CCD6", "base05": "#EEFFFF", "base08": "#F07178",
                 "base09": "#F78C6C", "base0A": "#FFCB6B", "base0B": "#C3E88D", "base0C": "#89DDFF",
                 "base0D": "#82AAFF", "base0E": "#C792EA", "base0F": "#FF5370"},
        roles={"text": "base05", "muted": "base04", "dim": "base03", "accent": "base0D", "border": "base04",
               "success": "base0B", "error": "base08", "warning": "base0A", "toolTitle": "base04",
               "customMessageLabel": "base0E",
               "mdHeading": "base0D", "mdLink": "base08", "mdLinkUrl": "base09", "mdCode": "base0B",
               "mdQuote": "base0C", "mdListBullet": "base08",
               "syntaxComment": "base03", "syntaxKeyword": "base0E", "syntaxFunction": "base0D",
               "syntaxVariable": "base08", "syntaxString": "base0B", "syntaxNumber": "base09",
               "syntaxType": "base0A", "syntaxOperator": "base05", "syntaxPunctuation": "base05"},
        info="#2F3A33"),

    # tinted-theming/schemes base16/snazzy.yaml (after sindresorhus/hyper-snazzy) + Base16 styling spec.
    # toolTitle = base0D functions blue (5.21:1); base0E magenta is 3.82:1 in boxes.
    "flow-snazzy": dict(
        bg="#282A36",
        palette={"base03": "#78787E", "base04": "#A5A5A9", "base05": "#E2E4E5", "base08": "#FF5C57",
                 "base09": "#FF9F43", "base0A": "#F3F99D", "base0B": "#5AF78E", "base0C": "#9AEDFE",
                 "base0D": "#57C7FF", "base0E": "#FF6AC1", "base0F": "#B2643C"},
        roles={"text": "base05", "muted": "base04", "dim": "base03", "accent": "base0E", "border": "base03",
               "success": "base0B", "error": "base08", "warning": "base0A", "toolTitle": "base0D",
               "customMessageLabel": "base0E",
               "mdHeading": "base0D", "mdLink": "base08", "mdLinkUrl": "base09", "mdCode": "base0B",
               "mdQuote": "base0C", "mdListBullet": "base08",
               "syntaxComment": "base03", "syntaxKeyword": "base0E", "syntaxFunction": "base0D",
               "syntaxVariable": "base08", "syntaxString": "base0B", "syntaxNumber": "base09",
               "syntaxType": "base0A", "syntaxOperator": "base05", "syntaxPunctuation": "base05"},
        info="#3A3040"),
}


# ---------------------------------------------------------------- build
HEX = re.compile(r"#[0-9A-Fa-f]{6}$")


def build(name: str, spec: dict) -> dict:
    bad = set(spec["roles"]) - set(TOKENS)
    if bad:
        raise ValueError(f"{name}: unknown role tokens {sorted(bad)}")
    bad = set(spec["roles"]) & set(UI)
    if bad:
        raise ValueError(f"{name}: {sorted(bad)} belong to the shared UI layer, not to a theme")
    for k, v in spec["palette"].items():
        if not HEX.match(v):
            raise ValueError(f"{name}: palette {k}={v!r} is not #RRGGBB")
    roles = {**DEFAULTS, **spec["roles"]}
    vars_ = {**spec["palette"], **{f"ui_{k}": v for k, v in UI.items()}}
    colors = {}
    for tok in TOKENS:
        if tok in UI:
            colors[tok] = f"ui_{tok}"
            continue
        if tok not in roles:
            raise ValueError(f"{name}: missing role {tok} (no DEFAULTS fallback; set it in roles)")
        v, seen = roles[tok], []
        while v.startswith("@"):               # token -> token indirection (DEFAULTS)
            if v in seen or v[1:] not in roles:
                raise ValueError(f"{name}: {tok} -> {' -> '.join(seen + [v])} (cycle or unknown token)")
            seen.append(v)
            v = roles[v[1:]]
        if not (v in vars_ or HEX.match(v)):
            raise ValueError(f"{name}: {tok} = {v!r} is neither a palette name nor #RRGGBB")
        colors[tok] = v
    return {"$schema": SCHEMA, "name": name, "vars": vars_, "colors": colors,
            "export": {"pageBg": spec["bg"], "cardBg": UI["userMessageBg"], "infoBg": spec["info"]}}


def resolve(theme: dict, tok: str) -> str:
    v = theme["colors"][tok]
    return theme["vars"].get(v, v)


# ---------------------------------------------------------------- check
def _lin(c):
    """sRGB 8-bit channel -> linear light."""
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _rgb(h):
    return tuple(_lin(int(h[i:i + 2], 16)) for i in (1, 3, 5))


def _lum(h):
    r, g, b = _rgb(h)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    """WCAG 2 luminance contrast ratio (1 = same colour; 3 = UI floor; 4.5 = body text floor)."""
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def lab(h):
    """CIE L*a*b* (D65, sRGB). L* is perceptual lightness 0-100."""
    r, g, b = _rgb(h)
    x, y, z = r * .4124 + g * .3576 + b * .1805, r * .2126 + g * .7152 + b * .0722, r * .0193 + g * .1192 + b * .9505
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    return 116 * f(y) - 16, 500 * (f(x / .95047) - f(y)), 200 * (f(y) - f(z / 1.08883))


def dE(a, b):
    """CIE76 colour difference (~2 just noticeable, 10+ clearly distinct, 20+ obviously different)."""
    return sum((x - y) ** 2 for x, y in zip(lab(a), lab(b))) ** 0.5


# Foregrounds measured on the canvas. Structural lines (mdQuoteBorder, and the shared borderMuted /
# mdHr / mdCodeBlockBorder) are not held to FLOOR: like pi's own dark theme they only need to be
# visible, not readable, and several official quote borders sit at 2.2-3.0:1 by design.
CANVAS_TOKENS = ("text", "muted", "dim", "accent", "border", "borderAccent", "success", "error", "warning",
                 "thinkingText", "mdHeading", "mdLink", "mdLinkUrl", "mdCode", "mdCodeBlock", "mdQuote",
                 "mdListBullet", "bashMode", "syntaxComment", "syntaxKeyword", "syntaxFunction", "syntaxVariable",
                 "syntaxString", "syntaxNumber", "syntaxType", "syntaxOperator", "syntaxPunctuation")


def check(theme: dict) -> list:
    """Legibility report: (token, background, contrast) for every foreground on the background
    it actually renders on (canvas / user+custom panel / the three tool boxes / selection / search)."""
    g = lambda k: resolve(theme, k)
    bg = theme["export"]["pageBg"]
    boxes = [UI["toolPendingBg"], UI["toolSuccessBg"], UI["toolErrorBg"]]
    rows = [(tok, "canvas", contrast(g(tok), bg)) for tok in CANVAS_TOKENS]
    rows += [(tok, "panel", contrast(g(tok), UI["userMessageBg"]))
             for tok in ("userMessageText", "customMessageText", "customMessageLabel")]
    rows += [(tok, "boxes", min(contrast(g(tok), b) for b in boxes))
             for tok in ("toolTitle", "toolOutput", "toolDiffAdded", "toolDiffRemoved", "toolDiffContext")]
    rows += [(tok, "canvas", contrast(UI[tok], bg)) for tok in RAMP]   # shared ramp on this canvas
    rows.append(("text", "selected", contrast(g("text"), UI["selectedBg"])))
    rows.append(("searchMatchText", "search", contrast(g("searchMatchText"), UI["searchMatchBg"])))
    return rows


# Both sheets render through the "Desktop Chrome HiDPI" device profile (deviceScaleFactor 2):
# a 1x capture looks soft once GitHub scales it to the README column.
def preview(themes: dict):
    """Contact sheet -> preview/handwritten.png (playwright CLI + chromium, 2x)."""
    KEY = {"kw": "syntaxKeyword", "var": "syntaxVariable", "op": "syntaxOperator", "num": "syntaxNumber",
           "pun": "syntaxPunctuation", "com": "syntaxComment", "fn": "syntaxFunction", "type": "syntaxType",
           "str": "syntaxString", "txt": "text"}
    CODE = [[("kw", "const"), ("txt", " "), ("var", "answer"), ("op", " = "), ("num", "42"), ("pun", ";"),
             ("com", "  // note &amp; todo")],
            [("fn", "parse"), ("pun", "("), ("type", "Input"), ("pun", ") {"), ("txt", " "), ("kw", "return"),
             ("str", ' "ok"'), ("pun", "; }")]]
    cards = []
    for n, t in themes.items():
        g = lambda k: resolve(t, k)
        code = "".join("<div class=line>" + "".join(f"<span style='color:{g(KEY[k])}'>{s}</span>" for k, s in ln)
                       + "</div>" for ln in CODE)
        box = lambda b, l: f"<span class=box style='background:{g(b)};color:{g('toolTitle')}'>{l}</span>"
        cards.append(f"""<div class=card style="background:{t['export']['pageBg']}"><div class=hd>{n}</div>
<div class=code style="border:1px solid {g('mdCodeBlockBorder')}">{code}</div>
<div style="color:{g('text')}">text — normal output line</div><div style="color:{g('muted')}">muted — secondary text</div>
<div style="color:{g('dim')}">dim — statusline</div>
<div><span style="color:{g('mdHeading')}">## Heading</span> · <span style="color:{g('mdLink')}">link</span><span style="color:{g('mdLinkUrl')}"> (https://url)</span> ·
<span style="color:{g('mdCode')}">`code`</span> · <span style="color:{g('mdQuoteBorder')}">▎</span><span style="color:{g('mdQuote')}">quote</span> ·
<span style="color:{g('mdListBullet')}">•</span> <span style="color:{g('text')}">item</span> ·
<span style="background:{g('selectedBg')};color:{g('text')}">&nbsp;selected&nbsp;</span> ·
<span style="background:{g('searchMatchBg')};color:{g('searchMatchText')}">&nbsp;search&nbsp;</span></div>
<div class=tool style="background:{g('toolSuccessBg')}"><span style="color:{g('toolTitle')};font-weight:700">$ git diff</span>
<span style="color:{g('toolOutput')}">  output line</span>
<span style="color:{g('toolDiffContext')}">  ctx</span> <span style="color:{g('toolDiffAdded')}">+ added</span> <span style="color:{g('toolDiffRemoved')}">- removed</span></div>
<div class=line><span style="color:{g('success')}">✔ ok</span> <span style="color:{g('error')}">✘ fail</span>
<span style="color:{g('warning')}">▲ warn</span> <span style="color:{g('toolDiffAdded')}">+ added</span>
<span style="color:{g('toolDiffRemoved')}">- removed</span></div>
<div><span style="background:{g('userMessageBg')};color:{g('userMessageText')}">&nbsp;▸ user message&nbsp;</span>
<span style="background:{g('customMessageBg')};color:{g('customMessageLabel')}">&nbsp;[info] custom&nbsp;</span></div>
<div>{box('toolPendingBg', 'pending')} {box('toolSuccessBg', 'done')} {box('toolErrorBg', 'error')}</div>
<div style="border:1px solid {g('thinkingHigh')};border-radius:4px;padding:2px 8px;margin-top:4px">
<span style="color:{g('toolOutput')}">▸ input · thinking:high</span></div></div>""")
    html = ("<!doctype html><meta charset=utf-8><style>body{background:#16161c;font:13px/1.45 ui-monospace,Menlo,"
            "monospace;margin:14px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;max-width:1360px}"
            ".card{border-radius:8px;padding:10px 12px}.hd{color:#eee;font-weight:700;font-size:14px}"
            ".code{font-size:12.5px;border-radius:5px;padding:4px 8px;margin:5px 0}.line{white-space:pre}"
            ".box{border-radius:4px;padding:1px 7px;margin-right:6px;font-size:12px}"
            ".tool{border-radius:4px;padding:2px 8px;margin:4px 0;white-space:pre;font-size:12.5px}</style>"
            f"<div class=grid>{''.join(cards)}</div>")
    page = ROOT / "handwritten.html"
    page.write_text(html, encoding="utf-8")
    (ROOT / "preview").mkdir(exist_ok=True)
    subprocess.run(["playwright", "screenshot", "--device", "Desktop Chrome HiDPI", "--viewport-size=1380,600", "--full-page",
                    page.resolve().as_uri(), str(ROOT / "preview" / "handwritten.png")], check=True)
    page.unlink()
    print("preview/handwritten.png")


def preview_ui():
    """Shared UI layer on every measured terminal background -> preview/ui-layer.png
    (two-column contact sheet, one card per terminal)."""
    fg, dim = "#D4D4D4", "#9A9A9A"
    chip = lambda k, t: f"<span class=chip style='background:{UI[k]};color:{fg}'>{t}</span>"
    cards = []
    for label, bg in TERMINALS:
        levels = "".join(f"<span class=inp style='border-color:{UI[k]};color:{dim}'>{k.removeprefix('thinking').lower()}</span>"
                         for k in ("thinkingOff", "thinkingMinimal", *RAMP))
        cards.append(f"""<div class=card style="background:{bg}">
<div class=lbl style="color:{fg}">{label} <span style="color:{dim}">{bg} · L* {lstar(bg):.0f}</span></div>
<div class=line>{chip('userMessageBg', '▸ user message')}{chip('toolPendingBg', 'pending')}{chip('toolSuccessBg', 'done')}{chip('toolErrorBg', 'error')}</div>
<div class=line>{chip('selectedBg', 'selected')}{chip('searchMatchBg', 'search')}<span class=code style="border:1px solid {UI['mdCodeBlockBorder']};color:{dim}">code block</span><span class=hr style="background:{UI['mdHr']}"></span><span class=bar style="background:{UI['scrollbarTrack']}"><span style="background:{UI['scrollbarThumb']}"></span></span></div>
<div class=line>{levels}</div></div>""")
    html = ("<!doctype html><meta charset=utf-8><style>body{background:#16161c;margin:14px;font:13px/1.5 ui-monospace,"
            "Menlo,monospace}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;max-width:1360px}"
            ".card{border-radius:8px;padding:10px 14px}.lbl{font-weight:700;margin-bottom:6px}"
            ".line{margin-top:6px;white-space:nowrap}.chip,.code,.inp{display:inline-block;border-radius:4px;"
            "padding:1px 10px;margin-right:8px}.inp{border:1px solid}.hr{display:inline-block;width:70px;height:1px;"
            "vertical-align:middle;margin-right:10px}.bar{display:inline-block;width:8px;height:14px;"
            "vertical-align:middle;border-radius:2px}.bar span{display:block;width:8px;height:7px;border-radius:2px}"
            "</style><div class=grid>" + "".join(cards) + "</div>")
    page = ROOT / "ui-layer.html"
    page.write_text(html, encoding="utf-8")
    subprocess.run(["playwright", "screenshot", "--device", "Desktop Chrome HiDPI", "--viewport-size=1380,400",
                    "--full-page", page.resolve().as_uri(), str(ROOT / "preview" / "ui-layer.png")], check=True)
    page.unlink()
    print("preview/ui-layer.png")


def lstar(h: str) -> float:
    return lab(h)[0]


FLOOR = {"text": 4.5, "userMessageText": 4.5, "customMessageText": 4.5, "toolTitle": 4.5}   # everything else 3.0

# Known official-colour residuals, verified and accepted (see docs/design.md "已知代价"). Keyed by
# (theme, token, background). Anything below FLOOR and NOT listed here fails --check.
KNOWN: dict[tuple, str] = {
    ("flow-one-dark-pro", "syntaxComment", "canvas"): "onedark.vim comment is dark by design",
    ("flow-one-dark-pro", "text", "selected"): "bright fg on the shared selection gray",
    ("flow-nord", "dim", "canvas"): "official nord3 brightened",
    ("flow-nord", "mdLinkUrl", "canvas"): "nord3 brightened",
    ("flow-nord", "syntaxComment", "canvas"): "nord3 brightened",
    ("flow-nord", "toolDiffRemoved", "boxes"): "nord11 on the state boxes",
    ("flow-dracula", "toolTitle", "boxes"): "official pink, 4.16:1; bold command text stays clear",
    ("flow-gruvbox", "toolDiffRemoved", "boxes"): "official red on the state boxes",
    ("flow-tokyo-night", "mdLinkUrl", "canvas"): "official comment blue-grey",
    ("flow-tokyo-night", "syntaxComment", "canvas"): "official comment",
    ("flow-solarized-dark", "dim", "canvas"): "base01 by design",
    ("flow-solarized-dark", "mdLinkUrl", "canvas"): "base01",
    ("flow-solarized-dark", "syntaxComment", "canvas"): "base01",
    ("flow-solarized-dark", "customMessageLabel", "panel"): "violet label, author colour",
    ("flow-solarized-dark", "toolDiffRemoved", "boxes"): "official red on the state boxes",
    ("flow-solarized-dark", "userMessageText", "panel"): "base1 on the shared user panel",
    ("flow-solarized-dark", "customMessageText", "panel"): "base1 on the shared user panel",
    ("flow-solarized-dark", "text", "selected"): "base1 on the shared selection gray",
    ("flow-monokai", "toolDiffRemoved", "boxes"): "original Monokai pink on the state boxes",
    ("flow-kanagawa", "customMessageLabel", "panel"): "oniViolet label",
    ("flow-kanagawa", "toolDiffAdded", "boxes"): "autumnGreen on the state boxes",
    # --- expansion set
    ("flow-oceanic-next", "dim", "canvas"): "official comment #65737E, dark by design",
    ("flow-oceanic-next", "mdLinkUrl", "canvas"): "official comment colour",
    ("flow-oceanic-next", "syntaxComment", "canvas"): "official comment #65737E",
    ("flow-noctis-bordo", "toolDiffRemoved", "boxes"): "official TAG #E66533 on the state boxes, 2.97:1",
    ("flow-noctis-sereno", "toolDiffRemoved", "boxes"): "official TAG #E66533 on the state boxes, 2.97:1",
    ("flow-andromeda", "toolDiffRemoved", "boxes"): "official red #EE5D43 on the state boxes",
    ("flow-material", "dim", "canvas"): "base03 comments, dark by design",
    ("flow-material", "syntaxComment", "canvas"): "base03 comments",
    ("flow-miramare", "dim", "canvas"): "light_grey comment colour, author look",
    ("flow-miramare", "syntaxComment", "canvas"): "light_grey comment colour",
}


def canvas_ceiling(name: str, theme: dict) -> tuple[float, str]:
    """Brightest TERMINALS background on which every canvas foreground (KNOWN residuals excepted)
    still meets FLOOR. pi paints on the terminal's own background, so this is the theme's declared
    support range; contrast of a light foreground only falls as the background brightens."""
    g = lambda k: resolve(theme, k)
    toks = [t for t in CANVAS_TOKENS if (name, t, "canvas") not in KNOWN]
    best = (lstar(theme["export"]["pageBg"]), "own canvas")     # check() already enforces FLOOR here
    for label, bg in TERMINALS:
        if all(contrast(g(t), bg) >= FLOOR.get(t, 3.0) for t in toks):
            best = max(best, (lstar(bg), label))
    return best


def near_duplicates(built: dict) -> list:
    """(identical foreground tokens, mean dE over foreground tokens, a, b) for every theme pair,
    most similar first. Same-family flavours legitimately score high; a true duplicate would be
    ~all tokens identical or a mean dE under DUP_DE."""
    fg = [t for t in TOKENS if t not in UI]
    vec = {n: [resolve(t, k) for k in fg] for n, t in built.items()}
    names = list(vec)
    out = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            same = sum(x == y for x, y in zip(vec[a], vec[b]))
            de = sum(dE(x, y) for x, y in zip(vec[a], vec[b])) / len(fg)
            out.append((same, de, a, b))
    return sorted(out, key=lambda r: (-r[0], r[1]))


DUP_SAME, DUP_DE = 30, 2.5   # of 37 foreground tokens / mean CIE76 dE: beyond this two themes are one theme


def check_sources(built: dict) -> list:
    """Every theme needs a manifest entry with at least one upstream locked to a full commit hash
    and a stated license. Returns problems (empty = ok)."""
    if not SOURCES.exists():
        return [f"missing {SOURCES.relative_to(ROOT)}"]
    entries = {e["name"]: e for e in json.loads(SOURCES.read_text(encoding="utf-8"))["themes"]}
    problems = [f"{n}: no entry in {SOURCES.name}" for n in built if n not in entries]
    problems += [f"{n}: in {SOURCES.name} but not in THEMES" for n in entries if n not in built]
    for n, e in entries.items():
        for src in e.get("sources", []):
            if not re.fullmatch(r"[0-9a-f]{40}", src.get("ref", "")):
                problems.append(f"{n}: {src.get('upstream')} ref is not a full commit hash")
            if not src.get("license"):
                problems.append(f"{n}: {src.get('upstream')} has no license field")
        if not e.get("sources"):
            problems.append(f"{n}: no sources")
    return problems


def check_report(name: str, theme: dict) -> tuple[list, list]:
    """Split check() rows into (known violations, unexpected violations) against FLOOR."""
    known, unexpected = [], []
    for tok, on, c in check(theme):
        if c < FLOOR.get(tok, 3.0):
            (known if (name, tok, on) in KNOWN else unexpected).append((tok, on, c))
    return known, unexpected


def measure(built: dict, hexes: list):
    """Print the metrics cited in README and docs/design.md, or pairwise metrics for the given hex colours."""
    if hexes:
        for h in hexes:
            if not HEX.match(h):
                raise SystemExit(f"{h!r} is not #RRGGBB")
            L, a, b = lab(h)
            print(f"{h}  L* {L:5.1f}  a* {a:+6.1f}  b* {b:+6.1f}")
        for i, x in enumerate(hexes):
            for y in hexes[i + 1:]:
                print(f"{x} vs {y}  contrast {contrast(x, y):4.2f}:1  dE {dE(x, y):5.1f}  dL* {abs(lstar(x) - lstar(y)):5.1f}")
        return
    print("== shared UI layer (hex, L*)")
    for tok, h in UI.items():
        print(f"  {tok:18} {h}  L* {lstar(h):5.1f}")
    boxes = [("user", UI["userMessageBg"]), ("pending", UI["toolPendingBg"]),
             ("done", UI["toolSuccessBg"]), ("error", UI["toolErrorBg"])]
    print("== state boxes, pairwise dE")
    for i, (na, ha) in enumerate(boxes):
        for nb, hb in boxes[i + 1:]:
            print(f"  {na:8}~ {nb:8} {dE(ha, hb):5.1f}")
    print("== panel vs terminal backgrounds (dL* = panel L* - background L*)")
    for label, bg in TERMINALS:
        print(f"  {bg}  L* {lstar(bg):4.1f}  dL* {lstar(UI['userMessageBg']) - lstar(bg):5.1f}  {label}")
    print("== canvas ceiling (brightest terminal background on which all canvas foregrounds hold)")
    for name, theme in built.items():
        L, label = canvas_ceiling(name, theme)
        print(f"  {name:24} own L* {lstar(theme['export']['pageBg']):4.1f}  ceiling L* {L:4.1f}  {label}")
    print("== nearest theme pairs (identical fg tokens / 37, mean dE)")
    for same, de, a, b in near_duplicates(built)[:6]:
        print(f"  {same:2}/37  dE {de:5.1f}  {a} ~ {b}")
    print("== per-theme contrast (foreground vs the background it renders on; * = below floor)")
    for name, theme in built.items():
        print(f"  {name}  canvas {theme['export']['pageBg']} L* {lstar(theme['export']['pageBg']):.1f}")
        for tok, on, c in check(theme):
            flag = " *" if c < FLOOR.get(tok, 3.0) else ""
            print(f"    {tok:20} {on:8} {c:5.2f}:1{flag}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="print foregrounds below 3:1 on their real background")
    ap.add_argument("--preview", action="store_true", help="render preview/handwritten.png (playwright CLI)")
    ap.add_argument("--measure", nargs="*", metavar="HEX",
                    help="print the metrics cited in README / docs/design.md (no args) or pairwise metrics for given hex colours")
    args = ap.parse_args()
    if args.measure:                       # pairwise mode: no build, no writes
        if args.check or args.preview:
            ap.error("--measure HEX... is a standalone calculator; run --check / --preview separately")
        measure({}, args.measure)
        return
    OUT.mkdir(exist_ok=True)
    built = {name: build(name, spec) for name, spec in THEMES.items()}
    failures: list = []
    for stale in OUT.glob("flow-*.json"):
        if stale.stem not in built:
            stale.unlink()
            print(f"removed stale {stale.name}")
    for name, theme in built.items():
        (OUT / f"{name}.json").write_text(json.dumps(theme, indent="\t") + "\n", encoding="utf-8")
        if args.check:
            known, unexpected = check_report(name, theme)
            parts = [f"{t}/{on} {c:.1f} (known)" for t, on, c in known]
            parts += [f"{t}/{on} {c:.1f} < {FLOOR.get(t, 3.0)} !!" for t, on, c in unexpected]
            print(f"{name:24} " + ("ok" if not parts else "; ".join(parts)))
            failures.append((name, unexpected))
    print(f"wrote {len(built)} themes -> {OUT}")
    if args.check:
        problems = [f"contrast: {n} {t}/{on} {c:.2f}" for n, u in failures for t, on, c in u]
        for name, theme in built.items():
            L, label = canvas_ceiling(name, theme)
            print(f"{name:24} canvas ok up to L* {L:4.1f} ({label})")
        dups = near_duplicates(built)
        print("nearest pairs: " + "; ".join(f"{a}~{b} {s}/37 dE {d:.1f}" for s, d, a, b in dups[:3]))
        problems += [f"duplicate: {a} ~ {b} ({s}/37 identical, mean dE {d:.1f})"
                     for s, d, a, b in dups if s >= DUP_SAME or d < DUP_DE]
        problems += [f"sources: {p}" for p in check_sources(built)]
        if problems:
            raise SystemExit("--check failed:\n  " + "\n  ".join(problems)
                             + "\n(extend KNOWN / sources only with a verified reason)")
        print("--check ok")
    if args.measure is not None:           # full report (--measure with no hexes)
        measure(built, [])
    if args.preview:
        preview(built)
        preview_ui()


if __name__ == "__main__":
    main()
