"""
Generate overview.png -- 4-panel publication-quality figure
for minister_panel_comprehensive.csv
"""

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
import numpy as np
from pathlib import Path

# Set Korean font
plt.rcParams["font.family"] = "Nanum Gothic"
plt.rcParams["axes.unicode_minus"] = False

# ── Load ──────────────────────────────────────────────────────────────────────
DATA = Path(__file__).parent.parent / "data" / "minister_panel_comprehensive.csv"
df = pd.read_csv(DATA)
df["start_dt"] = pd.to_datetime(df["start"], errors="coerce")
df["end_dt"]   = pd.to_datetime(df["end"],   errors="coerce")
df["dual_office"] = df["dual_office"].astype(bool)

# Administration order + ideology colors
ADMIN_ORDER = ["노무현", "이명박", "박근혜", "문재인", "윤석열", "이재명"]
IDEOLOGY    = {"노무현": "Progressive", "이명박": "Conservative",
               "박근혜": "Conservative", "문재인": "Progressive",
               "윤석열": "Conservative", "이재명": "Progressive"}
ADM_COLORS  = {a: ("#2166ac" if IDEOLOGY[a] == "Progressive" else "#d6604d")
               for a in ADMIN_ORDER}

# Compute admin stats (김대중 excluded -- only 2 entries, partial)
adm = df[df["admin"].isin(ADMIN_ORDER)].copy()
admin_stats = (adm.groupby("admin")["dual_office"]
               .agg(["sum", "count"])
               .rename(columns={"sum": "n_dual", "count": "n_total"})
               .reindex(ADMIN_ORDER))
admin_stats["rate"] = admin_stats["n_dual"] / admin_stats["n_total"] * 100

# ── Figure layout ─────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(14, 11), facecolor="white")
fig.subplots_adjust(hspace=0.42, wspace=0.38)

gs = fig.add_gridspec(2, 2)
ax1 = fig.add_subplot(gs[0, 0])   # A: admin bar chart
ax2 = fig.add_subplot(gs[0, 1])   # B: timeline / Gantt
ax3 = fig.add_subplot(gs[1, 0])   # C: top ministries
ax4 = fig.add_subplot(gs[1, 1])   # D: scatter

GRAY_BG = "#f8f8f8"
for ax in [ax1, ax2, ax3, ax4]:
    ax.set_facecolor(GRAY_BG)
    ax.spines[["top", "right"]].set_visible(False)

# ── Panel A: Dual-office rate by administration ────────────────────────────────
x = np.arange(len(ADMIN_ORDER))
bars = ax1.bar(x, admin_stats["rate"],
               color=[ADM_COLORS[a] for a in ADMIN_ORDER],
               edgecolor="white", linewidth=1.2, zorder=3, width=0.65)

# Rate labels on bars
for bar, n_d, n_t, rate in zip(bars, admin_stats["n_dual"],
                                admin_stats["n_total"], admin_stats["rate"]):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.8,
             f"{rate:.0f}%\n({n_d}/{n_t})",
             ha="center", va="bottom", fontsize=7.5, color="#333333")

ax1.set_xticks(x)
ax1.set_xticklabels(ADMIN_ORDER, fontsize=9)
ax1.set_ylabel("Dual-office rate (%)", fontsize=9)
ax1.set_ylim(0, 58)
ax1.yaxis.grid(True, linestyle="--", alpha=0.5, zorder=0)
ax1.set_axisbelow(True)
ax1.set_title("A  Dual-office rate by administration", fontsize=10,
              fontweight="bold", loc="left", pad=6)

prog_patch = mpatches.Patch(color="#2166ac", label="Progressive")
cons_patch = mpatches.Patch(color="#d6604d", label="Conservative")
ax1.legend(handles=[prog_patch, cons_patch], fontsize=8,
           loc="upper left", framealpha=0.8)

# ── Panel B: Gantt timeline of dual-office appointments ───────────────────────
dual = adm[adm["dual_office"]].copy()
dual["admin_idx"] = dual["admin"].map({a: i for i, a in enumerate(ADMIN_ORDER)})

# Drop rows with missing start (safety)
dual = dual.dropna(subset=["start_dt"])

# Fill missing end dates with data collection date proxy
CUTOFF_YEAR = 2025.25
dual["end_dt_filled"] = dual["end_dt"].fillna(pd.Timestamp("2025-04-01"))

dual_sorted = dual.sort_values(["admin_idx", "start_dt"]).reset_index(drop=True)

for i, row in dual_sorted.iterrows():
    start_yr = row["start_dt"].year + (row["start_dt"].month - 1) / 12
    end_yr   = row["end_dt_filled"].year + (row["end_dt_filled"].month - 1) / 12
    width    = max(end_yr - start_yr, 0.08)  # min width for visibility

    ax2.barh(i, width, left=start_yr,
             height=0.75, color=ADM_COLORS[row["admin"]], alpha=0.78, zorder=3)

ax2.set_xlim(2003, 2026)
ax2.set_ylim(-1, len(dual_sorted))
ax2.set_xlabel("Year", fontsize=9)
ax2.set_ylabel("Dual-office ministers", fontsize=9)
ax2.set_yticks([])
ax2.xaxis.grid(True, linestyle="--", alpha=0.4, zorder=0)
ax2.set_axisbelow(True)
ax2.set_title("B  Dual-office ministerial tenures (2003-2025)", fontsize=10,
              fontweight="bold", loc="left", pad=6)

# Admin boundary lines
ADMIN_START = {"노무현": 2003.15, "이명박": 2008.21, "박근혜": 2013.15,
               "문재인": 2017.46, "윤석열": 2022.37, "이재명": 2025.5}
for adm_name, yr in ADMIN_START.items():
    if yr < 2026:
        ax2.axvline(yr, color="#888888", lw=0.8, linestyle=":", zorder=2)
        ax2.text(yr + 0.05, len(dual_sorted) - 0.5, adm_name,
                 fontsize=6.5, color="#555555", va="top", rotation=0)

ax2.legend(handles=[prog_patch, cons_patch], fontsize=8,
           loc="lower right", framealpha=0.8)

# ── Panel C: Ministry dual-office rates (min 4 appointments) ─────────────────
min_count = 4
ministry_stats = (adm.groupby("ministry")["dual_office"]
                  .agg(["mean", "sum", "count"])
                  .rename(columns={"mean": "rate", "sum": "n_dual", "count": "n_total"})
                  .query("n_total >= @min_count")
                  .sort_values("rate", ascending=True)
                  .tail(12))

y = np.arange(len(ministry_stats))
ax3.barh(y, ministry_stats["rate"] * 100,
         color="#2166ac", alpha=0.78, edgecolor="white", linewidth=0.8, zorder=3)

for j, (rate, n_d, n_t) in enumerate(zip(ministry_stats["rate"],
                                          ministry_stats["n_dual"],
                                          ministry_stats["n_total"])):
    ax3.text(rate * 100 + 0.8, j, f"{rate*100:.0f}% ({n_d}/{n_t})",
             va="center", fontsize=7.5, color="#333333")

ax3.set_yticks(y)
ax3.set_yticklabels(ministry_stats.index, fontsize=8)
ax3.set_xlabel("Dual-office rate (%)", fontsize=9)
ax3.set_xlim(0, 115)
ax3.xaxis.grid(True, linestyle="--", alpha=0.5, zorder=0)
ax3.set_axisbelow(True)
ax3.set_title(f"C  Ministries with highest dual-office rates\n"
              f"(minimum {min_count} appointments)", fontsize=10,
              fontweight="bold", loc="left", pad=6)

# ── Panel D: Ministry size vs. dual-office rate (scatter) ────────────────────
ministry_all = (adm.groupby("ministry")["dual_office"]
                .agg(["mean", "sum", "count"])
                .rename(columns={"mean": "rate", "sum": "n_dual", "count": "n_total"}))

sc = ax4.scatter(ministry_all["n_total"], ministry_all["rate"] * 100,
                 s=ministry_all["n_dual"] * 18 + 20,
                 color="#2166ac", alpha=0.55, edgecolor="white", linewidth=0.6, zorder=3)

# Label selected large or high-rate ministries
LABEL_THRESHOLD = 8
for name, row in ministry_all.iterrows():
    if row["n_total"] >= LABEL_THRESHOLD or row["rate"] >= 0.45:
        ax4.annotate(name, (row["n_total"], row["rate"] * 100),
                     xytext=(4, 2), textcoords="offset points",
                     fontsize=6.5, color="#333333")

ax4.set_xlabel("Total appointments (N)", fontsize=9)
ax4.set_ylabel("Dual-office rate (%)", fontsize=9)
ax4.set_ylim(-5, 110)
ax4.xaxis.grid(True, linestyle="--", alpha=0.4, zorder=0)
ax4.yaxis.grid(True, linestyle="--", alpha=0.4, zorder=0)
ax4.set_axisbelow(True)
ax4.set_title("D  Ministry size vs. dual-office rate\n(bubble = # dual-office ministers)",
              fontsize=10, fontweight="bold", loc="left", pad=6)

# ── Super title ───────────────────────────────────────────────────────────────
fig.suptitle("Korean Dual-Office Ministers (겸직 국무위원), 2003-2025\n"
             "Yang (2025) — github.com/kyusik-yang/minister-data",
             fontsize=12, fontweight="bold", y=0.98, color="#222222")

# ── Save ──────────────────────────────────────────────────────────────────────
OUT = Path(__file__).parent / "overview.png"
fig.savefig(OUT, dpi=180, bbox_inches="tight", facecolor="white")
print(f"Saved: {OUT}")
