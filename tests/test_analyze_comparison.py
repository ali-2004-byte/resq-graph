"""
tests/test_analyze_comparison.py – Sprint 9 (US-034)

Unit tests for ComparisonAnalyser and report writer.
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.analyze_comparison import (
    ComparisonAnalyser,
    _mean,
    _std,
    _cohens_d,
    _paired_ttest,
    write_report,
    generate_all_plots,
)

FIELDS = ["run_id", "seed", "n_events", "mean_art", "std_art", "ticks"]


def _write_csv(path: str, rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def _make_rows(arts: list[float], seeds: list[int] | None = None) -> list[dict]:
    seeds = seeds or list(range(len(arts)))
    return [
        {"run_id": i, "seed": s, "n_events": 50, "mean_art": a, "std_art": 1.0, "ticks": 1000}
        for i, (a, s) in enumerate(zip(arts, seeds))
    ]


# ── Statistics helpers ────────────────────────────────────────────────────────

def test_mean_basic():
    assert abs(_mean([1.0, 2.0, 3.0]) - 2.0) < 1e-9


def test_std_ddof1():
    vals = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    # Population std (ddof=0) = 2.0; sample std (ddof=1) ≈ 2.138
    result = _std(vals, ddof=1)
    assert result > 0
    assert abs(result - 2.138) < 0.01


def test_cohens_d_positive_when_a_greater():
    a = [30.0 + i * 0.1 for i in range(10)]
    b = [20.0 + i * 0.1 for i in range(10)]
    assert _cohens_d(a, b) > 0


def test_cohens_d_sign_ai_better():
    """Positive d when baseline ART > AI ART (baseline=a, ai=b)."""
    baseline = [28.0 + i * 0.2 for i in range(8)]
    ai       = [22.0 + i * 0.2 for i in range(8)]
    d = _cohens_d(baseline, ai)
    assert d > 0, "Cohen's d should be positive when baseline ART > AI ART"


def test_paired_ttest_significant():
    """t-stat > 0 and p < 0.05 for a clearly different pair."""
    a = [30.0 + i * 0.1 for i in range(10)]
    b = [20.0 + i * 0.1 for i in range(10)]
    t, p = _paired_ttest(a, b)
    assert t > 0
    assert p < 0.05


def test_paired_ttest_no_difference():
    """Identical arrays → either NaN or p ≥ 0.05 (no detectable difference)."""
    import math
    arr = [25.0] * 10
    _, p = _paired_ttest(arr, arr[:])
    # scipy returns NaN for zero-variance differences; treat as non-significant
    assert math.isnan(p) or p >= 0.05


# ── ComparisonAnalyser tests ──────────────────────────────────────────────────

def test_analyser_perfect_improvement(tmp_path):
    """AI ART = baseline - 3 → pct_improvement ≈ 30%."""
    b_arts = [10.0] * 10
    a_arts = [7.0]  * 10
    seeds  = list(range(10))

    b_csv = str(tmp_path / "baseline.csv")
    a_csv = str(tmp_path / "ai.csv")
    _write_csv(b_csv, _make_rows(b_arts, seeds))
    _write_csv(a_csv, _make_rows(a_arts, seeds))

    analyser = ComparisonAnalyser(baseline_csv=b_csv, ai_csv=a_csv)
    m = analyser.compute()

    assert abs(m["pct_improvement"] - 30.0) < 0.5


def test_analyser_no_improvement(tmp_path):
    """Identical ARTs → not significant."""
    arts  = [25.0] * 10
    seeds = list(range(10))
    b_csv = str(tmp_path / "baseline.csv")
    a_csv = str(tmp_path / "ai.csv")
    _write_csv(b_csv, _make_rows(arts, seeds))
    _write_csv(a_csv, _make_rows(arts, seeds))

    analyser = ComparisonAnalyser(baseline_csv=b_csv, ai_csv=a_csv)
    m = analyser.compute()

    assert m["significant"] is False


def test_analyser_seed_mismatch_raises(tmp_path):
    """AssertionError when seeds differ between CSVs."""
    b_csv = str(tmp_path / "baseline.csv")
    a_csv = str(tmp_path / "ai.csv")
    _write_csv(b_csv, _make_rows([25.0] * 5, seeds=[0, 1, 2, 3, 4]))
    _write_csv(a_csv, _make_rows([22.0] * 5, seeds=[10, 11, 12, 13, 14]))

    with pytest.raises(AssertionError):
        ComparisonAnalyser(baseline_csv=b_csv, ai_csv=a_csv)


# ── write_report tests ────────────────────────────────────────────────────────

def test_write_report_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr("src.analyze_comparison.REPORT_PATH",
                        str(tmp_path / "report.md"))
    metrics = {
        "baseline_mean_art": 25.0,
        "baseline_std_art":  1.5,
        "ai_mean_art":       20.0,
        "ai_std_art":        1.0,
        "pct_improvement":   20.0,
        "t_statistic":       4.5,
        "p_value":           0.001,
        "cohens_d":          1.2,
        "significant":       True,
        "n_runs":            10,
    }
    write_report(metrics, plot_paths={})
    rpt = tmp_path / "report.md"
    assert rpt.exists() and rpt.stat().st_size > 0


def test_report_significance_language(tmp_path, monkeypatch):
    monkeypatch.setattr("src.analyze_comparison.REPORT_PATH",
                        str(tmp_path / "report_sig.md"))
    metrics = {
        "baseline_mean_art": 25.0, "baseline_std_art": 1.5,
        "ai_mean_art": 20.0, "ai_std_art": 1.0,
        "pct_improvement": 20.0, "t_statistic": 5.0,
        "p_value": 0.001, "cohens_d": 1.5, "significant": True, "n_runs": 10,
    }
    write_report(metrics, plot_paths={})
    content = (tmp_path / "report_sig.md").read_text()
    assert "significant" in content.lower()


def test_report_not_significant_language(tmp_path, monkeypatch):
    monkeypatch.setattr("src.analyze_comparison.REPORT_PATH",
                        str(tmp_path / "report_ns.md"))
    metrics = {
        "baseline_mean_art": 25.0, "baseline_std_art": 1.5,
        "ai_mean_art": 24.5, "ai_std_art": 1.5,
        "pct_improvement": 2.0, "t_statistic": 0.5,
        "p_value": 0.62, "cohens_d": 0.1, "significant": False, "n_runs": 10,
    }
    write_report(metrics, plot_paths={})
    content = (tmp_path / "report_ns.md").read_text()
    # Report should say "not statistically significant" when significant=False
    assert "not statistically significant" in content


def test_generate_all_plots_creates_pngs(tmp_path, monkeypatch):
    """All 4 PNGs are created in outputs/figures/."""
    import matplotlib
    matplotlib.use("Agg")   # force non-interactive backend before any plt call

    monkeypatch.setattr("src.analyze_comparison.FIGURES_DIR", str(tmp_path / "figures"))
    monkeypatch.setattr("src.analyze_comparison.NODE_POSITIONS",
                        "data/node_positions.json")
    monkeypatch.setattr("src.analyze_comparison.OPTIMAL_STATIONS",
                        "outputs/optimal_stations.json")
    monkeypatch.setattr("src.analyze_comparison.FLEET_LOG",
                        "outputs/random_fleet_log.json")
    monkeypatch.setattr("src.analyze_comparison.DISTANCE_MATRIX",
                        "data/distance_matrix.npy")

    metrics = {
        "baseline_mean_art": 25.0, "baseline_std_art": 1.5,
        "ai_mean_art": 20.0, "ai_std_art": 1.0,
        "pct_improvement": 20.0, "t_statistic": 4.5,
        "p_value": 0.001, "cohens_d": 1.2, "significant": True, "n_runs": 10,
        "baseline_arts": [25.0 + i * 0.1 for i in range(10)],
        "ai_arts":       [20.0 + i * 0.1 for i in range(10)],
    }
    paths = generate_all_plots(metrics)
    assert len(paths) == 4
    for name, path in paths.items():
        assert os.path.isfile(path), f"Missing plot: {name} -> {path}"
