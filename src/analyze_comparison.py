"""
analyze_comparison.py – Sprint 9 (US-034 + US-036)

Loads baseline_results.csv and ai_results.csv, performs a paired two-tailed
t-test, computes Cohen's d effect size, generates four Matplotlib comparison
plots, and writes outputs/comparison_report.md.

Usage
-----
    python src/analyze_comparison.py

Outputs
-------
    outputs/comparison_metrics.json
    outputs/figures/comparison_art_distribution.png
    outputs/figures/comparison_art_timeseries.png
    outputs/figures/comparison_coverage_heatmap.png
    outputs/figures/comparison_station_placement.png
    outputs/comparison_report.md
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from datetime import datetime, timezone

# Force non-interactive (no display, no Tk) backend BEFORE any pyplot import.
# This must happen at module level – calling matplotlib.use() inside a function
# is too late once pyplot has been imported elsewhere in the same process.
import matplotlib
matplotlib.use("Agg")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASELINE_CSV     = "outputs/baseline_results.csv"
AI_CSV           = "outputs/ai_results.csv"
METRICS_JSON     = "outputs/comparison_metrics.json"
REPORT_PATH      = "outputs/comparison_report.md"
FIGURES_DIR      = "outputs/figures"
FLEET_LOG        = "outputs/random_fleet_log.json"
OPTIMAL_STATIONS = "outputs/optimal_stations.json"
NODE_POSITIONS   = "data/node_positions.json"
DISTANCE_MATRIX  = "data/distance_matrix.npy"


# ── Data loading ──────────────────────────────────────────────────────────────

def _load_csv(path: str, label: str) -> list[dict]:
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"{label} CSV not found: {path!r}\n"
            "Run the corresponding batch runner first."
        )
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if str(row.get("run_id", "")).upper() == "SUMMARY":
                continue
            rows.append({
                "run_id":   int(row["run_id"]),
                "seed":     int(row["seed"]),
                "n_events": int(row["n_events"]),
                "mean_art": float(row["mean_art"]),
                "std_art":  float(row["std_art"]),
                "ticks":    int(row["ticks"]),
            })
    return rows


# ── Statistics ────────────────────────────────────────────────────────────────

def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: list[float], ddof: int = 1) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - ddof))


def _paired_ttest(a: list[float], b: list[float]) -> tuple[float, float]:
    """Paired two-tailed t-test. Returns (t_statistic, p_value)."""
    try:
        from scipy import stats as _scipy_stats
        t, p = _scipy_stats.ttest_rel(a, b)
        return float(t), float(p)
    except ImportError:
        pass
    # Pure-Python fallback (Student's t on differences)
    if len(a) != len(b) or len(a) < 2:
        return 0.0, 1.0
    diffs = [ai - bi for ai, bi in zip(a, b)]
    n = len(diffs)
    d_mean = _mean(diffs)
    d_std  = _std(diffs, ddof=1)
    if d_std == 0:
        return 0.0, 1.0
    t_stat = d_mean / (d_std / math.sqrt(n))
    # Approximate two-tailed p-value via beta function incomplete ratio
    # For small n use a lookup; else return a conservative bound
    t_abs = abs(t_stat)
    df    = n - 1
    # Simple approximation: p ≈ 2 * (1 - normal_cdf(|t|)) for large df
    # Use a rough polynomial approximation for the normal CDF tail
    z = t_abs
    p_approx = math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi) / (z + 0.001)
    p_approx = max(0.0, min(1.0, 2.0 * p_approx))
    return t_stat, p_approx


def _cohens_d(a: list[float], b: list[float]) -> float:
    """Cohen's d = (mean_a - mean_b) / pooled_std. Positive when a > b."""
    if len(a) < 2 or len(b) < 2:
        return 0.0
    pooled = math.sqrt((_std(a, ddof=1) ** 2 + _std(b, ddof=1) ** 2) / 2)
    if pooled == 0:
        return 0.0
    return (_mean(a) - _mean(b)) / pooled


class ComparisonAnalyser:
    """Load baseline and AI results, run statistical comparison.

    Parameters
    ----------
    baseline_csv : str
        Path to outputs/baseline_results.csv
    ai_csv : str
        Path to outputs/ai_results.csv
    """

    def __init__(
        self,
        baseline_csv: str = BASELINE_CSV,
        ai_csv: str = AI_CSV,
    ) -> None:
        self.baseline_rows = _load_csv(baseline_csv, "Baseline")
        self.ai_rows       = _load_csv(ai_csv,       "AI fleet")

        # Verify seeds align
        b_seeds = [r["seed"] for r in self.baseline_rows]
        a_seeds = [r["seed"] for r in self.ai_rows]
        assert b_seeds == a_seeds, (
            f"Seed mismatch between baseline and AI CSVs.\n"
            f"Baseline seeds: {b_seeds}\nAI seeds: {a_seeds}"
        )
        self.seeds = b_seeds

    def compute(self) -> dict:
        """Run all statistical tests and return a metrics dict."""
        b_arts = [r["mean_art"] for r in self.baseline_rows]
        a_arts = [r["mean_art"] for r in self.ai_rows]

        b_mean = _mean(b_arts)
        a_mean = _mean(a_arts)
        b_std  = _std(b_arts, ddof=1)
        a_std  = _std(a_arts, ddof=1)

        t_stat, p_val   = _paired_ttest(b_arts, a_arts)
        cohens_d        = _cohens_d(b_arts, a_arts)
        pct_improvement = ((b_mean - a_mean) / b_mean * 100) if b_mean else 0.0

        significant = p_val < 0.05

        metrics = {
            "baseline_mean_art": round(b_mean, 3),
            "baseline_std_art":  round(b_std,  3),
            "ai_mean_art":       round(a_mean, 3),
            "ai_std_art":        round(a_std,  3),
            "pct_improvement":   round(pct_improvement, 2),
            "t_statistic":       round(t_stat, 4),
            "p_value":           round(p_val,  6),
            "cohens_d":          round(cohens_d, 4),
            "significant":       significant,
            "n_runs":            len(b_arts),
            "baseline_arts":     b_arts,
            "ai_arts":           a_arts,
        }
        return metrics


# ── Visualization ─────────────────────────────────────────────────────────────

def generate_all_plots(metrics: dict) -> dict[str, str]:
    """Generate all four comparison plots. Returns {name: path}."""
    paths = {}
    paths["art_distribution"] = _plot_art_distribution(metrics)
    paths["art_timeseries"]   = _plot_art_timeseries(metrics)
    paths["coverage_heatmap"] = _plot_coverage_heatmap()
    paths["station_placement"] = _plot_station_placement()
    return paths


def _dark_fig(figsize=(9, 5)):
    import matplotlib.pyplot as plt
    _BG, _PAN, _TXT, _MUT = "#0f172a", "#1e293b", "#e2e8f0", "#64748b"
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_PAN)
    ax.tick_params(colors=_TXT, labelsize=9)
    ax.xaxis.label.set_color(_TXT)
    ax.yaxis.label.set_color(_TXT)
    ax.title.set_color(_TXT)
    for sp in ax.spines.values():
        sp.set_edgecolor(_MUT)
    return fig, ax, _BG, _PAN, _TXT, _MUT


def _save(fig, name: str) -> str:
    import matplotlib.pyplot as plt
    os.makedirs(FIGURES_DIR, exist_ok=True)
    path = os.path.join(FIGURES_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [US-035] Saved -> {path}")
    return path


def _plot_art_distribution(metrics: dict) -> str:
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    import numpy as np

    b_arts = metrics["baseline_arts"]
    a_arts = metrics["ai_arts"]

    fig, ax, _, _PAN, _TXT, _MUT = _dark_fig((9, 5))

    bins = np.linspace(min(b_arts + a_arts) - 1, max(b_arts + a_arts) + 1, 12)
    ax.hist(b_arts, bins=bins, alpha=0.6, color="#818cf8", label="Random baseline", zorder=2)
    ax.hist(a_arts, bins=bins, alpha=0.6, color="#34d399", label="AI optimised",    zorder=2)
    ax.axvline(metrics["baseline_mean_art"], color="#818cf8", linestyle="--", linewidth=1.5, zorder=3)
    ax.axvline(metrics["ai_mean_art"],       color="#34d399", linestyle="--", linewidth=1.5, zorder=3)

    sig_label = "significant" if metrics["significant"] else "not significant"
    ax.set_title(
        f"ART Distribution Comparison  |  Δ={metrics['pct_improvement']:+.1f}%  "
        f"p={metrics['p_value']:.4f} ({sig_label})",
        fontsize=12, pad=10
    )
    ax.set_xlabel("Mean ART (ticks)", fontsize=11)
    ax.set_ylabel("Number of runs", fontsize=11)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.legend(facecolor=_PAN, labelcolor=_TXT, fontsize=9)
    ax.grid(axis="y", color=_MUT, alpha=0.3)
    plt.tight_layout()
    return _save(fig, "comparison_art_distribution.png")


def _plot_art_timeseries(metrics: dict) -> str:
    import matplotlib.pyplot as plt

    b_arts = metrics["baseline_arts"]
    a_arts = metrics["ai_arts"]
    xs     = list(range(len(b_arts)))

    fig, ax, _, _PAN, _TXT, _MUT = _dark_fig((10, 5))

    ax.plot(xs, b_arts, "o--", color="#818cf8", linewidth=1.8, markersize=6,
            label=f"Baseline (μ={metrics['baseline_mean_art']:.1f})")
    ax.plot(xs, a_arts, "s-",  color="#34d399", linewidth=1.8, markersize=6,
            label=f"AI fleet  (μ={metrics['ai_mean_art']:.1f})")
    ax.fill_between(xs, b_arts, a_arts,
                    where=[b > a for b, a in zip(b_arts, a_arts)],
                    alpha=0.15, color="#34d399", label="AI improvement")

    ax.set_title("ART per Run — Baseline vs AI Fleet", fontsize=13, pad=10)
    ax.set_xlabel("Run ID", fontsize=11)
    ax.set_ylabel("Mean ART (ticks)", fontsize=11)
    ax.set_xticks(xs)
    ax.legend(facecolor=_PAN, labelcolor=_TXT, fontsize=9)
    ax.grid(axis="y", color=_MUT, alpha=0.3)
    plt.tight_layout()
    return _save(fig, "comparison_art_timeseries.png")


def _plot_coverage_heatmap() -> str:
    """Coverage heatmap: colour each node by min distance to nearest station."""
    import matplotlib.pyplot as plt
    import numpy as np
    import json as _json

    fig, ax, _BG, _PAN, _TXT, _MUT = _dark_fig((9, 7))

    try:
        with open(NODE_POSITIONS, "r") as fh:
            raw = _json.load(fh)
        node_positions = {int(k): v for k, v in raw.items()}

        with open(OPTIMAL_STATIONS, "r") as fh:
            opt = _json.load(fh)
        if isinstance(opt, dict):
            station_ids = [int(x) for x in opt.get("optimal_stations", opt.get("stations", []))]
        else:
            station_ids = [int(x) for x in opt]

        all_nodes   = list(node_positions.keys())
        node_index  = {n: i for i, n in enumerate(all_nodes)}

        # Use distance matrix if available, else Euclidean fallback
        use_matrix = os.path.isfile(DISTANCE_MATRIX)
        if use_matrix:
            dm = np.load(DISTANCE_MATRIX)
            s_idx = [node_index[s] for s in station_ids if s in node_index]
            min_dists = np.min(dm[:, s_idx], axis=1) if s_idx else np.zeros(len(all_nodes))
        else:
            def _euc(a, b):
                return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)
            s_pos = [node_positions[s] for s in station_ids if s in node_positions]
            min_dists = np.array([
                min((_euc(node_positions[n], sp) for sp in s_pos), default=0)
                for n in all_nodes
            ])

        xs = [node_positions[n][0] for n in all_nodes]
        ys = [node_positions[n][1] for n in all_nodes]
        sc = ax.scatter(xs, ys, c=min_dists, cmap="RdYlGn_r", s=4, zorder=2)
        plt.colorbar(sc, ax=ax, label="Min distance to nearest station (ticks)")

        # Plot station markers
        sx = [node_positions[s][0] for s in station_ids if s in node_positions]
        sy = [node_positions[s][1] for s in node_positions if s in station_ids]
        sy = [node_positions[s][1] for s in station_ids if s in node_positions]
        ax.scatter(sx, sy, c="#34d399", s=120, marker="*", zorder=5, label="AI stations")
        ax.legend(facecolor=_PAN, labelcolor=_TXT, fontsize=9)

    except Exception as exc:
        ax.text(0.5, 0.5, f"Coverage data unavailable\n{exc}",
                ha="center", va="center", color=_TXT, transform=ax.transAxes)

    ax.set_title("Coverage Heatmap — AI Optimised Fleet", fontsize=13, pad=10)
    ax.set_xlabel("X (pixel)", fontsize=10)
    ax.set_ylabel("Y (pixel)", fontsize=10)
    plt.tight_layout()
    return _save(fig, "comparison_coverage_heatmap.png")


def _plot_station_placement() -> str:
    """Scatter: all random placements (faint) + AI stations (bright)."""
    import matplotlib.pyplot as plt
    import json as _json

    fig, ax, _BG, _PAN, _TXT, _MUT = _dark_fig((9, 7))

    try:
        with open(NODE_POSITIONS, "r") as fh:
            node_positions = {int(k): v for k, v in _json.load(fh).items()}

        # Random placements from fleet log
        if os.path.isfile(FLEET_LOG):
            with open(FLEET_LOG, "r") as fh:
                log = _json.load(fh)
            # Use only the first batch (first 10 entries by repeat 0-9)
            seen = set()
            placements = []
            for entry in log:
                key = (entry["seed"], entry["repeat"])
                if key not in seen:
                    seen.add(key)
                    placements.append(entry)
                if len(seen) >= 10:
                    break

            for entry in placements:
                xs = [node_positions[int(n)][0] for n in entry["nodes"] if int(n) in node_positions]
                ys = [node_positions[int(n)][1] for n in entry["nodes"] if int(n) in node_positions]
                ax.scatter(xs, ys, c="#818cf8", s=25, alpha=0.35, zorder=2)

        # AI optimal stations
        with open(OPTIMAL_STATIONS, "r") as fh:
            opt = _json.load(fh)
        if isinstance(opt, dict):
            station_ids = [int(x) for x in opt.get("optimal_stations", opt.get("stations", []))]
        else:
            station_ids = [int(x) for x in opt]

        sx = [node_positions[s][0] for s in station_ids if s in node_positions]
        sy = [node_positions[s][1] for s in station_ids if s in node_positions]
        ax.scatter(sx, sy, c="#34d399", s=160, marker="*", zorder=5, label="AI optimised stations")
        ax.scatter([], [], c="#818cf8", s=25, alpha=0.6, label="Random placements")
        ax.legend(facecolor=_PAN, labelcolor=_TXT, fontsize=9)

    except Exception as exc:
        ax.text(0.5, 0.5, f"Placement data unavailable\n{exc}",
                ha="center", va="center", color=_TXT, transform=ax.transAxes)

    ax.set_title("Station Placement — Random vs AI Optimised", fontsize=13, pad=10)
    ax.set_xlabel("X (pixel)", fontsize=10)
    ax.set_ylabel("Y (pixel)", fontsize=10)
    plt.tight_layout()
    return _save(fig, "comparison_station_placement.png")


# ── Report writer ─────────────────────────────────────────────────────────────

def write_report(metrics: dict, plot_paths: dict) -> None:
    """Write outputs/comparison_report.md."""
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    ts  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sig_phrase = "**statistically significant**" if metrics["significant"] else "**not statistically significant**"

    def _img(key: str) -> str:
        path = plot_paths.get(key, "")
        rel  = os.path.relpath(path, os.path.dirname(REPORT_PATH)) if path else key
        return f"![{key}]({rel.replace(os.sep, '/')})"

    report = f"""# Fleet Comparison Report — AI vs Random Baseline (Sprint 9)

*Generated automatically by `src/analyze_comparison.py` on {ts}*

---

## Summary

| Metric | Baseline (Random) | AI Optimised | Δ |
|--------|:-----------------:|:------------:|:---:|
| Grand mean ART (ticks) | {metrics['baseline_mean_art']:.2f} | {metrics['ai_mean_art']:.2f} | {metrics['pct_improvement']:+.1f}% |
| Std dev across runs | {metrics['baseline_std_art']:.2f} | {metrics['ai_std_art']:.2f} | — |

---

## Statistical Analysis

| Test | Value |
|------|-------|
| Paired t-statistic | {metrics['t_statistic']:.4f} |
| Two-tailed p-value | {metrics['p_value']:.6f} |
| Cohen's d | {metrics['cohens_d']:.4f} |
| Significant (α=0.05) | {"Yes ✓" if metrics['significant'] else "No ✗"} |

The improvement is {sig_phrase} (p={metrics['p_value']:.4f}).
{"A positive Cohen's d = " + str(metrics['cohens_d']) + " indicates the AI fleet outperforms the random baseline." if metrics['cohens_d'] > 0 else "Cohen's d is negative or zero, indicating no performance advantage."}

---

## Visualizations

### ART Distribution
{_img("art_distribution")}

### ART per Run (Time-Series)
{_img("art_timeseries")}

### Coverage Heatmap — AI Fleet
{_img("coverage_heatmap")}

### Station Placement Comparison
{_img("station_placement")}

---

## Methodology

- **Baseline**: {metrics['n_runs']} runs × 1000 ticks with random station placement
  (`src/run_baseline.py`, Sprint 8).
- **AI fleet**: Same {metrics['n_runs']} runs × 1000 ticks with GA-optimised fixed stations
  (`src/run_ai_fleet.py`, Sprint 9).
- **Seed parity**: Both experiments used identical per-run event seeds to ensure
  the event sequence is identical for each paired run.
- **Test**: Paired two-tailed Student's t-test on per-run mean ART vectors.
- **Effect size**: Cohen's d using pooled standard deviation.

---

## Conclusion

{"The GA-optimised fleet achieves a " + str(abs(metrics['pct_improvement'])) + "% reduction in mean ART compared to random placement. The improvement is statistically significant, providing strong evidence that intelligent station placement reduces emergency response times." if metrics['significant'] and metrics['pct_improvement'] > 0 else "The experiment did not detect a statistically significant improvement. Review GA convergence (Sprint 3) or increase the number of simulation runs for higher statistical power."}
"""

    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write(report)
    print(f"[US-036] Report written -> {REPORT_PATH}")

    # Optional PDF via pandoc (graceful if absent)
    pdf_path = REPORT_PATH.replace(".md", ".pdf")
    try:
        import subprocess
        result = subprocess.run(
            ["pandoc", REPORT_PATH, "-o", pdf_path],
            capture_output=True, timeout=30,
        )
        if result.returncode == 0:
            print(f"[US-036] PDF written -> {pdf_path}")
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass  # pandoc absent – PDF is optional


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    print("\n[Comparison] Loading results ...")
    analyser = ComparisonAnalyser()
    metrics  = analyser.compute()

    print(f"[Comparison] Baseline ART = {metrics['baseline_mean_art']:.2f} ticks")
    print(f"[Comparison] AI ART       = {metrics['ai_mean_art']:.2f} ticks")
    print(f"[Comparison] Improvement  = {metrics['pct_improvement']:+.1f}%")
    print(f"[Comparison] t={metrics['t_statistic']:.3f}  p={metrics['p_value']:.4f}  "
          f"d={metrics['cohens_d']:.3f}  significant={metrics['significant']}")

    # Save metrics JSON (exclude raw arrays for portability)
    json_metrics = {k: v for k, v in metrics.items() if k not in ("baseline_arts", "ai_arts")}
    os.makedirs("outputs", exist_ok=True)
    with open(METRICS_JSON, "w", encoding="utf-8") as fh:
        json.dump(json_metrics, fh, indent=2)
    print(f"[Comparison] Metrics JSON -> {METRICS_JSON}")

    print("[Comparison] Generating plots ...")
    plot_paths = generate_all_plots(metrics)

    print("[Comparison] Writing report ...")
    write_report(metrics, plot_paths)

    print("\n[Comparison] Done.")


if __name__ == "__main__":
    main()
