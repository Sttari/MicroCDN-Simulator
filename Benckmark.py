import time
import random
from collections import defaultdict, deque

class NetworkSimulator:
    def __init__(self, num_nodes):
        self.num_nodes = num_nodes
        # Using a dictionary of lists for the adjacency list (used by BFS)
        self.graph = defaultdict(list)
        self.edges = []
        
        # DSU Arrays
        self.parent = list(range(num_nodes))
        self.rank = [1] * num_nodes

    def add_link(self, u, v, latency):
        """Adds a bidirectional fiber link between two nodes."""
        self.graph[u].append((v, latency))
        self.graph[v].append((u, latency))
        self.edges.append((u, v, latency))
        self.dsu_union(u, v)

    # --- DSU IMPLEMENTATION ---
    def dsu_find(self, i):
        """Finds the root of node i with Path Compression."""
        if self.parent[i] == i:
            return i
        # Compress the path by pointing directly to the root
        self.parent[i] = self.dsu_find(self.parent[i])
        return self.parent[i]

    def dsu_union(self, i, j):
        """Connects two network segments with Union by Rank."""
        root_i = self.dsu_find(i)
        root_j = self.dsu_find(j)
        if root_i != root_j:
            if self.rank[root_i] < self.rank[root_j]:
                self.parent[root_i] = root_j
            elif self.rank[root_i] > self.rank[root_j]:
                self.parent[root_j] = root_i
            else:
                self.parent[root_j] = root_i
                self.rank[root_i] += 1

    def is_connected_dsu(self, u, v):
        """O(1) time complexity to check if a path exists."""
        return self.dsu_find(u) == self.dsu_find(v)

    # --- BFS IMPLEMENTATION ---
    def is_connected_bfs(self, start, target):
        """O(V + E) time complexity to check if a path exists."""
        visited = set()
        queue = deque([start])
        visited.add(start)

        while queue:
            current = queue.popleft()
            if current == target:
                return True
            for neighbor, _ in self.graph[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return False

# --- BENCHMARK RUNNER ---
def run_benchmark():
    print("--- MICRO-CDN CONNECTIVITY BENCHMARK ---")
    num_nodes = 5000  # Large enough to show a difference
    sim = NetworkSimulator(num_nodes)

    # 1. Generate a dense random network topology
    print(f"Building network with {num_nodes} nodes...")
    for i in range(num_nodes - 1):
        # Guarantee it's fully connected first
        sim.add_link(i, i + 1, random.randint(10, 100))
    
    # Add random extra connections
    for _ in range(10000):
        u, v = random.randint(0, num_nodes-1), random.randint(0, num_nodes-1)
        sim.add_link(u, v, random.randint(10, 100))

    # Pick two nodes far apart
    client_node = 0
    origin_server = num_nodes - 1

    # 2. Benchmark BFS
    start_time = time.perf_counter()
    bfs_result = sim.is_connected_bfs(client_node, origin_server)
    bfs_time = (time.perf_counter() - start_time) * 1000

    # 3. Benchmark DSU
    start_time = time.perf_counter()
    dsu_result = sim.is_connected_dsu(client_node, origin_server)
    dsu_time = (time.perf_counter() - start_time) * 1000

    print(f"\n[RESULTS]")
    print(f"BFS Verification Time: {bfs_time:.4f} ms (Found: {bfs_result})")
    print(f"DSU Verification Time: {dsu_time:.4f} ms (Found: {dsu_result})")
    if dsu_time > 0:
        print(f"-> DSU was {bfs_time / dsu_time:.2f}x faster!")

if __name__ == "__main__":
    run_benchmark()