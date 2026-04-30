import time
import random
from collections import defaultdict, deque
from CacheNode import CacheNode 

class NetworkTopologyBuilder:
    """Factory class to build different network topologies for testing."""

    @staticmethod
    def build_random_mesh(sim, num_nodes : int, extra_edges: int):
        """ Topology 1: Random Mesh - Purely random Erdos-Renyi graph. """
        print(f"Building Random Mesh with {num_nodes} nodes and {extra_edges} extra edges...")
        
        sim.num_nodes = num_nodes
        # Ensure fully connectivity
        for i in range(num_nodes - 1):
            sim.add_link(i, i + 1, random.randint(10, 100))

        # Add extra connectivity with out self loops
        for _ in range(extra_edges):
            u, v = random.sample(range(num_nodes), 2)
            sim.add_link(u, v, random.randint(10, 100))

    
    @staticmethod
    def build_regional_clusters(sim, regions: list, nodes_per_region: int):
        """ Topology 2: Regional Clusters - Nodes are grouped into clusters with dense intra-cluster connectivity and sparse inter-cluster links. """
        print(f"Building Regional Clusters with ({len(regions)} regions)")
        region_nodes = {}
        node_id_counter = 0
        sim.num_nodes = len(regions) * nodes_per_region

        # 1. Build tight local networks (Intra-region)
        for region in regions:
            local_nodes = []
            for _ in range(nodes_per_region):
                local_nodes.append(node_id_counter)
                # Assign metadata to the node
                sim.node_metadata[node_id_counter] = {"region": region, "type": "client"}
                node_id_counter += 1
            
            region_nodes[region] = local_nodes

            # Connect local nodes with low latency (5 - 15 ms)
            for i in range(len(local_nodes) -1):
                sim.add_link(local_nodes[i], local_nodes[i + 1], random.randint(5, 15))
            
        
        # 2. Connect regions together via "backbone" routers (Inter-region)
        # High latency (80 - 200 ms) to simulate long-distance links
        region_names = list(regions)
        for i in range(len(region_names) - 1):
            router_a = random.choice(region_nodes[region_names[i]])
            router_b = random.choice(region_nodes[region_names[i + 1]])
            sim.add_link(router_a, router_b, random.randint(80, 200))

            # Mark these as edge cache candidates
            sim.node_metadata[router_a]["type"] = "edge_cache"
            sim.node_metadata[router_b]["type"] = "edge_cache"
        



class MicroCDNSimulator:
    def __init__(self, capacity = 5, strategy = "LRU"):
        self.num_nodes = 0
        self.graph = defaultdict(dict)  # For quick latency lookups: graph[u][v] = latency
        self.edges = []
        self.node_metadata = {}  # Store metadata for nodes (e.g., region, type)

        # Add CacheNode
        self.cache_capacity = capacity
        self.cache_strategy = strategy
        self.cache_layer = {} # Will hold NodeID -> CacheNode Object

    def add_link(self, u, v, latency):
        """ Add a bidirectional link between nodes u and v. """
        self.graph[u][v] = latency
        self.graph[v][u] = latency
        self.edges.append((u, v, latency))
    
    def calculate_bellman_ford(self, start_node, end_node):
        """
        Inputs:
            start_node (int): The client requesting data.
            end_node (int): The target origin server.
            
        Returns:
            path (list): The sequence of node IDs representing the lowest latency route.
            total_latency (int): The combined weight of the path.
            
        Requirements:
            - Must handle potential dynamic weight changes.
            - Should include the V-th iteration check for negative weight cycles.
        """
        dist = [float('inf')] * self.num_nodes
        successor  = [None] * self.num_nodes
        dist[end_node] = 0

        for _ in range(self.num_nodes - 1):
            for u, v , latency in self.edges:
                if dist[u] != float('inf') and dist[u] + latency < dist[v]:
                    dist[v] = dist[u] + latency
                    successor[v] = u
                if dist[v] != float('inf') and dist[v] + latency < dist[u]:
                    dist[u] = dist[v] + latency
                    successor[u] = v
        
        for u, v, latency in self.edges:
            if dist[u] != float('inf') and dist[u] + latency < dist[v]:
                raise ValueError("Routing Loop: Negative weight cycle detected")
            if dist[v] != float('inf') and dist[v] + latency < dist[u]:
                raise ValueError("Routing Loop: Negative weight cycle detected")
        
        if dist[start_node] == float('inf'):
            return None, float('inf')


        curr = start_node
        path = []
        while curr is not None:
            path.append(curr)
            curr = successor[curr]
        return path, dist[start_node]




    def fetch_payload(self, client_node, origin_server, payload_id):
        """
        Inputs:
            client_node (int): The user requesting the file.
            origin_server (int): The main server that permanently stores the file.
            payload_id (str): The unique identifier for the requested data.
            
        Flow:
            1. Call self.calculate_bellman_ford(client_node, origin_server) to get the ideal path.
            2. Iterate through the nodes in that path.
            3. Check if the node is an "edge_cache" and if payload_id is in self.cache_layer[node].
            4. CACHE HIT: Return early, log the reduced latency.
            5. CACHE MISS: Continue to origin_server. On the return trip, populate the 
               cache_layer of the edge nodes you pass through.
        """
        # 1: Get the ideal path and total latency, throw an error if no path exists
        path, total_latency = self.calculate_bellman_ford(client_node, origin_server)
        if not path: return None

        current_latency = 0
        edge_nodes_passed = []

        # 2. Trace the path from the client towards the origin server.
        for i in range(len(path)):
            curr_node = path[i]

            # Accomulate latency as we traverse the path
            if i > 0:
                current_latency += self.graph[path[i-1]][curr_node]
            
            # 3. Check if the current node is an edge cache and if it has the payload
            node_info = self.node_metadata.get(curr_node, {})

            if node_info.get("type") == "edge_cache":

                if curr_node not in self.cache_layer:
                    self.cache_layer[curr_node] = CacheNode(self.cache_capacity, self.cache_strategy)

                cached_data = self.cache_layer[curr_node].get(payload_id)

                # 4. Cache Hit: If the payload is found in the cache, update fatched data into for all edge nodes passed and return immediately with the reduced latency.
                if cached_data:
                    for missed_node in edge_nodes_passed:
                        if missed_node not in self.cache_layer:
                            self.cache_layer[missed_node] = CacheNode(self.cache_capacity, self.cache_strategy)
                        self.cache_layer[missed_node].put(payload_id, cached_data)

                    return  {
                        "status": "hit",
                        "served_by": curr_node,
                        "latency": current_latency,
                        "data": cached_data
                    }
                edge_nodes_passed.append(curr_node)
        # 5. Cache Miss: If we reach the origin server without a cache hit, we fetch the data and then populate the caches on the return trip.
        fetched_data = f"Binary_Data_For_{payload_id}"  # Simulate fetching data from the origin server
        for missed_node in edge_nodes_passed:
            if missed_node not in self.cache_layer:
                self.cache_layer[missed_node] = CacheNode(self.cache_capacity, self.cache_strategy)
            self.cache_layer[missed_node].put(payload_id, fetched_data)  # Populate the cache with the fetched data
        return {
            "status": "miss",
            "served_by": origin_server,
            "latency": total_latency,
            "data": fetched_data
        }


def run_ab_cache_test():
    regions = ["us-east", "us-west", "eu-central", "ap-south"]
    num_requests = 15000
    cache_size = 10  # Very small cache forces heavy eviction!
    
    # Generate the video library and traffic weights
    video_library = [f"video_{i}.mp4" for i in range(50)]
    # First 5 videos get heavy traffic (weight 100), the rest get low traffic (weight 5)
    traffic_weights = [1000] * 5 + [5] * 45 

    results = {}

    for strategy in ["RANDOM", "LRU", "LFU"]:
        print(f"\n--- BOOTING CDN WITH {strategy} CACHE ---")
        sim = MicroCDNSimulator(capacity=cache_size, strategy=strategy)
        NetworkTopologyBuilder.build_regional_clusters(sim, regions, nodes_per_region=50)
        
        origin_server = len(sim.graph) - 1 
        sim.node_metadata[origin_server] = {"type": "origin"}
        client_nodes = [node for node in sim.graph.keys() if node != origin_server]

        hits = 0
        total_latency_cached = 0

        # Run the traffic
        for i in range(num_requests):
            client = random.choice(client_nodes)
            # Pick a video based on our viral distribution
            target_video = random.choices(video_library, weights=traffic_weights, k=1)[0]
            
            res = sim.fetch_payload(client, origin_server, target_video)
            
            total_latency_cached += res["latency"]
            if res["status"] == "hit":
                hits += 1

        hit_rate = (hits / num_requests) * 100
        results[strategy] = {"hit_rate": hit_rate, "latency": total_latency_cached}
        
        print(f"[{strategy}] Done. Hit Rate: {hit_rate:.1f}%")

    # Print Comparison
    print("\n==================================================")
    print("             A/B TEST REPORT")
    print("==================================================")
    print(f"Control Group (RANDOM): {results['RANDOM']['hit_rate']:.1f}% Hit Rate")
    print(f"Experimental  (LRU):    {results['LRU']['hit_rate']:.1f}% Hit Rate")
    print(f"Experimental  (LFU):    {results['LFU']['hit_rate']:.1f}% Hit Rate")
    print("--------------------------------------------------")
    
    lfu_vs_random_diff = results['LFU']['hit_rate'] - results['RANDOM']['hit_rate']
    lfu_vs_lru_diff = results['LFU']['hit_rate'] - results['LRU']['hit_rate']
    
    print(f"LFU beat RANDOM by: +{lfu_vs_random_diff:.1f}% hit rate")
    print(f"LFU beat LRU by:    +{lfu_vs_lru_diff:.1f}% hit rate")
    print("==================================================\n")

if __name__ == "__main__":
    run_ab_cache_test()