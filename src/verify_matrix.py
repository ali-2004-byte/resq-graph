import networkx as nx
import numpy as np

G = nx.read_graphml("data/model_town.graphml")

# FIX
for u, v, data in G.edges(data=True):
    if "length" in data:
        data["length"] = float(data["length"])

matrix = np.load("data/distance_matrix.npy")

nodes = list(G.nodes())

u = nodes[4]
v = nodes[10]

true_dist = nx.shortest_path_length(G, u, v, weight="length")

print("Matrix dist:", matrix[4][10])
print("Actual dist:", true_dist)