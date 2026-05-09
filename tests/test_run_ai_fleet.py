"""
tests/test_run_ai_fleet.py – Sprint 9 (US-033)

Unit tests for src/run_ai_fleet.py.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.run_ai_fleet import load_optimal_fleet, verify_seed_parity


# ── load_optimal_fleet tests ──────────────────────────────────────────────────

def test_load_optimal_fleet_dict_format(tmp_path):
    """Load from the standard GA output format {optimal_stations: [...]}."""
    data = {"optimal_stations": ["11", "22", "33", "44", "55"], "best_fitness": 1.0}
    p = tmp_path / "stations.json"
    p.write_text(json.dumps(data))
    result = load_optimal_fleet(str(p))
    assert result == [11, 22, 33, 44, 55]


def test_load_optimal_fleet_list_format(tmp_path):
    """Load from a bare list format."""
    p = tmp_path / "stations.json"
    p.write_text(json.dumps([100, 200, 300]))
    result = load_optimal_fleet(str(p))
    assert result == [100, 200, 300]


def test_load_optimal_fleet_missing_file():
    """FileNotFoundError raised when file absent."""
    with pytest.raises(FileNotFoundError):
        load_optimal_fleet("/nonexistent/path/stations.json")


def test_load_optimal_fleet_bad_key(tmp_path):
    """KeyError raised when dict has no recognised station key."""
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"foo": [1, 2, 3]}))
    with pytest.raises(KeyError):
        load_optimal_fleet(str(p))


# ── verify_seed_parity tests ──────────────────────────────────────────────────

def test_verify_seed_parity_passes(tmp_path):
    """No exception raised when seeds match."""
    baseline = tmp_path / "baseline.yaml"
    baseline.write_text(
        "event_seed: 100\nn_repeats: 10\nticks_per_run: 1000\n"
    )
    cfg = {"event_seed": 100, "n_repeats": 10, "ticks_per_run": 1000}
    # Should not raise
    verify_seed_parity(cfg, baseline_cfg_path=str(baseline))


def test_verify_seed_parity_mismatch_raises(tmp_path):
    """AssertionError raised on seed mismatch."""
    baseline = tmp_path / "baseline.yaml"
    baseline.write_text("event_seed: 999\nn_repeats: 10\nticks_per_run: 1000\n")
    cfg = {"event_seed": 100, "n_repeats": 10, "ticks_per_run": 1000}
    with pytest.raises(AssertionError):
        verify_seed_parity(cfg, baseline_cfg_path=str(baseline))


def test_verify_seed_parity_missing_baseline_no_error(tmp_path):
    """No exception raised when baseline YAML not found (graceful skip)."""
    cfg = {"event_seed": 100, "n_repeats": 10, "ticks_per_run": 1000}
    # Should NOT raise even though file is missing
    verify_seed_parity(cfg, baseline_cfg_path=str(tmp_path / "missing.yaml"))
