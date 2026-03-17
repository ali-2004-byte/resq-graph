from astar import astar
from visualizer import visualize_path
import networkx as nx
import time

def validate_path(G, path):
    """Confirms every step in the path is a valid edge in the graph."""
    if path is None:
        return False
    for i in range(len(path) - 1):
        if not G.has_edge(path[i], path[i+1]):
            print(f"  ❌ Invalid edge: {path[i]} → {path[i+1]}")
            return False
    return True

def run_test(G, test_name, start, goal, expect_none=False):
    """Runs a single A* test case with timing."""
    print(f"\n--- {test_name} ---")
    t0 = time.time()
    path = astar(G, start, goal)
    elapsed = (time.time() - t0) * 1000

    if expect_none:
        result = "✓ PASS" if path is None else "✗ FAIL"
        print(f"  Expected: None | Got: {path} | {result}")
    else:
        valid = validate_path(G, path)
        result = "✓ PASS" if path and valid else "✗ FAIL"
        print(f"  Path length: {len(path) if path else 0} nodes | Valid: {valid} | {result}")

    print(f"  Time: {elapsed:.2f}ms")
    assert elapsed < 50, f"Performance violation: {elapsed:.2f}ms > 50ms"
    return path

if __name__ == "__main__":
    G = nx.read_graphml("data/model_town.graphml")

    print(type(G))

    for node in G.nodes:
        G.nodes[node]['x'] = float(G.nodes[node]['x'])
        G.nodes[node]['y'] = float(G.nodes[node]['y'])
   
    for u, v, key in G.edges(keys=True):
        if 'length' in G[u][v][key]:
            G[u][v][key]['length'] = float(G[u][v][key]['length'])

    
    nodes = list(G.nodes())

    # Define test cases
    tc1 = run_test(G, "TC1: Short Path",    nodes[0],   nodes[5])
    nx1 = nx.shortest_path(G, nodes[0], nodes[5], weight='length')
    print("A* length:", len(tc1))
    print("NX length:", len(nx1))
    tc2 = run_test(G, "TC2: Long Path",     nodes[0],   nodes[-1])
    nx2 = nx.shortest_path(G, nodes[0], nodes[-1], weight='length')
    print("A* length:", len(tc2))
    print("NX length:", len(nx2))

    tc3 = run_test(G, "TC3: Same Node",     nodes[50],  nodes[50])
    nx3 = nx.shortest_path(G, nodes[50], nodes[50], weight='length')
    print("A* length:", len(tc3))
    print("NX length:", len(nx3))

    tc4 = run_test(G, "TC4: Unreachable", nodes[0], "fake_node_999", expect_none=True)
    print("A* result:", tc4)
    tc5 = run_test(G, "TC5: Complex Route", nodes[100], nodes[500])
    nx5 = nx.shortest_path(G, nodes[100], nodes[500], weight='length')
    print("A* length:", len(tc5))
    print("NX length:", len(nx5))

    visualize_path(G, tc1, nodes[0], nodes[5],
                    title="TC1: Short Path",
                save_path="outputs/path_tc1_short.png")

    visualize_path(G, tc2, nodes[0], nodes[-1],
                title="TC2: Long Path",
                save_path="outputs/path_tc2_long.png")

    visualize_path(G, tc5, nodes[100], nodes[500],
                title="TC5: Complex Route",
                save_path="outputs/path_tc5_complex.png")
