import networkx as nx
from distance_matrix import compute_distance_matrix

G = nx.read_graphml("data/model_town.graphml")
for u, v, data in G.edges(data=True):
    if "length" in data:
        data["length"] = float(data["length"])
matrix, node_index = compute_distance_matrix(G)

print("Matrix shape:", matrix.shape)
print("Distance matrix saved.")