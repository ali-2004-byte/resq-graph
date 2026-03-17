import heapq
import math

def haversine(G, u, v):
    lat1, lon1 = G.nodes[u]['y'], G.nodes[u]['x']
    lat2, lon2 = G.nodes[v]['y'], G.nodes[v]['x']
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def astar(G, start, goal):
    """
    A* pathfinding algorithm.

    Parameters:
        G (networkx.Graph): Graph with 'x' (lon) and 'y' (lat) node attributes
        start (node): Start node ID
        goal (node): Goal node ID

    Returns:
        list: Ordered list of node IDs OR None if no path exists
    """
    if len(G.nodes) == 0:
        raise ValueError("Graph is empty.")
    if start == goal:
        return [start]
    if start not in G or goal not in G:
        return None

    open_set = []
    heapq.heappush(open_set, (0, start))

    came_from = {}
    g_score = {node: float('inf') for node in G.nodes}
    g_score[start] = 0
    f_score = {node: float('inf') for node in G.nodes}
    f_score[start] = haversine(G, start, goal)

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1]

        for neighbor in G.neighbors(current):
            edge_data = G[current][neighbor]
            weight = min(float(d.get('length', 1)) for d in edge_data.values())
            tentative_g = g_score[current] + weight

            if tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + haversine(G, neighbor, goal)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))

    return None