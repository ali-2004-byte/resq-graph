"""
run_ai_fleet.py – Sprint 9 (US-033)

Batch AI-fleet runner. Loads GA-optimised station locations from
``outputs/optimal_stations.json`` (Sprint 3 deliverable, read-only),
then executes the simulation headlessly N times using the same per-run
event seeds as the Sprint 8 baseline, collecting ART via MetricsTracker.

Outputs
-------
outputs/ai_results.csv         — per-run summary (same schema as baseline_results.csv)
outputs/ai_response_times.csv  — every individual response time across all runs

Usage
-----
    python src/run_ai_fleet.py --headless --config headless_ai.yaml

Flags
-----
    --headless         Set SDL_VIDEODRIVER=dummy (must precede any pygame init)
    --config PATH      YAML config file (default: headless_ai.yaml)
    --ticks N          Override ticks_per_run from config
    --seeds N [N ...]  Override per-run seeds (space-separated integers)
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import os
import sys

# ── Headless env var MUST be set before any pygame-importing project module ────
_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument("--headless", action="store_true")
_pre, _ = _parser.parse_known_args()
if _pre.headless:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"

# ── Now safe to import project modules ────────────────────────────────────────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.sim_config_loader import load_sim_config                      # noqa: E402
from src.simulation.simulation_engine import (                         # noqa: E402
    load_graph,
    load_node_positions,
    run_simulation,
)
from src.simulation.sim_logger import setup_logging                    # noqa: E402

logger = logging.getLogger(__name__)

# ── Output paths ──────────────────────────────────────────────────────────────
AI_CSV          = "outputs/ai_results.csv"
AI_RT_CSV       = "outputs/ai_response_times.csv"
OPTIMAL_STATIONS = "outputs/optimal_stations.json"

_FIELDS = ["run_id", "seed", "n_events", "mean_art", "std_art", "ticks"]


# ── Station loader ────────────────────────────────────────────────────────────

def load_optimal_fleet(path: str = OPTIMAL_STATIONS) -> list[int]:
    """Load GA-optimised station node IDs from JSON.

    Supports both formats written by run_genetic_algorithm.py:
    - ``{"optimal_stations": ["id1", "id2", ...], ...}``  ← current format
    - ``[id1, id2, ...]``                                  ← bare list

    Returns
    -------
    list[int]
        Ordered list of node IDs.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    KeyError / ValueError
        If the JSON structure is unrecognised.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Optimal stations file not found: {path!r}\n"
            "Run 'python src/run_genetic_algorithm.py' (Sprint 3) first, "
            "or check that 'outputs/optimal_stations.json' exists."
        )
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    if isinstance(data, list):
        nodes = data
    elif isinstance(data, dict):
        # Try common key names written by the GA runner
        for key in ("optimal_stations", "stations", "nodes"):
            if key in data:
                nodes = data[key]
                break
        else:
            raise KeyError(
                f"Cannot find station list in {path!r}. "
                f"Expected key 'optimal_stations', 'stations', or 'nodes'. "
                f"Got keys: {list(data.keys())}"
            )
    else:
        raise ValueError(f"Unexpected JSON type in {path!r}: {type(data)}")

    return [int(n) for n in nodes]


# ── Seed parity assertion ─────────────────────────────────────────────────────

def verify_seed_parity(
    ai_cfg: dict,
    baseline_cfg_path: str = "headless_baseline.yaml",
) -> None:
    """Assert that AI and baseline configs share identical event seeds.

    Raises
    ------
    AssertionError
        If the event_seed, n_repeats, or ticks_per_run differ.
    """
    try:
        b_cfg = load_sim_config(path=baseline_cfg_path)
    except FileNotFoundError:
        logger.warning(
            "headless_baseline.yaml not found; skipping seed parity check."
        )
        return

    for key in ("event_seed", "n_repeats", "ticks_per_run"):
        ai_val  = ai_cfg.get(key)
        bas_val = b_cfg.get(key)
        assert str(ai_val) == str(bas_val), (
            f"Seed parity violation — key={key!r}: "
            f"AI config has {ai_val!r}, baseline has {bas_val!r}. "
            "Both configs must use identical seeds for a valid comparison."
        )
    logger.info("Seed parity check passed.")


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ResQ-Graph Sprint 9 AI Fleet Runner")
    p.add_argument("--headless", action="store_true")
    p.add_argument("--config",   default="headless_ai.yaml")
    p.add_argument("--ticks",    type=int,   default=None,
                   help="Override ticks_per_run from config.")
    p.add_argument("--seeds",    type=int,   nargs="+", default=None,
                   help="Explicit list of per-run seeds (overrides n_repeats).")
    return p.parse_args()


# ── Per-run metrics extraction (identical to run_baseline.py) ─────────────────

def _read_last_run_stats() -> tuple[float, float, int]:
    """Read ART stats from the last-written metrics_summary.csv."""
    summary_path = "outputs/metrics_summary.csv"
    if not os.path.isfile(summary_path):
        return 0.0, 0.0, 0
    try:
        with open(summary_path, "r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                return (
                    float(row.get("art",         0)),
                    float(row.get("std_dev",      0)),
                    int(row.get("total_events",   0)),
                )
    except (OSError, KeyError, ValueError):
        pass
    return 0.0, 0.0, 0


def _read_last_run_response_times() -> list[float]:
    """Read per-event response times from the last-written metrics_events.csv."""
    events_path = "outputs/metrics_events.csv"
    if not os.path.isfile(events_path):
        return []
    times: list[float] = []
    try:
        with open(events_path, "r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                rt_key = "response_time"
                if rt_key in row:
                    try:
                        val = row.get(rt_key)
                        if val is not None and val.strip() != "":
                            times.append(float(val))
                    except (ValueError, TypeError):
                        pass
    except OSError:
        pass
    return times


# ── CSV writers ───────────────────────────────────────────────────────────────

def _write_results_csv(rows: list[dict], summary: dict) -> None:
    os.makedirs(os.path.dirname(AI_CSV), exist_ok=True)
    with open(AI_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
        writer.writerow(summary)
    logger.info("AI results written -> %s", AI_CSV)


def _write_response_times_csv(all_rt: list[tuple[int, int, float]]) -> None:
    """Write a flat CSV of every response time with run_id and seed."""
    os.makedirs(os.path.dirname(AI_RT_CSV), exist_ok=True)
    with open(AI_RT_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["run_id", "seed", "response_time"])
        writer.writeheader()
        for run_id, seed, rt in all_rt:
            writer.writerow({"run_id": run_id, "seed": seed, "response_time": rt})
    logger.info("AI response times written -> %s", AI_RT_CSV)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = _parse_args()

    cfg = load_sim_config(path=args.config)

    setup_logging(level=cfg.get("LOG_LEVEL", "WARNING"),
                  log_file=cfg.get("LOG_FILE", "outputs/ai_fleet_sim.log"))

    # ── Verify seed parity before any run ─────────────────────────────────
    verify_seed_parity(cfg)

    ticks_per_run: int = args.ticks or int(cfg.get("ticks_per_run", 1000))
    n_repeats:     int = int(cfg.get("n_repeats", 10))
    base_seed:     int = int(cfg.get("random_seed", 42))
    event_seed:    int = int(cfg.get("event_seed", 100))

    # Build per-run seeds matching the baseline convention:
    # base_seed, base_seed+1, ..., base_seed+(n-1)
    if args.seeds:
        run_seeds = args.seeds
    else:
        run_seeds = [base_seed + i for i in range(n_repeats)]

    # ── Load optimal fleet (fixed across all runs) ─────────────────────────
    optimal_path = cfg.get("optimal_stations_path", OPTIMAL_STATIONS)
    station_nodes = load_optimal_fleet(optimal_path)
    logger.info("Loaded %d optimal stations from %s.", len(station_nodes), optimal_path)

    # ── Load graph once ────────────────────────────────────────────────────
    graph          = load_graph("data/model_town.graphml")
    node_positions = load_node_positions("data/node_positions.json")

    logger.info(
        "Starting AI fleet: %d runs x %d ticks (seeds: %s ... %s)",
        len(run_seeds), ticks_per_run, run_seeds[0], run_seeds[-1],
    )
    print(f"\n[AI Fleet] Starting {len(run_seeds)} headless runs x {ticks_per_run} ticks each ...")
    print(f"[AI Fleet] Stations (fixed): {station_nodes}\n")

    rows:   list[dict]               = []
    all_rt: list[tuple[int, int, float]] = []

    for run_id, seed in enumerate(run_seeds):
        # AI fleet uses the SAME station nodes every run (fixed, GA-optimised)
        # Event randomness is controlled by event_seed from YAML — same as
        # the baseline run at this index.
        run_cfg = dict(cfg)
        run_cfg["SIMULATION_TICKS"] = ticks_per_run
        run_cfg["TARGET_FPS"]       = 0           # headless
        run_cfg["event_seed"]       = seed        # reproducible events per run

        # Pass the fixed optimal station nodes
        run_simulation(cfg_override=run_cfg, initial_nodes=station_nodes)

        mean_art, std_art, n_events = _read_last_run_stats()
        run_times = _read_last_run_response_times()

        row = {
            "run_id":   run_id,
            "seed":     seed,
            "n_events": n_events,
            "mean_art": mean_art,
            "std_art":  std_art,
            "ticks":    ticks_per_run,
        }
        rows.append(row)
        all_rt.extend((run_id, seed, rt) for rt in run_times)

        print(f"  Run {run_id:>2d} | seed={seed} | events={n_events:>4d} | "
              f"ART={mean_art:>7.2f} +/- {std_art:.2f}")

    # ── Summary row ───────────────────────────────────────────────────────
    valid = [r for r in rows if r["n_events"] > 0]
    if valid:
        all_arts   = [r["mean_art"] for r in valid]
        grand_mean = round(sum(all_arts) / len(all_arts), 3)
        grand_std  = round(
            math.sqrt(sum((x - grand_mean) ** 2 for x in all_arts) / len(all_arts)), 3
        )
    else:
        grand_mean = grand_std = 0.0

    summary = {
        "run_id":   "SUMMARY",
        "seed":     "all",
        "n_events": sum(r["n_events"] for r in rows),
        "mean_art": grand_mean,
        "std_art":  grand_std,
        "ticks":    ticks_per_run * len(run_seeds),
    }

    _write_results_csv(rows, summary)
    _write_response_times_csv(all_rt)

    print(f"\n[AI Fleet] Done. Grand mean ART = {grand_mean} +/- {grand_std}")
    print(f"[AI Fleet] Results -> {AI_CSV}")
    print(f"[AI Fleet] Response times -> {AI_RT_CSV}\n")


if __name__ == "__main__":
    main()
