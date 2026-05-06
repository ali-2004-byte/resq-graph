"""
test_metrics_tracker.py – Sprint 5 (US-019)

Unit tests for MetricsTracker: ART computation, CSV buffer flush,
and get_hud_data() contract.
"""
import os
import csv
import pytest

from src.simulation.metrics_tracker import MetricsTracker
from src.simulation.ambulance import Ambulance, AmbulanceState


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def tracker(tmp_path):
    """MetricsTracker writing to a temp directory."""
    csv_path     = str(tmp_path / "events.csv")
    summary_path = str(tmp_path / "summary.csv")
    return MetricsTracker(
        csv_path      = csv_path,
        summary_path  = summary_path,
        flush_interval= 100,
    )


def _record(tracker, event_id, spawn, dispatch, arrival):
    tracker.record_response(
        event_id      = event_id,
        spawn_tick    = spawn,
        dispatch_tick = dispatch,
        arrival_tick  = arrival,
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestART:
    def test_art_zero_when_no_events(self, tracker):
        assert tracker.art == 0.0

    def test_art_correct_single_event(self, tracker):
        _record(tracker, 0, spawn=0, dispatch=2, arrival=10)
        # response_time = arrival - spawn = 10
        assert tracker.art == 10.0

    def test_art_correct_multiple_events(self, tracker):
        _record(tracker, 0, spawn=0,  dispatch=1, arrival=10)   # rt = 10
        _record(tracker, 1, spawn=5,  dispatch=7, arrival=15)   # rt = 10
        _record(tracker, 2, spawn=10, dispatch=12, arrival=16)  # rt = 6
        expected = (10 + 10 + 6) / 3
        assert abs(tracker.art - expected) < 1e-9

    def test_art_no_division_error_on_empty(self, tracker):
        assert tracker.art == 0.0   # must not raise ZeroDivisionError


class TestCSVFlush:
    def test_rows_written_equal_recorded_events(self, tracker):
        for i in range(3):
            _record(tracker, i, spawn=i, dispatch=i+1, arrival=i+5)
        tracker.flush_csv()

        with open(tracker.csv_path, newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 3

    def test_buffer_cleared_after_flush(self, tracker):
        _record(tracker, 0, spawn=0, dispatch=1, arrival=5)
        tracker.flush_csv()
        assert tracker._buffer == []

    def test_flush_with_empty_buffer_no_crash(self, tracker):
        tracker.flush_csv()  # must not raise

    def test_csv_header_written_once(self, tracker):
        for i in range(2):
            _record(tracker, i, spawn=i, dispatch=i+1, arrival=i+3)
        tracker.flush_csv()
        # Record more and flush again
        _record(tracker, 99, spawn=0, dispatch=1, arrival=4)
        tracker.flush_csv()

        with open(tracker.csv_path, newline="") as f:
            lines = f.readlines()
        headers = [l for l in lines if l.startswith("event_id")]
        assert len(headers) == 1  # header written only once


class TestSummaryCSV:
    def test_summary_csv_written_on_export(self, tracker):
        _record(tracker, 0, spawn=0, dispatch=2, arrival=8)
        tracker.flush_csv()
        tracker.export_summary_csv()
        assert os.path.isfile(tracker.summary_path)

    def test_summary_csv_no_crash_when_empty(self, tracker):
        tracker.export_summary_csv()  # must not raise


class TestHUDData:
    def test_get_hud_data_returns_all_keys(self, tracker):
        _record(tracker, 0, spawn=0, dispatch=1, arrival=5)
        data = tracker.get_hud_data()
        required = {"art", "total_events", "latest_rt", "min_rt", "max_rt",
                    "std_dev", "last_five", "tick_history"}
        assert required.issubset(data.keys())

    def test_get_hud_data_no_keyerror_when_empty(self, tracker):
        data = tracker.get_hud_data()  # must not raise
        assert data["art"] == 0.0
        assert data["total_events"] == 0

    def test_latest_rt_matches_last_recorded(self, tracker):
        _record(tracker, 0, spawn=0, dispatch=1, arrival=5)   # rt = 5
        _record(tracker, 1, spawn=0, dispatch=1, arrival=9)   # rt = 9
        assert tracker.get_hud_data()["latest_rt"] == 9


class TestSnapshot:
    def test_snapshot_appends_to_history(self, tracker):
        import networkx as nx
        G = nx.Graph()
        G.add_node(1, x=0.0, y=0.0)
        amb = Ambulance(id=0, start_node=1, graph=G)
        tracker.snapshot(current_tick=10, active_events=[], ambulances=[amb])
        assert len(tracker._tick_history) == 1
        entry = tracker._tick_history[0]
        assert entry["tick"] == 10
        assert "art" in entry
        assert "utilisation" in entry
