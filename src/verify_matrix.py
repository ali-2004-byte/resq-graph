import networkx as nx

G = nx.read_graphml("data/model_town.graphml")

# Pick any node
node = list(G.nodes)[0]

print("Node ID:", node)
print("Attributes:", G.nodes[node])

