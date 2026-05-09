"""
traffic_profiler.py - Sprint 10

Generates a traffic-adjusted distance matrix for the Genetic Algorithm.
Since accidents spawn uniformly, central nodes naturally become traffic bottlenecks.
This script approximates traffic congestion by simulating 10,000 random ambulance trips,
tracking edge usage, and applying a congestion multiplier to frequently used edges.
"""

import networkx as nx
import numpy as np
import random
import os

def create_traffic_distance_matrix(
    graph_path="data/model_town.graphml",
    save_path="data/traffic_distance_matrix.npy",
    samples=10000,
    max_multiplier=2.5,
):
    print(f"Loading graph from {graph_path}...")
    G = nx.read_graphml(graph_path)
    nodes = list(G.nodes())
    node_index = {node: i for i, node in enumerate(nodes)}
    
    # 1. Initialize edge usage counts
    print("Simulating random trips to estimate traffic bottlenecks...")
    edge_usage = {(u, v, k): 0 for u, v, k in G.edges(keys=True)}
    
    # Precompute edge lengths for fast A* (or just use nx.shortest_path)
    # We will just use shortest path by length
    def weight_func(u, v, d):
        return min(float(e.get('length', 1)) for e in d.values())

    # Simulate random trips
    np.random.seed(42)
    random.seed(42)
    
    for i in range(samples):
        if i % 1000 == 0:
            print(f"  Simulated {i}/{samples} trips...")
        u, v = random.sample(nodes, 2)
        try:
            path = nx.shortest_path(G, source=u, target=v, weight=weight_func)
            # Increment usage for edges in path
            for j in range(len(path) - 1):
                n1 = path[j]
                n2 = path[j+1]
                # Find the key with minimum length
                min_key = min(G[n1][n2], key=lambda k: float(G[n1][n2][k].get('length', 1)))
                edge_usage[(n1, n2, min_key)] += 1
        except nx.NetworkXNoPath:
            continue

    # 2. Map usage to a multiplier
    max_usage = max(edge_usage.values()) if edge_usage else 1
    if max_usage == 0: max_usage = 1
    
    print(f"Max edge usage: {max_usage}")
    
    # Define a new weight function that includes the traffic penalty
    def traffic_weight_func(u, v, d):
        min_w = float('inf')
        for k, e in d.items():
            usage = edge_usage.get((u, v, k), 0)
            # Map usage linearly to [1.0, max_multiplier]
            multiplier = 1.0 + ((usage / max_usage) * (max_multiplier - 1.0))
            w = float(e.get('length', 1)) * multiplier
            if w < min_w:
                min_w = w
        return min_w

    # 3. Compute the all-pairs shortest paths using the traffic weights
    print("Computing all-pairs shortest paths with traffic weights (this may take a minute)...")
    n = len(nodes)
    dist_matrix = np.full((n, n), np.inf)
    
    for source, lengths in nx.all_pairs_dijkstra_path_length(G, weight=traffic_weight_func):
        i = node_index[source]
        for target, dist in lengths.items():
            j = node_index[target]
            dist_matrix[i][j] = dist

    print(f"Saving traffic distance matrix to {save_path}...")
    os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else ".", exist_ok=True)
    np.save(save_path, dist_matrix)
    print("Done!")
    return dist_matrix

if __name__ == "__main__":
    create_traffic_distance_matrix()
