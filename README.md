## Sprint 2: Navigation Layer

### Modules
- `src/astar.py` — Custom A* pathfinding with Haversine heuristic
- `src/visualizer.py` — Path visualization on Model Town street map

### Usage
```python
import networkx as nx
from src.astar import astar
from src.visualizer import visualize_path

G = nx.read_graphml("data/model_town.graphml")
nodes = list(G.nodes())

path = astar(G, start=nodes[0], goal=nodes[-1])
visualize_path(G, path, start=nodes[0], goal=nodes[-1], title="Long Path Example")
```

### Performance
- Graph: 798 nodes, 1928 edges
- TC1 (short path): 2ms, 32 nodes
- TC2 (long path): 10ms, 45 nodes  
- TC5 (complex route): 8ms, 38 nodes
- All benchmarks well under 50ms limit
- Heuristic: Haversine distance (great-circle distance in meters)
