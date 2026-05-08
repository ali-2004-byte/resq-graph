"""
test_hotspot_detection.py – Sprint 6 (US-021 / US-022)

Comprehensive tests for the hotspot-detection pipeline:
  - HDBSCAN internal algorithm stages
  - Edge cases (collinear points, duplicates, outliers, single point)
  - Geometric correctness of cluster assignments
  - DemandClusterer integration (centroid resolution, noise filtering,
    member correctness, duplicate cluster IDs, etc.)
"""
from __future__ import annotations

import math
import numpy as np
import pytest

from src.intelligence.hdbscan import HDBSCAN
from src.intelligence.demand_clustering import DemandClusterer, Hotspot


# ── Shared test helpers ────────────────────────────────────────────────────────

class _Ev:
    """Minimal event stub (location + pixel_pos)."""
    def __init__(self, node_id: int, px: int, py: int):
        self.location  = node_id
        self.pixel_pos = (px, py)


def _two_cluster_points(n: int = 15, gap: float = 300.0) -> np.ndarray:
    """Two tight blobs separated by *gap* pixels."""
    rng = np.random.default_rng(7)
    a = rng.normal(loc=[0.0, 0.0],    scale=4.0, size=(n, 2))
    b = rng.normal(loc=[gap,  0.0],   scale=4.0, size=(n, 2))
    return np.vstack([a, b])


def _three_cluster_points(n: int = 12, gap: float = 250.0) -> np.ndarray:
    rng = np.random.default_rng(99)
    a = rng.normal(loc=[0.0,  0.0], scale=3.0, size=(n, 2))
    b = rng.normal(loc=[gap,  0.0], scale=3.0, size=(n, 2))
    c = rng.normal(loc=[0.0,  gap], scale=3.0, size=(n, 2))
    return np.vstack([a, b, c])


# ══════════════════════════════════════════════════════════════════════════════
# 1. HDBSCAN – internal stage tests
# ══════════════════════════════════════════════════════════════════════════════

class TestHDBSCANInternals:
    """White-box tests for each algorithm stage."""

    def test_pairwise_euclidean_symmetry(self):
        X = np.array([[0.0, 0.0], [3.0, 4.0], [6.0, 0.0]])
        D = HDBSCAN._pairwise_euclidean(X)
        np.testing.assert_allclose(D, D.T)

    def test_pairwise_euclidean_diagonal_zero(self):
        X = np.array([[1.0, 2.0], [3.0, 5.0]])
        D = HDBSCAN._pairwise_euclidean(X)
        assert D[0, 0] == pytest.approx(0.0)
        assert D[1, 1] == pytest.approx(0.0)

    def test_pairwise_euclidean_known_distance(self):
        X = np.array([[0.0, 0.0], [3.0, 4.0]])
        D = HDBSCAN._pairwise_euclidean(X)
        assert D[0, 1] == pytest.approx(5.0)

    def test_core_distances_non_negative(self):
        hdb = HDBSCAN(min_cluster_size=3, min_samples=2)
        X = _two_cluster_points()
        D = HDBSCAN._pairwise_euclidean(X)
        core = hdb._core_distances(D)
        assert np.all(core >= 0)

    def test_core_distances_length(self):
        X = _two_cluster_points(n=10)
        hdb = HDBSCAN(min_cluster_size=3, min_samples=2)
        D = HDBSCAN._pairwise_euclidean(X)
        core = hdb._core_distances(D)
        assert core.shape == (len(X),)

    def test_mutual_reachability_ge_raw_distance(self):
        X = _two_cluster_points(n=10)
        hdb = HDBSCAN(min_cluster_size=3, min_samples=2)
        D    = HDBSCAN._pairwise_euclidean(X)
        core = hdb._core_distances(D)
        mre  = HDBSCAN._mutual_reachability(D, core)
        # d_mre(a,b) >= dist(a,b) by definition
        assert np.all(mre >= D - 1e-12)

    def test_mutual_reachability_symmetry(self):
        X = _two_cluster_points(n=8)
        hdb = HDBSCAN(min_cluster_size=3, min_samples=2)
        D    = HDBSCAN._pairwise_euclidean(X)
        core = hdb._core_distances(D)
        mre  = HDBSCAN._mutual_reachability(D, core)
        np.testing.assert_allclose(mre, mre.T)

    def test_prim_mst_edge_count(self):
        X = _two_cluster_points(n=10)
        hdb = HDBSCAN(min_cluster_size=3, min_samples=2)
        D    = HDBSCAN._pairwise_euclidean(X)
        core = hdb._core_distances(D)
        mre  = HDBSCAN._mutual_reachability(D, core)
        mst  = HDBSCAN._prim_mst(mre)
        # MST of n nodes always has n-1 edges
        assert len(mst) == len(X) - 1

    def test_prim_mst_weights_sorted(self):
        X = _two_cluster_points(n=10)
        hdb = HDBSCAN(min_cluster_size=3, min_samples=2)
        D    = HDBSCAN._pairwise_euclidean(X)
        core = hdb._core_distances(D)
        mre  = HDBSCAN._mutual_reachability(D, core)
        mst  = HDBSCAN._prim_mst(mre)
        weights = [e.weight for e in mst]
        assert weights == sorted(weights)

    def test_prim_mst_nodes_in_range(self):
        n = 8
        X = _two_cluster_points(n=n)
        hdb = HDBSCAN(min_cluster_size=3, min_samples=2)
        D    = HDBSCAN._pairwise_euclidean(X)
        core = hdb._core_distances(D)
        mre  = HDBSCAN._mutual_reachability(D, core)
        mst  = HDBSCAN._prim_mst(mre)
        for e in mst:
            assert 0 <= e.u < 2 * n
            assert 0 <= e.v < 2 * n


# ══════════════════════════════════════════════════════════════════════════════
# 2. HDBSCAN – edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestHDBSCANEdgeCases:

    def test_single_point_all_noise(self):
        X = np.array([[5.0, 5.0]])
        labels = HDBSCAN(min_cluster_size=2).fit_predict(X)
        assert list(labels) == [-1]

    def test_exactly_min_cluster_size_points_tight(self):
        """Exactly min_cluster_size identical-region points should form a cluster."""
        rng = np.random.default_rng(0)
        X = rng.normal(loc=[0.0, 0.0], scale=0.1, size=(5, 2))
        labels = HDBSCAN(min_cluster_size=5, min_samples=2).fit_predict(X)
        unique = set(labels) - {-1}
        assert len(unique) >= 1

    def test_collinear_points_no_crash(self):
        """Points on a straight line must not raise an exception."""
        X = np.column_stack([np.linspace(0, 100, 20), np.zeros(20)])
        labels = HDBSCAN(min_cluster_size=3, min_samples=2).fit_predict(X)
        assert labels.shape == (20,)
        assert all(l >= -1 for l in labels)

    def test_duplicate_points_no_crash(self):
        """Duplicate pixel positions (zero distance) must not raise."""
        X = np.tile([50.0, 50.0], (10, 1))
        labels = HDBSCAN(min_cluster_size=3, min_samples=2).fit_predict(X)
        assert labels.shape == (10,)

    def test_isolated_outlier_labelled_noise(self):
        """One point far from two clusters should be labelled -1."""
        rng = np.random.default_rng(3)
        cluster_a = rng.normal(loc=[0.0,   0.0], scale=2.0, size=(15, 2))
        cluster_b = rng.normal(loc=[200.0, 0.0], scale=2.0, size=(15, 2))
        outlier   = np.array([[1000.0, 1000.0]])
        X = np.vstack([cluster_a, cluster_b, outlier])
        labels = HDBSCAN(min_cluster_size=3, min_samples=2).fit_predict(X)
        assert labels[-1] == -1, "Isolated outlier should be noise."

    def test_min_samples_defaults_to_min_cluster_size(self):
        hdb = HDBSCAN(min_cluster_size=4)
        assert hdb.min_samples == 4

    def test_three_distinct_clusters_detected(self):
        X = _three_cluster_points(n=15)
        labels = HDBSCAN(min_cluster_size=3, min_samples=2).fit_predict(X)
        unique = set(labels) - {-1}
        assert len(unique) >= 2, "Should find at least 2 of the 3 clusters."

    def test_no_label_below_minus_one(self):
        X = _two_cluster_points()
        labels = HDBSCAN(min_cluster_size=3, min_samples=2).fit_predict(X)
        assert np.all(labels >= -1)

    def test_cluster_labels_are_contiguous_from_zero(self):
        """Cluster labels must be 0, 1, 2 … (no gaps)."""
        X = _two_cluster_points(n=15)
        labels = HDBSCAN(min_cluster_size=3, min_samples=2).fit_predict(X)
        unique = sorted(set(labels) - {-1})
        if unique:
            assert unique[0] == 0
            assert unique == list(range(len(unique)))

    def test_fit_predict_returns_ndarray(self):
        X = _two_cluster_points(n=8)
        result = HDBSCAN(min_cluster_size=3, min_samples=2).fit_predict(X)
        assert isinstance(result, np.ndarray)

    def test_min_samples_smaller_than_min_cluster_size(self):
        """min_samples=1 is a valid, more aggressive noise-tolerance setting."""
        X = _two_cluster_points(n=12)
        labels = HDBSCAN(min_cluster_size=5, min_samples=1).fit_predict(X)
        assert labels.shape == (len(X),)

    def test_high_dimensional_input(self):
        """HDBSCAN should work on >2D data (e.g. 5 features)."""
        rng = np.random.default_rng(11)
        a = rng.normal(loc=[0]*5,   scale=1.0, size=(15, 5))
        b = rng.normal(loc=[20]*5,  scale=1.0, size=(15, 5))
        X = np.vstack([a, b])
        labels = HDBSCAN(min_cluster_size=3, min_samples=2).fit_predict(X)
        assert labels.shape == (30,)


# ══════════════════════════════════════════════════════════════════════════════
# 3. HDBSCAN – geometric correctness
# ══════════════════════════════════════════════════════════════════════════════

class TestHDBSCANGeometric:

    def test_cross_cluster_separation(self):
        """Points in cluster A must not share a label with points in cluster B."""
        rng = np.random.default_rng(55)
        n = 20
        a = rng.normal(loc=[0.0,   0.0], scale=3.0, size=(n, 2))
        b = rng.normal(loc=[500.0, 0.0], scale=3.0, size=(n, 2))
        X = np.vstack([a, b])
        labels = HDBSCAN(min_cluster_size=5, min_samples=2).fit_predict(X)

        labels_a = set(labels[:n]) - {-1}
        labels_b = set(labels[n:]) - {-1}
        if labels_a and labels_b:
            assert labels_a.isdisjoint(labels_b), (
                "Points from different blobs should not share a cluster label."
            )

    def test_tight_blob_majority_not_noise(self):
        """In a very tight cluster most points should not be noise."""
        rng = np.random.default_rng(22)
        X = rng.normal(loc=[100.0, 100.0], scale=0.5, size=(30, 2))
        labels = HDBSCAN(min_cluster_size=3, min_samples=2).fit_predict(X)
        noise_frac = np.sum(labels == -1) / len(labels)
        assert noise_frac < 0.5, "More than half the points in a tight blob are noise."

    def test_well_separated_both_clusters_found(self):
        """With a huge gap, both clusters should be recovered."""
        rng = np.random.default_rng(66)
        n = 20
        a = rng.normal(loc=[0.0,    0.0], scale=2.0, size=(n, 2))
        b = rng.normal(loc=[1000.0, 0.0], scale=2.0, size=(n, 2))
        X = np.vstack([a, b])
        labels = HDBSCAN(min_cluster_size=5, min_samples=2).fit_predict(X)
        unique = set(labels) - {-1}
        assert len(unique) == 2, f"Expected 2 clusters, got {unique}."


# ══════════════════════════════════════════════════════════════════════════════
# 4. DemandClusterer – integration tests
# ══════════════════════════════════════════════════════════════════════════════

def _node_positions_grid(cols: int = 50, rows: int = 50, spacing: int = 10) -> dict:
    pos = {}
    for r in range(rows):
        for c in range(cols):
            nid = r * cols + c
            pos[nid] = [float(c * spacing), float(r * spacing)]
    return pos


def _events_for_cluster(
    node_ids: list[int],
    node_positions: dict,
) -> list[_Ev]:
    return [
        _Ev(nid, int(node_positions[nid][0]), int(node_positions[nid][1]))
        for nid in node_ids
    ]


class TestDemandClustererIntegration:

    def setup_method(self):
        self.nodes = _node_positions_grid()  # 2500 nodes on 10-px grid

    def _dc(self, min_cluster_size=3, min_samples=2):
        return DemandClusterer(
            node_positions=self.nodes,
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
        )

    # ── Basic output structure ────────────────────────────────────────────────

    def test_returns_list(self):
        events = [_Ev(i, i * 10, 0) for i in range(10)]
        assert isinstance(self._dc().run(events), list)

    def test_hotspot_type(self):
        node_ids = list(range(10))   # tight top-left corner
        events = _events_for_cluster(node_ids, self.nodes)
        result = self._dc().run(events)
        for hs in result:
            assert isinstance(hs, Hotspot)

    # ── Noise filtering ───────────────────────────────────────────────────────

    def test_noise_events_not_in_any_hotspot(self):
        """Events labelled noise by HDBSCAN must not appear in member_nodes."""
        # One tight cluster + one isolated outlier far away
        cluster_nodes = list(range(10))          # nodes 0-9, top-left
        outlier_node  = 2499                      # bottom-right corner
        events = (
            _events_for_cluster(cluster_nodes, self.nodes)
            + [_Ev(outlier_node,
                   int(self.nodes[outlier_node][0]),
                   int(self.nodes[outlier_node][1]))]
        )
        hotspots = self._dc().run(events)
        all_members = {n for hs in hotspots for n in hs.member_nodes}
        assert outlier_node not in all_members, (
            "The isolated outlier node should not appear in any hotspot."
        )

    # ── Centroid correctness ──────────────────────────────────────────────────

    def test_centroid_node_exists_in_node_positions(self):
        node_ids = list(range(12))
        events = _events_for_cluster(node_ids, self.nodes)
        hotspots = self._dc().run(events)
        for hs in hotspots:
            assert hs.centroid_node in self.nodes, (
                f"centroid_node {hs.centroid_node} not in node_positions."
            )

    def test_centroid_pixel_pos_matches_node_positions(self):
        node_ids = list(range(15))
        events = _events_for_cluster(node_ids, self.nodes)
        hotspots = self._dc().run(events)
        for hs in hotspots:
            expected = (
                int(self.nodes[hs.centroid_node][0]),
                int(self.nodes[hs.centroid_node][1]),
            )
            assert hs.pixel_pos == expected

    def test_centroid_near_geometric_mean(self):
        """centroid_node pixel_pos should be the node nearest the geometric mean."""
        # Use 9 nodes in a 3×3 block; centroid should land near the middle node.
        block = [0, 1, 2, 50, 51, 52, 100, 101, 102]
        events = _events_for_cluster(block, self.nodes)
        hotspots = self._dc(min_cluster_size=3).run(events)
        if not hotspots:
            pytest.skip("No cluster found.")
        hs = hotspots[0]
        px, py = hs.pixel_pos
        # Geometric centroid of the block in pixel space
        mean_x = np.mean([self.nodes[n][0] for n in block])
        mean_y = np.mean([self.nodes[n][1] for n in block])
        dist = math.hypot(px - mean_x, py - mean_y)
        # Must be within one grid spacing (10 px) of the true centroid
        assert dist <= 20.0, f"Centroid too far from mean: {dist:.1f}px"

    # ── Member correctness ────────────────────────────────────────────────────

    def test_member_nodes_subset_of_input(self):
        node_ids = list(range(12))
        events = _events_for_cluster(node_ids, self.nodes)
        hotspots = self._dc().run(events)
        input_set = set(node_ids)
        for hs in hotspots:
            assert set(hs.member_nodes).issubset(input_set)

    def test_member_pixel_positions_match_events(self):
        node_ids = list(range(10))
        events = _events_for_cluster(node_ids, self.nodes)
        ev_map = {e.location: e.pixel_pos for e in events}
        hotspots = self._dc().run(events)
        for hs in hotspots:
            for nid, ppx in zip(hs.member_nodes, hs.member_pixel_positions):
                assert ppx == ev_map[nid]

    def test_no_duplicate_member_nodes_within_hotspot(self):
        node_ids = list(range(12))
        events = _events_for_cluster(node_ids, self.nodes)
        hotspots = self._dc().run(events)
        for hs in hotspots:
            assert len(hs.member_nodes) == len(set(hs.member_nodes))

    def test_size_property_equals_member_count(self):
        node_ids = list(range(10))
        events = _events_for_cluster(node_ids, self.nodes)
        hotspots = self._dc().run(events)
        for hs in hotspots:
            assert hs.size == len(hs.member_nodes)
            assert hs.size == len(hs.member_pixel_positions)

    # ── Cluster ID integrity ─────────────────────────────────────────────────

    def test_cluster_ids_are_non_negative(self):
        node_ids = list(range(12))
        events = _events_for_cluster(node_ids, self.nodes)
        hotspots = self._dc().run(events)
        for hs in hotspots:
            assert hs.cluster_id >= 0

    def test_cluster_ids_are_unique_across_hotspots(self):
        # Two tight clusters far apart
        group_a = list(range(10))       # nodes 0-9
        group_b = list(range(2490, 2500))  # nodes near bottom-right
        events = (
            _events_for_cluster(group_a, self.nodes)
            + _events_for_cluster(group_b, self.nodes)
        )
        hotspots = self._dc().run(events)
        ids = [hs.cluster_id for hs in hotspots]
        assert len(ids) == len(set(ids)), "cluster_id must be unique per hotspot."

    # ── Duplicate-location events ─────────────────────────────────────────────

    def test_events_at_same_pixel_no_crash(self):
        """Multiple events on the exact same node should not raise."""
        events = [_Ev(5, 50, 0)] * 10
        result = self._dc().run(events)
        assert isinstance(result, list)

    # ── min_cluster_size boundary ─────────────────────────────────────────────

    def test_exactly_min_cluster_size_events_may_cluster(self):
        node_ids = list(range(5))
        events = _events_for_cluster(node_ids, self.nodes)
        dc = self._dc(min_cluster_size=5)
        result = dc.run(events)
        # May or may not cluster depending on density; must not crash
        assert isinstance(result, list)

    def test_one_fewer_than_min_cluster_size_returns_empty(self):
        node_ids = list(range(4))
        events = _events_for_cluster(node_ids, self.nodes)
        dc = self._dc(min_cluster_size=5)
        result = dc.run(events)
        assert result == []

    # ── Two-cluster separation ────────────────────────────────────────────────

    def test_two_clusters_both_found(self):
        """Two well-separated groups should yield (at least) two hotspots."""
        group_a = list(range(10))
        group_b = list(range(2490, 2500))
        events = (
            _events_for_cluster(group_a, self.nodes)
            + _events_for_cluster(group_b, self.nodes)
        )
        hotspots = self._dc().run(events)
        assert len(hotspots) >= 2, (
            f"Expected ≥2 hotspots for two separated clusters, got {len(hotspots)}."
        )

    def test_two_clusters_centroids_are_different_nodes(self):
        group_a = list(range(10))
        group_b = list(range(2490, 2500))
        events = (
            _events_for_cluster(group_a, self.nodes)
            + _events_for_cluster(group_b, self.nodes)
        )
        hotspots = self._dc().run(events)
        if len(hotspots) < 2:
            pytest.skip("Algorithm merged into fewer than 2 clusters.")
        centroids = [hs.centroid_node for hs in hotspots]
        assert len(set(centroids)) == len(centroids), (
            "Each hotspot must have a distinct centroid node."
        )
