import networkx as nx
import numpy as np
import os

def compute_distance_matrix(G, save_path="data/distance_matrix.npy"):
    """
    Computes all-pairs shortest path distances and saves matrix.
    """

    nodes = list(G.nodes())
    node_index = {node: i for i, node in enumerate(nodes)}

    n = len(nodes)
    dist_matrix = np.full((n, n), np.inf)

    for source, lengths in nx.all_pairs_dijkstra_path_length(G, weight="length"):
        i = node_index[source]
        for target, dist in lengths.items():
            j = node_index[target]
            dist_matrix[i][j] = dist

    np.save(save_path, dist_matrix)

    return dist_matrix, node_index

def load_distance_matrix(path="data/distance_matrix.npy"):
    """
    Loads precomputed distance matrix.
    """

    if not os.path.exists(path):
        raise FileNotFoundError("Distance matrix not found. Run computation first.")

    return np.load(path)

def get_distance(matrix, node_index, u, v):
    """
    Returns distance between two nodes in O(1).
    """

    i = node_index[u]
    j = node_index[v]

    return matrix[i][j]