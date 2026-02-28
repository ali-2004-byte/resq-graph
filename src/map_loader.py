import osmnx as ox
import networkx as nx
import os
import json

DATA_DIR = "data"
GRAPH_PATH = os.path.join(DATA_DIR, "model_town.graphml")
STATS_PATH = os.path.join(DATA_DIR, "model_town_stats.json")

ox.settings.use_cache = True                 # cache results for faster reruns
ox.settings.log_console = True               # show logs in console
ox.settings.overpass_max_query_area_size = 50_000_000  # increase max query area (50 km^2)

bbox = (74.347, 31.505, 74.370, 31.535) 

north, south, east, west = bbox

def remove_isolated_nodes(G):
    isolated = list(nx.isolates(G))
    G_clean = G.copy()
    G_clean.remove_nodes_from(isolated)
    return G_clean, len(isolated)


def get_graph_stats(G):
    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "weakly_connected": nx.is_weakly_connected(G),
    }


def bake_map():
    os.makedirs(DATA_DIR, exist_ok=True)

    # 🟢 If GraphML already exists → load instead of recreate
    if os.path.exists(GRAPH_PATH):
        print("GraphML exists. Loading from disk...")
        G = nx.read_graphml(GRAPH_PATH)
        return G

    print("GraphML not found. Downloading from OSM...")

    G = ox.graph_from_bbox(
        bbox,
        simplify=True,
        network_type="drive"
    )

    print("Removing isolated nodes...")
    G_clean, removed = remove_isolated_nodes(G)

    print("Saving GraphML...")
    ox.save_graphml(G_clean, GRAPH_PATH)

    print("Saving statistics...")
    stats = get_graph_stats(G_clean)
    stats["isolated_nodes_removed"] = removed

    with open(STATS_PATH, "w") as f:
        json.dump(stats, f, indent=4)

    # 🔄 Verify reload
    G_test = nx.read_graphml(GRAPH_PATH)
    assert G_test.number_of_nodes() > 0
    print("Reload verification successful.")

    return G_clean
