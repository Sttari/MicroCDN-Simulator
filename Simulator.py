import random
from collections import defaultdict
from CacheNode import CacheNode 
import heapq

class MicroCDNSimulator:
    def __init__(self, capacity = 5, strategy = "LRU"):
        self.num_nodes = 0
        self.origin_server = 0
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

    def unleash_chaos_monkey(self, failure_rate = 0.05):
        """
        Randomly severs a percentage of active network links
        failure_rate: Float representing the chance any given link fails (0.05 = 5%)
        """
        broken_count = 0

        # We need to rebuild self.edge and update self.graph
        new_edges = []

        for u, v, latency in self.edges:
            # If the link is broken, 50% chance it comes back online
            if latency == float('inf'):
                if random.random() < 0.5:
                    restored_latency = random.randint(10, 100)
                    new_edges.append((u, v, restored_latency))
                    self.graph[u][v] = restored_latency
                    self.graph[v][u] = restored_latency
                else:
                    new_edges.append((u, v, float('inf')))
            
            elif random.random() < failure_rate:
                new_edges.append((u, v, float('inf')))
                self.graph[u][v] = float('inf')
                self.graph[u][v] = float('inf')
                broken_count += 1
            else:
                new_edges.append((u, v, latency))
        self.edges = new_edges
        return broken_count

    def find_nearest_anycast(self, start_node, node_type):
        """
        Uses Dijkstra's Algorithm to find the closest Anycast Edge Cache.
        Returns: (nearest_edgenode_id, latency_to_edge)
        """
        dist= {node: float('inf') for node in range(self.num_nodes)}
        dist[start_node] = 0

        pq = [(0, start_node)]
        nearest_edge = None
        min_edge_latency = float('inf')

        while pq:
            curr_latency, node = heapq.heappop(pq)

            if curr_latency > dist[node]:
                continue

            if self.node_metadata.get(node, {}).get("type") == node_type:
                if curr_latency < min_edge_latency:
                    min_edge_latency = curr_latency
                    nearest_edge = node
                continue
            
            for neighbour, latency in self.graph[node].items():
                if latency == float('inf'):
                    continue
                new_latency = curr_latency + latency
                if new_latency < dist[neighbour]:
                    dist[neighbour] = new_latency
                    heapq.heappush(pq, (new_latency, neighbour))
        
        return nearest_edge, min_edge_latency

    
    def calculate_bellman_ford(self, start_node):
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
        dist[self.origin_server] = 0

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




    def fetch_payload(self, client_node,  payload_id):
        """
        Inputs:
            client_node (int): The user requesting the file.
            payload_id (str): The unique identifier for the requested data.
            
        Flow:
            1. Call self.calculate_bellman_ford(client_node) to get the ideal path.
            2. Iterate through the nodes in that path.
            3. Check if the node is an "edge_cache" and if payload_id is in self.cache_layer[node].
            4. CACHE HIT: Return early, log the reduced latency.
            5. CACHE MISS: Continue to origin_server. On the return trip, populate the 
               cache_layer of the edge nodes you pass through.
        """
        # 1: Get the ideal path and total latency, throw an error if no path exists
        path, total_latency = self.calculate_bellman_ford(client_node)
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
            "served_by": self.origin_server,
            "latency": total_latency,
            "data": fetched_data
        }

    def fetch_payload_anycast(self, client_node, payload_id):
        """
        Inputs:
        client_node (int): The user requesting the file.
        payload_id (str): The unique identifier for the requested data.

        Flow:
        1. Call self.find_nearest_anycast_edge(client_node) to get the ideal path to closest anycast
        2. Cache Hit: return earily with data
        2. Cache Miss:
        """
        edge_node, client_to_edge_latency = self.find_nearest_anycast(client_node, "edge_cache")
        if edge_node is None:
            return None
        

        edge_cache = self.cache_layer.get(edge_node)
        if  edge_cache:
            cached_data = edge_cache.get(payload_id)
            if cached_data:
                return {
                    "status":"hit",
                    "latency": client_to_edge_latency,
                    "served_by":edge_node
                }
        else :
            self.cache_layer[edge_node] = CacheNode(self.cache_capacity, self.cache_strategy)
            
        origin_server, edge_to_origin_latency = self.find_nearest_anycast(edge_node, "origin")
        if edge_to_origin_latency == float('inf'):
            return None
        fetched_data = f"Binary_Data_For_{payload_id}"

        self.cache_layer[edge_node].put(payload_id, fetched_data)
        total_latency = client_to_edge_latency + edge_to_origin_latency

        return {
            "status": "miss", 
            "latency": total_latency,
            "served_by": origin_server
        }
            
