# Fleet Comparison Report — AI vs Random Baseline (Sprint 9)

*Generated automatically by `src/analyze_comparison.py` on 2026-05-09 08:05 UTC*

---

## Summary

| Metric | Baseline (Random) | AI Optimised | Δ |
|--------|:-----------------:|:------------:|:---:|
| Grand mean ART (ticks) | 25.73 | 23.09 | +10.3% |
| Std dev across runs | 2.00 | 2.52 | — |

---

## Statistical Analysis

| Test | Value |
|------|-------|
| Paired t-statistic | 3.5834 |
| Two-tailed p-value | 0.005899 |
| Cohen's d | 1.1630 |
| Significant (α=0.05) | Yes ✓ |

The improvement is **statistically significant** (p=0.0059).
A positive Cohen's d = 1.163 indicates the AI fleet outperforms the random baseline.

---

## Visualizations

### ART Distribution
![art_distribution](figures/comparison_art_distribution.png)

### ART per Run (Time-Series)
![art_timeseries](figures/comparison_art_timeseries.png)

### Coverage Heatmap — AI Fleet
![coverage_heatmap](figures/comparison_coverage_heatmap.png)

### Station Placement Comparison
![station_placement](figures/comparison_station_placement.png)

---

## Methodology

- **Baseline**: 10 runs × 1000 ticks with random station placement
  (`src/run_baseline.py`, Sprint 8).
- **AI fleet**: Same 10 runs × 1000 ticks with GA-optimised fixed stations
  (`src/run_ai_fleet.py`, Sprint 9).
- **Seed parity**: Both experiments used identical per-run event seeds to ensure
  the event sequence is identical for each paired run.
- **Test**: Paired two-tailed Student's t-test on per-run mean ART vectors.
- **Effect size**: Cohen's d using pooled standard deviation.

---

## Conclusion

The GA-optimised fleet achieves a 10.28% reduction in mean ART compared to random placement. The improvement is statistically significant, providing strong evidence that intelligent station placement reduces emergency response times.
