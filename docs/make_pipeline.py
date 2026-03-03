"""
Generate pipeline.png -- research infrastructure diagram (v2)
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np

plt.rcParams["font.family"] = "Nanum Gothic"
plt.rcParams["axes.unicode_minus"] = False

# ── Canvas ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(16, 7.5), facecolor="white")
ax.set_xlim(0, 16)
ax.set_ylim(0, 7.5)
ax.axis("off")

# ── Palette ───────────────────────────────────────────────────────────────────
C_BG      = "white"
C_SOURCE  = "#f1f5f9"   # light gray -- external sources
C_SRC_E   = "#94a3b8"
C_DYAD    = "#f8fafc"   # very light -- Q-A dyads (not in repo)
C_DYAD_E  = "#94a3b8"
C_PANEL   = "#dbeafe"   # blue -- minister panel
C_PANEL_E = "#2563eb"
C_META    = "#ede9fe"   # purple -- mp metadata
C_META_E  = "#7c3aed"
C_MERGE   = "#e0f2fe"   # sky blue -- merged
C_MERGE_E = "#0284c7"
C_OUT     = "#dcfce7"   # green -- output
C_OUT_E   = "#16a34a"
C_ARROW   = "#475569"
C_TEXT    = "#1e293b"
C_GRAY    = "#64748b"

def rounded_box(x, y, w, h, fc, ec, lw=1.8, r=0.22):
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle=f"round,pad=0,rounding_size={r}",
                       facecolor=fc, edgecolor=ec, linewidth=lw, zorder=3,
                       clip_on=False)
    ax.add_patch(p)

def badge(x, y, text, fc, w=1.4, h=0.3):
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle="round,pad=0,rounding_size=0.1",
                       facecolor=fc, edgecolor="none", zorder=5, clip_on=False)
    ax.add_patch(p)
    ax.text(x + w/2, y + h/2, text, ha="center", va="center",
            fontsize=7, fontweight="bold", color="white", zorder=6)

def arrow(x0, y0, x1, y1, color=C_ARROW, lw=1.8, rad=0.0, label=None, labelside=0.5):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw,
                                mutation_scale=14,
                                connectionstyle=f"arc3,rad={rad}"))
    if label:
        mx = x0 + (x1-x0)*labelside
        my = y0 + (y1-y0)*labelside
        offset = 0.22 if rad >= 0 else -0.22
        ax.text(mx, my + offset, label, ha="center", va="center",
                fontsize=7.5, color=color, style="italic",
                bbox=dict(fc="white", ec="none", pad=1.5))

def title_block(cx, cy, title, lines, ts=10.5, ls=8.5):
    ax.text(cx, cy, title, ha="center", va="center",
            fontsize=ts, fontweight="bold", color=C_TEXT, zorder=4)
    for i, line in enumerate(lines):
        ax.text(cx, cy - 0.42*(i+1), line, ha="center", va="center",
                fontsize=ls, color=C_GRAY, zorder=4)

# ── COLUMN 1: External sources  x=0.25 .. 3.45 ───────────────────────────────
BW = 3.2   # box width
BH = 1.8   # box height

# LOSI
rounded_box(0.25, 4.55, BW, BH, C_SOURCE, C_SRC_E)
title_block(1.85, 5.68, "LOSI",
            ["국회의사록정보시스템",
             "17th – 21st Assembly  (2004-2024)",
             "Full-text committee transcripts"])

# Official records
rounded_box(0.25, 2.35, BW, BH, C_SOURCE, C_SRC_E)
title_block(1.85, 3.48, "Official Records",
            ["관보  (Official Gazette)",
             "National Assembly Open API",
             "Wikipedia / Namu Wiki"])

# col label
ax.text(1.85, 1.90, "External  Sources", ha="center", va="center",
        fontsize=8.5, color=C_GRAY, style="italic")

# ── COLUMN 2: Datasets  x=4.30 .. 8.50 ──────────────────────────────────────
DW = 4.1

# Q-A Dyads (not in repo)
rounded_box(4.30, 4.80, DW, 1.55, C_DYAD, C_DYAD_E, lw=1.4)
title_block(6.35, 5.78, "Q-A Dyads",
            ["274,763 exchanges  |  HEARING + AUDIT",
             "q_speaker  ·  q_text  ·  q_word_count  ·  r_text"])
ax.text(6.35, 4.95, "* not included — requires LOSI download",
        ha="center", va="center", fontsize=7, color=C_DYAD_E, style="italic", zorder=4)

# Minister panel (in repo)
rounded_box(4.30, 2.55, DW, 1.95, C_PANEL, C_PANEL_E, lw=2.2)
title_block(6.35, 3.75, "minister_panel_comprehensive.csv",
            ["286 appointments  ·  2000 – 2025",
             "dual_office  (hand-coded, key variable)",
             "mp_district  ·  mp_party  ·  confirmation_date"],
            ts=10, ls=8.5)
badge(4.35, 2.60, "THIS REPO", C_PANEL_E)

# MP metadata (in repo)
rounded_box(4.30, 1.00, DW, 1.25, C_META, C_META_E, lw=2.2)
title_block(6.35, 1.70, "losi_mp_metadata.csv",
            ["1,931 legislators  ·  17th–21st Assembly",
             "q_party  ·  q_elect_type  ·  q_term_count"],
            ts=10, ls=8.5)
badge(4.35, 1.05, "THIS REPO", C_META_E)

# col label
ax.text(6.35, 0.55, "Structured  Data", ha="center", va="center",
        fontsize=8.5, color=C_GRAY, style="italic")

# ── COLUMN 3: Merged dataset  x=9.35 .. 13.05 ───────────────────────────────
MW = 3.6

rounded_box(9.35, 2.30, MW, 4.05, C_MERGE, C_MERGE_E, lw=2.2)

ax.text(11.15, 5.90, "Merged Analysis Dataset",
        ha="center", va="center", fontsize=11, fontweight="bold", color=C_TEXT, zorder=4)

# Join descriptions
items = [
    (C_PANEL_E, "dual_office join",    "key: minister + admin + ministry"),
    (C_META_E,  "ruling/opp. coding",  "key: q_speaker + assembly"),
]
for j, (col, head, sub) in enumerate(items):
    yy = 5.30 - j*1.05
    ax.plot([9.65, 12.65], [yy+0.02, yy+0.02], color=col, lw=1.2,
            linestyle="--", alpha=0.6, zorder=4)
    ax.text(11.15, yy - 0.12, head, ha="center", va="center",
            fontsize=9, fontweight="bold", color=col, zorder=4)
    ax.text(11.15, yy - 0.45, sub, ha="center", va="center",
            fontsize=8, color=C_GRAY, style="italic", zorder=4)

# Result row
ax.text(11.15, 3.15, "Each row:", ha="center", va="center",
        fontsize=8.5, color=C_GRAY, zorder=4)
ax.text(11.15, 2.75,
        "Q-A exchange  x  dual_office  x  q_ruling  x  hearing_type",
        ha="center", va="center", fontsize=8, color=C_TEXT,
        fontweight="bold", zorder=4,
        bbox=dict(fc="#f0f9ff", ec=C_MERGE_E, lw=0.8, pad=4, boxstyle="round,pad=0.3"))

badge(9.40, 2.35, "THIS REPO", C_MERGE_E)

# col label
ax.text(11.15, 1.85, "Analysis-Ready  Dataset", ha="center", va="center",
        fontsize=8.5, color=C_GRAY, style="italic")

# ── COLUMN 4: Research output  x=13.8 .. 15.8 ───────────────────────────────
rounded_box(13.80, 3.00, 1.90, 3.35, C_OUT, C_OUT_E, lw=2.0)
ax.text(14.75, 5.80, "Research\nOutput", ha="center", va="center",
        fontsize=10, fontweight="bold", color=C_TEXT, zorder=4, linespacing=1.5)

questions = [
    "Do ruling-party",
    "legislators ask",
    "softer questions",
    "to dual-office",
    "ministers?",
]
for i, q in enumerate(questions):
    ax.text(14.75, 5.05 - i*0.38, q, ha="center", va="center",
            fontsize=8.2, color=C_GRAY, zorder=4)

# col label
ax.text(14.75, 2.60, "Oversight  Analysis", ha="center", va="center",
        fontsize=8.5, color=C_GRAY, style="italic")

# ── ARROWS ────────────────────────────────────────────────────────────────────

# LOSI -> Q-A Dyads
arrow(3.45, 5.45, 4.30, 5.45, label="transcripts")

# Official Records -> minister_panel
arrow(3.45, 3.25, 4.30, 3.50, label="appointment records")

# Q-A Dyads -> Merged (top)
arrow(8.40, 5.58, 9.35, 5.55)

# minister_panel -> Merged
arrow(8.40, 3.52, 9.35, 4.68, color=C_PANEL_E, lw=2.0,
      label="dual_office", labelside=0.55)

# losi_mp_metadata -> Merged
arrow(8.40, 1.62, 9.35, 3.60, color=C_META_E, lw=2.0, rad=-0.18,
      label="q_ruling coding", labelside=0.5)

# Merged -> Analysis
arrow(12.95, 4.32, 13.80, 4.32, color=C_OUT_E, lw=2.2)

# ── COLUMN DIVIDERS ───────────────────────────────────────────────────────────
for x in [4.0, 9.1, 13.55]:
    ax.plot([x, x], [0.75, 6.75], color="#e2e8f0", lw=1.0,
            linestyle="--", zorder=1)

# ── TITLE ─────────────────────────────────────────────────────────────────────
ax.text(8.0, 7.20,
        "Korean Dual-Office Minister Dataset  --  Research Infrastructure",
        ha="center", va="center", fontsize=13, fontweight="bold", color=C_TEXT)
ax.text(8.0, 6.92,
        "Yang (2025)   |   github.com/kyusik-yang/minister-data",
        ha="center", va="center", fontsize=9, color=C_GRAY)

# thin rule under title
ax.plot([0.3, 15.7], [6.78, 6.78], color="#e2e8f0", lw=1.0, zorder=1)

# ── SAVE ──────────────────────────────────────────────────────────────────────
OUT = __file__.replace("make_pipeline.py", "pipeline.png")
fig.savefig(OUT, dpi=180, bbox_inches="tight", facecolor="white")
print(f"Saved: {OUT}")
