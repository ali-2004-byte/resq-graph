# Sprint 2 Quick Reference Checklist
**⚡ Graph Navigation & A\* Search**

**Sprint Goal:** Implement custom A\* pathfinder and validate on real map
**Week:** 2 | **Phase:** The Skeleton | **Total Points:** 18 | **Estimated Time:** 8–10 hours

> **Dependency:** Requires `data/modeltown.graphml` and `data/distance_matrix.npy` from Sprint 1

---

## 🔍 US-005: Implement Custom A\* Pathfinding Algorithm

**Goal**
✅ A\* search implemented from scratch — no `nx.shortest_path` — with Haversine heuristic

**Checklist**
- [ ] Priority queue implemented using Python's `heapq`
- [ ] Haversine heuristic function written (accepts lat/lon coordinates)
- [ ] `astar(graph, start, goal)` returns ordered list of node IDs
- [ ] Edge case handled: unreachable nodes (returns `None` or empty list)
- [ ] Edge case handled: same start and goal (returns `[start]`)
- [ ] Edge case handled: empty graph (raises informative error)
- [ ] Code review completed and function documented with docstring

**Key Code**

```python
import heapq
import math

def haversine(G, u, v):
    """Heuristic: straight-line distance between two nodes using lat/lon."""
    lat1, lon1 = G.nodes[u]['y'], G.nodes[u]['x']
    lat2, lon2 = G.nodes[v]['y'], G.nodes[v]['x']
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def astar(G, start, goal):
    """A* pathfinding on a NetworkX graph. Returns list of node IDs or None."""
    if start == goal:
        return [start]
    if start not in G or goal not in G:
        return None

    open_set = []
    heapq.heappush(open_set, (0, start))

    came_from = {}
    g_score = {node: float('inf') for node in G.nodes()}
    g_score[start] = 0

    f_score = {node: float('inf') for node in G.nodes()}
    f_score[start] = haversine(G, start, goal)

    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            # Reconstruct path
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1]

        for neighbor in G.neighbors(current):
            edge_data = G[current][neighbor]
            weight = list(edge_data.values())[0].get('length', 1)
            tentative_g = g_score[current] + weight

            if tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + haversine(G, neighbor, goal)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))

    return None  # No path found
```

**Expected Output**
```
Path found: [123456, 234567, 345678, ..., 987654]
Path length: 23 nodes
Computation time: 12.4ms
```

**Time:** 2–3 hours

---

## ✅ US-006: Validate A\* with Manual Test Cases

**Goal**
✅ 5 concrete test cases defined, visually validated, and performance benchmarked < 50ms

**Checklist**
- [ ] Test Case 1: Short path (2 nodes apart, same street)
- [ ] Test Case 2: Long path (opposite ends of Model Town)
- [ ] Test Case 3: Unreachable node (isolated node or disconnected subgraph)
- [ ] Test Case 4: Same node (start == goal, expect `[start]`)
- [ ] Test Case 5: Complex routing (multiple turns, crossing roads)
- [ ] Visual validation: plot start (green), goal (red), and path (blue) on map
- [ ] Path validity confirmed: every consecutive node pair is a valid edge in graph
- [ ] Performance benchmark logged: average < 50ms across all 5 tests

**Key Code**

```python
import time
import networkx as nx

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

# Load graph
G = nx.read_graphml("data/modeltown.graphml")
nodes = list(G.nodes())

# Define test cases
run_test(G, "TC1: Short Path",    nodes[0],   nodes[5])
run_test(G, "TC2: Long Path",     nodes[0],   nodes[-1])
run_test(G, "TC3: Same Node",     nodes[50],  nodes[50])
run_test(G, "TC4: Unreachable",   nodes[0],   "fake_node_999", expect_none=True)
run_test(G, "TC5: Complex Route", nodes[100], nodes[500])
```

**Expected Output**
```
--- TC1: Short Path ---
  Path length: 4 nodes | Valid: True | ✓ PASS
  Time: 3.1ms

--- TC2: Long Path ---
  Path length: 87 nodes | Valid: True | ✓ PASS
  Time: 34.6ms

--- TC3: Same Node ---
  Path length: 1 nodes | Valid: True | ✓ PASS
  Time: 0.1ms

--- TC4: Unreachable ---
  Expected: None | Got: None | ✓ PASS
  Time: 0.2ms

--- TC5: Complex Route ---
  Path length: 42 nodes | Valid: True | ✓ PASS
  Time: 18.7ms

All tests passed ✓
```

**Time:** 1–1.5 hours

---

## 🗺️ US-007: Create Path Visualization Module

**Goal**
✅ Matplotlib visualization showing path on street network with color-coded markers and zoom/pan

**Checklist**
- [ ] `visualize_path(G, path, start, goal)` function created in `src/visualizer.py`
- [ ] Start node marked as **green** circle
- [ ] Goal node marked as **red** circle
- [ ] Path edges drawn in **blue**
- [ ] Remaining street network shown in **light gray** as background
- [ ] Zoom and pan work interactively (standard matplotlib behavior)
- [ ] Function accepts optional `title` and `save_path` arguments
- [ ] Tested and verified on at least 2 of the TC paths from US-006

**Key Code**

```python
import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox

def visualize_path(G, path, start, goal, title="A* Path", save_path=None):
    """
    Visualizes an A* path on the Model Town street network.

    Parameters
    ----------
    G : networkx.MultiDiGraph
        The road network graph.
    path : list
        Ordered list of node IDs from start to goal.
    start : int or str
        Start node ID.
    goal : int or str
        Goal node ID.
    title : str
        Plot title.
    save_path : str, optional
        If provided, saves figure to this path instead of showing it.
    """
    fig, ax = ox.plot_graph(
        G,
        show=False,
        close=False,
        bgcolor='white',
        node_size=0,
        edge_color='lightgray',
        edge_linewidth=0.5,
    )

    if path:
        # Draw path edges
        path_edges = list(zip(path[:-1], path[1:]))
        edge_xs, edge_ys = [], []
        for u, v in path_edges:
            x1, y1 = G.nodes[u]['x'], G.nodes[u]['y']
            x2, y2 = G.nodes[v]['x'], G.nodes[v]['y']
            edge_xs += [x1, x2, None]
            edge_ys += [y1, y2, None]
        ax.plot(edge_xs, edge_ys, color='royalblue', linewidth=2.5, label='Path', zorder=3)

    # Start and goal markers
    ax.scatter(G.nodes[start]['x'], G.nodes[start]['y'],
               c='green', s=120, zorder=5, label='Start')
    ax.scatter(G.nodes[goal]['x'], G.nodes[goal]['y'],
               c='red', s=120, zorder=5, label='Goal')

    ax.legend(loc='upper left')
    ax.set_title(title, fontsize=14)

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"  Saved to: {save_path}")
    else:
        plt.show()
```

**Expected Output**
```
Street network rendered in light gray
Blue line connecting start → goal along shortest path
Green dot at start node, red dot at goal node
Zoom/pan functional in interactive mode
Figure saved to: outputs/path_tc2_long.png
```

**Expected Files**
```
outputs/
├── path_tc1_short.png
├── path_tc2_long.png
└── path_tc5_complex.png
src/
└── visualizer.py
```

**Time:** 1–1.5 hours

---

## 📄 US-008: Document Navigation Layer API

**Goal**
✅ All navigation functions documented with docstrings, pseudocode, and README updated

**Checklist**
- [ ] `haversine(G, u, v)` — docstring with parameters, returns, and formula note
- [ ] `astar(G, start, goal)` — docstring with algorithm explanation and edge case notes
- [ ] `validate_path(G, path)` — docstring explaining what validation checks
- [ ] `visualize_path(G, path, start, goal, ...)` — full docstring with all params
- [ ] `notebooks/02_navigation.ipynb` created with end-to-end example (load graph → find path → visualize)
- [ ] `README.md` updated: new section **"Sprint 2: Navigation"** added
- [ ] Pseudocode block added to README or docstring for A\*

**Pseudocode to Include**

```
A* Search Pseudocode:
─────────────────────
OPEN ← priority queue containing start node
g[start] ← 0
f[start] ← haversine(start, goal)

WHILE OPEN is not empty:
    current ← node in OPEN with lowest f score
    IF current == goal:
        RETURN reconstruct_path(came_from, current)
    FOR each neighbor of current:
        tentative_g ← g[current] + edge_weight(current, neighbor)
        IF tentative_g < g[neighbor]:
            came_from[neighbor] ← current
            g[neighbor] ← tentative_g
            f[neighbor] ← tentative_g + haversine(neighbor, goal)
            ADD neighbor to OPEN

RETURN None  ← no path exists
```

**README Section to Add**

```markdown
## Sprint 2: Navigation Layer

### Modules
- `src/astar.py` — Custom A* pathfinding with Haversine heuristic
- `src/visualizer.py` — Path visualization on Model Town street map

### Usage
import networkx as nx
from src.astar import astar
from src.visualizer import visualize_path

G = nx.read_graphml("data/modeltown.graphml")
nodes = list(G.nodes())

path = astar(G, start=nodes[0], goal=nodes[-1])
visualize_path(G, path, start=nodes[0], goal=nodes[-1], title="Long Path Example")

### Performance
- Average path computation: < 50ms on Model Town graph (~2000–3000 nodes)
- Heuristic: Haversine distance (great-circle distance in meters)
```

**Time:** 0.5–1 hour

---

## 📊 Sprint 2 Summary

### Deliverables

**Code Files**
```
src/
├── __init__.py
├── astar.py             ← A* algorithm + Haversine heuristic
└── visualizer.py        ← Path visualization module
tests/
└── test_astar.py        ← 5 manual test cases + benchmarks
notebooks/
└── 02_navigation.ipynb  ← End-to-end demo
```

**Output Files**
```
outputs/
├── path_tc1_short.png
├── path_tc2_long.png
└── path_tc5_complex.png
```

**Documentation**
```
├── README.md      ← Updated with Sprint 2 navigation section
└── src/astar.py   ← Pseudocode + full docstrings
```

### Success Criteria

- [ ] A* implemented from scratch — no `nx.shortest_path` used anywhere
- [ ] All 5 test cases pass with printed results
- [ ] Path validity confirmed: every edge exists in graph
- [ ] All benchmarks < 50ms
- [ ] Visualization renders correctly with green/red/blue markers
- [ ] All functions have docstrings (numpy format preferred)
- [ ] README updated with Sprint 2 section
- [ ] Example notebook runs end-to-end without errors
- [ ] All files committed to version control (git)

---

## 🎯 Key Metrics to Track

After Sprint 2, you should have:

| Metric | Target |
|--------|--------|
| A* path (short) | < 10ms |
| A* path (long) | < 50ms |
| Test cases defined | 5 |
| Test cases passing | 5 / 5 |
| Path validity | 100% edges valid |
| Visualization outputs | ≥ 2 PNG files saved |
| Functions documented | 4 (haversine, astar, validate_path, visualize_path) |

---

## 📈 Expected Time Breakdown

| Task | Time | Start | End |
|------|------|-------|-----|
| US-005: A* Implementation | 2–3 hrs | Day 1 | Day 2 |
| US-006: Test Cases & Benchmarks | 1–1.5 hrs | Day 2 | Day 2 |
| US-007: Visualization Module | 1–1.5 hrs | Day 2–3 | Day 3 |
| US-008: Documentation | 0.5–1 hr | Day 3 | Day 3 |
| Testing & Polish | 1 hr | Day 3–4 | Day 4 |
| **Total** | **8–10 hrs** | **~1 week** | |

---

## 🆘 Common Issues & Fixes

**"KeyError: node not in graph"**
```python
# Always check node membership before calling A*
if start not in G.nodes() or goal not in G.nodes():
    print("Node not in graph — check GraphML was loaded correctly")
```

**"A* returns wrong path / longer than expected"**
```
→ Check Haversine uses G.nodes[u]['y'] for lat and ['x'] for lon (OSMnx convention)
→ Confirm edge weights use 'length' key (meters), not travel_time
→ Print g_score and f_score values for first few nodes to debug
```

**"Path not continuous — edges missing"**
```
→ OSMnx MultiDiGraph has parallel edges; access with G[u][v][0].get('length')
→ Use list(edge_data.values())[0] to get the first edge's attributes safely
```

**"Visualization shows blank / white plot"**
```python
# Ensure graph has 'x' and 'y' node attributes
print(dict(list(G.nodes(data=True))[0]))  # Should show 'x', 'y' keys
# If missing, re-bake map with osmnx (adds coordinates automatically)
```

**"Matplotlib plot doesn't show interactivity"**
```bash
pip install pyqt5
# or set in notebook:
%matplotlib widget
```

---

## 💡 Pro Tips

1. **Freeze node list once** — `list(G.nodes())` is slow on large graphs; call it once and store
2. **Use `ox.plot_graph` as base** — much faster than plotting edges manually with matplotlib
3. **Save figures, don't always show** — `save_path` argument avoids blocking execution in scripts
4. **Log path lengths** — comparing node count vs. expected street count helps catch heuristic bugs
5. **Test on small subgraph first** — extract a 200-node subgraph with `nx.subgraph()` to debug A* faster before running on full Model Town

---

## 📚 Resources

- OSMnx Docs: https://osmnx.readthedocs.io/
- NetworkX Shortest Paths: https://networkx.org/documentation/stable/reference/algorithms/shortest_paths.html
- Haversine Formula: https://en.wikipedia.org/wiki/Haversine_formula
- Python heapq: https://docs.python.org/3/library/heapq.html
- Matplotlib Interactive: https://matplotlib.org/stable/users/explain/figure/interactive.html

---

## ✅ Final Checklist Before Moving to Sprint 3

- [ ] `src/astar.py` written and working
- [ ] `src/visualizer.py` written and working
- [ ] All 5 test cases passing with benchmark < 50ms
- [ ] Path validity check passing for all test paths
- [ ] At least 2 path visualizations saved as PNG
- [ ] All functions have docstrings
- [ ] `notebooks/02_navigation.ipynb` runs top-to-bottom without errors
- [ ] README updated with Sprint 2 navigation section
- [ ] Files committed to git (`git commit -m "Sprint 2: A* navigation and visualization"`)
- [ ] Ready to load optimal stations and build simulation agents in Sprint 3

**You're all set! 🎉 Ready for Sprint 3: Genetic Algorithm & Strategic Solver**
