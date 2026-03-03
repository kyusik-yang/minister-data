"""
Generate pipeline.png -- research infrastructure diagram
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe
import numpy as np

plt.rcParams["font.family"] = "Nanum Gothic"
plt.rcParams["axes.unicode_minus"] = False

fig, ax = plt.subplots(figsize=(14, 7), facecolor="white")
ax.set_xlim(0, 14)
ax.set_ylim(0.3, 7.4)
ax.axis("off")

# ── Color palette ─────────────────────────────────────────────────────────────
C_SOURCE  = "#f0f4f8"   # light gray-blue  -- external data sources
C_SOURCE_B= "#c9d8e8"   # border
C_DATA    = "#dbeafe"   # light blue       -- this repo's data
C_DATA_B  = "#3b82f6"   # border
C_META    = "#ede9fe"   # light purple     -- metadata
C_META_B  = "#7c3aed"
C_OUT     = "#d1fae5"   # light green      -- output / analysis
C_OUT_B   = "#059669"
C_ARROW   = "#475569"   # slate
C_LABEL   = "#1e293b"   # near-black text
C_SUBLABEL= "#64748b"   # gray subtext

def box(ax, x, y, w, h, fc, ec, lw=1.5, radius=0.18):
    rect = FancyBboxPatch((x, y), w, h,
                          boxstyle=f"round,pad=0,rounding_size={radius}",
                          facecolor=fc, edgecolor=ec, linewidth=lw, zorder=3)
    ax.add_patch(rect)

def arrow(ax, x0, y0, x1, y1, color=C_ARROW, label=None, lw=1.8, style="->"):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle=style, color=color,
                                lw=lw, connectionstyle="arc3,rad=0.0"))
    if label:
        mx, my = (x0+x1)/2, (y0+y1)/2
        ax.text(mx, my + 0.18, label, ha="center", va="bottom",
                fontsize=7, color=color, style="italic")

def arrow_curved(ax, x0, y0, x1, y1, rad, color=C_ARROW, label=None, lw=1.6):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="->", color=color,
                                lw=lw, connectionstyle=f"arc3,rad={rad}"))
    if label:
        mx = (x0+x1)/2 + 0.1
        my = (y0+y1)/2 + 0.05
        ax.text(mx, my, label, ha="left", va="center",
                fontsize=7, color=color, style="italic")

def label(ax, x, y, title, lines, title_size=9.5, line_size=8, color=C_LABEL):
    ax.text(x, y, title, ha="center", va="center",
            fontsize=title_size, fontweight="bold", color=color, zorder=4)
    for i, line in enumerate(lines):
        ax.text(x, y - 0.38*(i+1), line, ha="center", va="center",
                fontsize=line_size, color=C_SUBLABEL, zorder=4)

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN 1: External sources  (x = 0.3)
# ─────────────────────────────────────────────────────────────────────────────

# Source A: LOSI
box(ax, 0.3, 4.1, 3.0, 2.1, C_SOURCE, C_SOURCE_B)
label(ax, 1.80, 5.55, "LOSI",
      ["국회의사록정보시스템",
       "17th-21st Assembly",
       "2004 - 2024"],
      title_size=10)

# Source B: Official records
box(ax, 0.3, 1.2, 3.0, 2.1, C_SOURCE, C_SOURCE_B)
label(ax, 1.80, 2.65, "Official Records",
      ["관보 (Official Gazette)",
       "National Assembly Open API",
       "Wikipedia / Namu Wiki"],
      title_size=10)

# Source label
ax.text(1.80, 0.65, "External Sources", ha="center", va="center",
        fontsize=8.5, color=C_SUBLABEL, style="italic")

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN 2: This repo's datasets  (x = 4.2)
# ─────────────────────────────────────────────────────────────────────────────

# Q-A Dyads (large dataset, not in repo)
box(ax, 4.2, 4.1, 3.2, 2.1, C_SOURCE, "#94a3b8", lw=1.5)
label(ax, 5.80, 5.55, "Q-A Dyads",
      ["274,763 exchanges",
       "HEARING  +  AUDIT",
       "q_speaker · q_text · q_word_count"],
      title_size=10)
ax.text(5.80, 4.22, "* not in this repo (LOSI download required)",
        ha="center", va="center", fontsize=6.8, color="#94a3b8", style="italic", zorder=4)

# Minister panel
box(ax, 4.2, 1.2, 3.2, 2.1, C_DATA, C_DATA_B, lw=2.0)
label(ax, 5.80, 2.60, "minister_panel_comprehensive.csv",
      ["286 appointments  ·  2000-2025",
       "dual_office  (hand-coded)",
       "mp_district · mp_party · confirmation_date"],
      title_size=9.5)

# "THIS REPO" badge
badge = FancyBboxPatch((4.25, 1.25), 1.05, 0.32,
                       boxstyle="round,pad=0,rounding_size=0.08",
                       facecolor=C_DATA_B, edgecolor="none", zorder=5)
ax.add_patch(badge)
ax.text(4.775, 1.41, "THIS REPO", ha="center", va="center",
        fontsize=6.5, fontweight="bold", color="white", zorder=6)

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN 2.5: losi_mp_metadata  (x = 4.2, middle height)
# ─────────────────────────────────────────────────────────────────────────────
box(ax, 4.2, -0.1, 3.2, 1.0, C_META, C_META_B, lw=2.0)
label(ax, 5.80, 0.42, "losi_mp_metadata.csv",
      ["1,931 legislators  ·  q_party · q_ruling"],
      title_size=9.0, line_size=8)

badge2 = FancyBboxPatch((4.25, -0.05), 1.05, 0.32,
                        boxstyle="round,pad=0,rounding_size=0.08",
                        facecolor=C_META_B, edgecolor="none", zorder=5)
ax.add_patch(badge2)
ax.text(4.775, 0.11, "THIS REPO", ha="center", va="center",
        fontsize=6.5, fontweight="bold", color="white", zorder=6)

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN 3: Merge / join  (x = 8.3)
# ─────────────────────────────────────────────────────────────────────────────
box(ax, 8.3, 2.0, 3.0, 3.2, C_DATA, C_DATA_B, lw=2.0)
label(ax, 9.80, 4.45, "Merged Analysis Dataset",
      ["Dyad × dual_office × q_ruling",
       "",
       "dyads.merge(panel, on=['minister','admin','ministry'])",
       ".merge(meta,  on=['q_speaker','assembly'])"],
      title_size=9.5, line_size=7.8)

# join key annotations inside the box
ax.text(9.80, 3.05, "join key: minister + admin + ministry",
        ha="center", va="center", fontsize=7.5, color=C_DATA_B,
        style="italic", zorder=4)
ax.text(9.80, 2.72, "join key: q_speaker + assembly",
        ha="center", va="center", fontsize=7.5, color=C_META_B,
        style="italic", zorder=4)

badge3 = FancyBboxPatch((8.35, 2.05), 1.05, 0.32,
                        boxstyle="round,pad=0,rounding_size=0.08",
                        facecolor=C_DATA_B, edgecolor="none", zorder=5)
ax.add_patch(badge3)
ax.text(8.875, 2.21, "THIS REPO", ha="center", va="center",
        fontsize=6.5, fontweight="bold", color="white", zorder=6)

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN 4: Analysis output  (x = 12.1)
# ─────────────────────────────────────────────────────────────────────────────
box(ax, 12.1, 2.8, 1.7, 2.4, C_OUT, C_OUT_B, lw=2.0)
label(ax, 12.95, 4.62, "Oversight",
      ["Analysis", "", "Do ruling-party",
       "legislators ask",
       "softer questions?"],
      title_size=9.5, line_size=8)

# ─────────────────────────────────────────────────────────────────────────────
# ARROWS
# ─────────────────────────────────────────────────────────────────────────────

# LOSI → Q-A Dyads
arrow(ax, 3.30, 5.15, 4.20, 5.15, label="transcripts", lw=1.8)

# Official records → minister_panel
arrow(ax, 3.30, 2.25, 4.20, 2.25, label="appointment records", lw=1.8)

# Q-A Dyads → Merged (top)
arrow(ax, 7.40, 5.15, 8.30, 4.60, lw=1.8)

# minister_panel → Merged (middle)
arrow(ax, 7.40, 2.25, 8.30, 3.20, label="dual_office join", lw=2.0, color=C_DATA_B)

# losi_mp_metadata → Merged (bottom)
arrow_curved(ax, 7.40, 0.42, 8.30, 2.55, rad=-0.25,
             label="ruling/opp. coding", color=C_META_B, lw=1.8)

# Merged → Analysis
arrow(ax, 11.30, 3.60, 12.10, 3.90, lw=2.0, color=C_OUT_B)

# ─────────────────────────────────────────────────────────────────────────────
# Column headers
# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# Title (top)
# ─────────────────────────────────────────────────────────────────────────────
ax.text(7.0, 7.08,
        "Korean Dual-Office Minister Dataset  --  Research Infrastructure",
        ha="center", va="center", fontsize=12, fontweight="bold", color=C_LABEL)
ax.text(7.0, 6.85,
        "Yang (2025)   github.com/kyusik-yang/minister-data",
        ha="center", va="center", fontsize=8.5, color=C_SUBLABEL)

# Divider lines
for x in [3.85, 7.9, 11.8]:
    ax.axvline(x, ymin=0.04, ymax=0.92, color="#cbd5e1", lw=0.8, linestyle="--", zorder=1)

# Column headers (below title)
for x, txt in [(1.80, "[ 1 ]  Raw Sources"),
               (5.80, "[ 2 ]  Structured Data"),
               (9.80, "[ 3 ]  Analysis-Ready"),
               (12.95, "[ 4 ]  Research")]:
    ax.text(x, 6.58, txt, ha="center", va="center",
            fontsize=9, color="#334155", fontweight="bold")

# ─────────────────────────────────────────────────────────────────────────────
OUT = __file__.replace("make_pipeline.py", "pipeline.png")
fig.savefig(OUT, dpi=180, bbox_inches="tight", facecolor="white")
print(f"Saved: {OUT}")
