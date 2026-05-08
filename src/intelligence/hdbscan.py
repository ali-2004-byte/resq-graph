"""
hdbscan.py – Sprint 6 (US-021)

Manual implementation of the HDBSCAN algorithm from scratch.

Algorithm stages
----------------
1. Core distances      – distance to the k-th nearest neighbour
                         (k = min_samples).
2. Mutual reachability – d_mre(a, b) = max(core_a, core_b, dist(a, b)).
3. MST                 – Prim's algorithm over the mutual-reachability graph.
4. Condensed tree      – collapse the MST dendrogram into a tree of stable
                         clusters using min_cluster_size.
5. Stability           – select flat clusters by maximising "Excess of Mass".

Public API
----------
    from src.intelligence.hdbscan import HDBSCAN

    labels = HDBSCAN(min_cluster_size=3, min_samples=2).fit_predict(points)
    # labels[i] == -1  →  noise point
    # labels[i] >= 0   →  cluster membership

Implementation philosophy
--------------------------
Written to the same standard expected of a professional library API
(clear docstrings, typed signatures, no premature micro-optimisation).
Uses only numpy and the Python standard library – no scikit-learn.

References
----------
- Campello et al. (2013) "Density-Based Clustering Based on Hierarchical
  Density Estimates", ECML PKDD.
- McInnes et al. (2017) "Accelerated Hierarchical Density Based Clustering",
  ICDM Workshop.
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Iterator

import numpy as np


# ── Internal data structures ──────────────────────────────────────────────────

@dataclass
class _MSTEdge:
    """One edge in the minimum spanning tree."""
    u: int
    v: int
    weight: float

    def __lt__(self, other: "_MSTEdge") -> bool:
        return self.weight < other.weight


@dataclass
class _ClusterNode:
    """Node in the condensed cluster tree."""
    node_id:    int
    parent_id:  int | None
    birth_level: float          # 1/distance at which cluster was born
    death_level: float | None   # 1/distance at which cluster split/died
    size:        int            # number of original points in subtree
    children:    list[int] = field(default_factory=list)
    point_ids:   list[int] = field(default_factory=list)


# ── Main class ────────────────────────────────────────────────────────────────

class HDBSCAN:
    """Hierarchical Density-Based Spatial Clustering of Applications with Noise.

    Parameters
    ----------
    min_cluster_size : int
        Minimum number of points for a group to be considered a cluster.
        Larger values produce fewer, broader clusters.
    min_samples : int
        Number of neighbours used to define the core distance of a point.
        Smaller values make the algorithm more tolerant of noise.

    Attributes (set after fit)
    --------------------------
    labels_ : np.ndarray, shape (n_samples,)
        Integer cluster labels.  Noise points are labelled ``-1``.
    """

    def __init__(
        self,
        min_cluster_size: int = 5,
        min_samples:      int | None = None,
    ) -> None:
        if min_cluster_size < 2:
            raise ValueError("min_cluster_size must be ≥ 2.")
        self.min_cluster_size = min_cluster_size
        self.min_samples      = min_samples if min_samples is not None else min_cluster_size
        self.labels_: np.ndarray | None = None

    # ── Public ────────────────────────────────────────────────────────────────

    def fit_predict(self, X: np.ndarray) -> np.ndarray:
        """Run HDBSCAN on *X* and return cluster labels.

        Parameters
        ----------
        X : np.ndarray, shape (n_samples, n_features)
            Input point cloud (e.g. pixel coordinates).

        Returns
        -------
        labels : np.ndarray, shape (n_samples,)
            Cluster label per point.  ``-1`` denotes noise.
        """
        n = len(X)
        if n < self.min_cluster_size:
            self.labels_ = np.full(n, -1, dtype=int)
            return self.labels_

        # Stage 1 & 2 – core distances + mutual reachability matrix
        dist_matrix = self._pairwise_euclidean(X)
        core_dists  = self._core_distances(dist_matrix)
        mreach      = self._mutual_reachability(dist_matrix, core_dists)

        # Stage 3 – minimum spanning tree via Prim's
        mst = self._prim_mst(mreach)

        # Stage 4 – condense the MST dendrogram
        cluster_tree, root_id = self._build_condensed_tree(mst, n)

        # Stage 5 – extract flat clusters by Excess-of-Mass
        selected = self._extract_clusters(cluster_tree, root_id)
        self.labels_ = self._assign_labels(n, cluster_tree, selected)
        return self.labels_

    # ── Stage 1: pairwise Euclidean distances ─────────────────────────────────

    @staticmethod
    def _pairwise_euclidean(X: np.ndarray) -> np.ndarray:
        """Return the full symmetric distance matrix (n × n)."""
        # Using broadcasting: avoids an explicit loop.
        diff = X[:, np.newaxis, :] - X[np.newaxis, :, :]   # (n, n, d)
        return np.sqrt((diff ** 2).sum(axis=-1))            # (n, n)

    # ── Stage 1: core distances ───────────────────────────────────────────────

    def _core_distances(self, dist_matrix: np.ndarray) -> np.ndarray:
        """Distance from each point to its min_samples-th nearest neighbour.

        The diagonal is ``inf`` so self-distance is never the minimum.
        """
        n = dist_matrix.shape[0]
        k = min(self.min_samples, n - 1)   # clamp to avoid index error

        # Partition to find k-th smallest per row (fast, O(n·k) expected)
        core = np.empty(n, dtype=float)
        for i in range(n):
            row = dist_matrix[i].copy()
            row[i] = np.inf                # exclude self
            core[i] = np.partition(row, k - 1)[k - 1]
        return core

    # ── Stage 2: mutual reachability ──────────────────────────────────────────

    @staticmethod
    def _mutual_reachability(
        dist_matrix: np.ndarray,
        core_dists:  np.ndarray,
    ) -> np.ndarray:
        """d_mre(a, b) = max(core_a, core_b, dist(a, b)).

        Broadcasting ensures this is O(n²) in memory and time.
        """
        core_a = core_dists[:, np.newaxis]   # column vector (n, 1)
        core_b = core_dists[np.newaxis, :]   # row vector    (1, n)
        return np.maximum(dist_matrix, np.maximum(core_a, core_b))

    # ── Stage 3: Prim's MST over mutual-reachability graph ───────────────────

    @staticmethod
    def _prim_mst(weight_matrix: np.ndarray) -> list[_MSTEdge]:
        """Prim's algorithm on the dense mutual-reachability matrix.

        Returns
        -------
        edges : list[_MSTEdge]
            ``n - 1`` edges forming the MST, sorted by ascending weight.
        """
        n = weight_matrix.shape[0]
        in_tree   = np.zeros(n, dtype=bool)
        min_cost  = np.full(n, np.inf)
        nearest   = np.full(n, -1, dtype=int)

        # Seed with node 0
        min_cost[0] = 0.0
        heap: list[tuple[float, int]] = [(0.0, 0)]
        edges: list[_MSTEdge] = []

        while heap:
            cost, u = heapq.heappop(heap)
            if in_tree[u]:
                continue
            in_tree[u] = True
            if nearest[u] != -1:
                edges.append(_MSTEdge(u=nearest[u], v=u, weight=cost))

            # Relax neighbours
            row = weight_matrix[u]
            mask = ~in_tree
            improve = mask & (row < min_cost)
            min_cost[improve] = row[improve]
            nearest[improve]  = u
            for v in np.where(improve)[0]:
                heapq.heappush(heap, (float(min_cost[v]), int(v)))

        edges.sort()
        return edges

    # ── Stage 4: condense the dendrogram ─────────────────────────────────────

    def _build_condensed_tree(
        self,
        mst: list[_MSTEdge],
        n_points: int,
    ) -> tuple[dict[int, _ClusterNode], int]:
        """Convert MST into a condensed cluster tree.

        The MST edges are sorted by ascending weight.  Merging them in order
        simulates the single-linkage hierarchy; we track components with a
        Union-Find structure and condense whenever a merge would keep at least
        ``min_cluster_size`` points in each sub-component.

        Returns
        -------
        tree : dict[int, _ClusterNode]
        root_id : int
        """
        # Union-Find
        parent    = list(range(n_points))
        rank      = [0] * n_points
        comp_size = [1] * n_points

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: int, y: int) -> int:
            rx, ry = find(x), find(y)
            if rx == ry:
                return rx
            if rank[rx] < rank[ry]:
                rx, ry = ry, rx
            parent[ry] = rx
            comp_size[rx] += comp_size[ry]
            if rank[rx] == rank[ry]:
                rank[rx] += 1
            return rx

        # Internal-node IDs start at n_points
        next_id = [n_points]
        tree: dict[int, _ClusterNode] = {}

        # Leaf nodes for each original point
        for i in range(n_points):
            tree[i] = _ClusterNode(
                node_id=i,
                parent_id=None,
                birth_level=0.0,
                death_level=None,
                size=1,
                point_ids=[i],
            )

        # BUG FIX: map each UF root → the current tree node that represents
        # that component.  Without this, re-merging a UF root overwrites its
        # parent_id/death_level in the tree, corrupting the condensed tree.
        uf_to_node: dict[int, int] = {i: i for i in range(n_points)}

        # Process edges in ascending weight order (→ increasing λ = 1/w)
        for edge in mst:
            w   = max(edge.weight, 1e-12)   # guard against zero-weight edges
            lam = 1.0 / w
            rc  = find(edge.u)
            rd  = find(edge.v)

            if rc == rd:
                continue   # already connected

            size_c = comp_size[rc]
            size_d = comp_size[rd]

            # Resolve to the correct tree nodes BEFORE the union mutates roots
            node_c = uf_to_node[rc]
            node_d = uf_to_node[rd]

            new_root = union(rc, rd)
            nid      = next_id[0]
            next_id[0] += 1

            # Create internal node
            tree[nid] = _ClusterNode(
                node_id=nid,
                parent_id=None,
                birth_level=lam,
                death_level=None,
                size=size_c + size_d,
                children=[node_c, node_d],
            )
            # Wire children to this new parent
            tree[node_c].parent_id   = nid
            tree[node_c].death_level = lam
            tree[node_d].parent_id   = nid
            tree[node_d].death_level = lam

            # Condense small components into noise
            for child_nid in (node_c, node_d):
                if tree[child_nid].size < self.min_cluster_size:
                    tree[child_nid].death_level = lam

            # The new UF root now maps to the freshly-created internal node
            uf_to_node[new_root] = nid

        # The last merged node is the root
        root_id = next_id[0] - 1
        return tree, root_id

    # ── Stage 5: Excess-of-Mass cluster extraction ────────────────────────────

    def _extract_clusters(
        self,
        tree: dict[int, _ClusterNode],
        root_id: int,
    ) -> set[int]:
        """Select flat clusters maximising Excess-of-Mass stability.

        Returns
        -------
        selected : set[int]
            Node IDs of the chosen clusters.
        """
        # BUG FIX: stability[nid] must store the node's OWN Excess-of-Mass
        # contribution, not max(own, children_sum).  The old code stored the
        # max, so s_node always equalled s_children at the root, preventing
        # the algorithm from ever descending into sub-clusters.
        stability: dict[int, float] = {}

        def _own_stability(nid: int) -> float:
            """Excess of Mass for this node: (λ_birth − λ_death) × size.

            In the bottom-up condensed tree:
              birth_level = λ at which this node was *created* (tight, high λ)
              death_level = λ at which it was absorbed into its parent (loose, low λ)
            so birth_level > death_level and stability = (birth − death) × size.
            The root has no parent → death_level is None → stability = 0,
            which guarantees the root is never selected over its children.
            """
            node = tree.get(nid)
            if node is None or node.death_level is None:
                return 0.0
            return max(0.0, node.birth_level - node.death_level) * node.size

        def _compute_stability(nid: int) -> float:
            """Recursively compute and cache own stability; return subtree max."""
            node = tree.get(nid)
            if node is None:
                return 0.0
            own = _own_stability(nid)
            stability[nid] = own          # store OWN value for the selector
            if not node.children:
                return own
            children_sum = sum(_compute_stability(c) for c in node.children)
            # Return the running subtree maximum (used only during recursion)
            return max(own, children_sum)

        _compute_stability(root_id)

        # Greedy selection: if the sum of children's own stabilities exceeds
        # this node's own stability, descend; otherwise select this node.
        selected: set[int] = set()

        def _select(nid: int) -> None:
            node = tree.get(nid)
            if node is None or not node.children:
                if node and node.size >= self.min_cluster_size:
                    selected.add(nid)
                return

            # Only descend if at least one child can itself form a valid cluster;
            # otherwise the parent is the finest selectable cluster.
            viable = [
                c for c in node.children
                if tree.get(c) and tree[c].size >= self.min_cluster_size
            ]
            s_node     = stability.get(nid, 0.0)
            s_children = sum(stability.get(c, 0.0) for c in node.children)
            if viable and s_children > s_node:
                for child in node.children:
                    _select(child)
            else:
                if node.size >= self.min_cluster_size:
                    selected.add(nid)

        _select(root_id)
        return selected

    # ── Label assignment ──────────────────────────────────────────────────────

    def _assign_labels(
        self,
        n_points: int,
        tree:     dict[int, _ClusterNode],
        selected: set[int],
    ) -> np.ndarray:
        """Map each original point to its cluster label (or -1 for noise)."""
        labels = np.full(n_points, -1, dtype=int)

        def _collect_point_ids(nid: int) -> Iterator[int]:
            """Recursively yield all original point indices under *nid*."""
            node = tree.get(nid)
            if node is None:
                return
            for pid in node.point_ids:
                yield pid
            for child in node.children:
                yield from _collect_point_ids(child)

        for cluster_label, nid in enumerate(sorted(selected)):
            for pid in _collect_point_ids(nid):
                if 0 <= pid < n_points:
                    labels[pid] = cluster_label

        return labels
