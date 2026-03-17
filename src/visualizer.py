import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

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
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_facecolor('white')

    # Draw all edges in light gray
    for u, v, data in G.edges(data=True):
        x1, y1 = float(G.nodes[u]['x']), float(G.nodes[u]['y'])
        x2, y2 = float(G.nodes[v]['x']), float(G.nodes[v]['y'])
        ax.plot([x1, x2], [y1, y2], color='lightgray', linewidth=0.5, zorder=1)

    # Draw path edges in blue
    if path:
        edge_xs, edge_ys = [], []
        for a, b in zip(path[:-1], path[1:]):
            x1, y1 = float(G.nodes[a]['x']), float(G.nodes[a]['y'])
            x2, y2 = float(G.nodes[b]['x']), float(G.nodes[b]['y'])
            edge_xs += [x1, x2, None]
            edge_ys += [y1, y2, None]
        ax.plot(edge_xs, edge_ys, color='royalblue', linewidth=2.5, zorder=2)

    # Start and goal markers
    ax.scatter(float(G.nodes[start]['x']), float(G.nodes[start]['y']),
               c='green', s=120, zorder=5, label='Start')
    ax.scatter(float(G.nodes[goal]['x']), float(G.nodes[goal]['y']),
               c='red', s=120, zorder=5, label='Goal')

    ax.legend(loc='upper left')
    ax.set_title(title, fontsize=14)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"  Saved to: {save_path}")
    else:
        plt.show()