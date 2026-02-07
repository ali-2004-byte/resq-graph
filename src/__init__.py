import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import osmnx as ox
import networkx as nx

bbox = (33.72, 33.64, 73.10, 73.00)

G = ox.graph_from_bbox(
    bbox,
    network_type="drive"
)
print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")