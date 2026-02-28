from map_loader import bake_map, get_graph_stats    

if __name__ == "__main__":
    G = bake_map()
    print(get_graph_stats(G))

