import random
from Simulator import MicroCDNSimulator

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
        
        @staticmethod
        def build_scale_free_network(sim, num_nodes, m=2):
            """
            Topology 3: Scale-Free Network (Barabási-Albert model)
            m = number of edges to attach from a new node to existing nodes.
            """
            print(f"Building Scale-Free Network ({num_nodes} nodes, m={m})...")
            sim.num_nodes = num_nodes

            # 1. Start with a small fully connected core of 'm' nodes (hubs)
            for i in range(m):
                for j in range(i+1, m):
                    sim.add_link(i,j,random.int(5, 20))
            
            # Track node degree for each node
            node_degrees = {i : m -1 for i in range(m)}
            if m == 1:
                node_degrees[0] = 1 # Edge case

            
            # 2. Add remaining nodes using Preferential Attachment
            for new_node in range(m, num_nodes):
                # Calculate prob based on current degrees
                existing_nodes = list(node_degrees.keys())
                weights = list(node_degrees.values())

                # Select 'm' distinct targets  based on weight (hubs are picked more often)
                # We loop to ensure distinct links
                targets = set()
                while len(target) < m:
                    target = random.choices(existing_nodes, weights=weights, k =1)[0]
                    targets.add(target)

                # Connect the new node
                node_degrees[new_node] = 0
                for target in targets:
                    # Add physics link
                    latency = random.randint(10, 100)
                    sim.add_link(new_node, target, latency)

                    # Update degrees
                    node_degrees[target] += 1
                    node_degrees[new_node] += 1

                # Designate the biggest hub as the origin server, and others as edge caches
                sorted_hubs = sorted(node_degrees.items(), key=lambda item:item[1], reverse=True)

                for idx, (node_id, degree) in enumerate(sorted_hubs):
                    if idx == 0:
                        sim.node_metadata[node_id] = {"type": "origin"}
                    elif idx < max (5, num_nodes // 10): # Top 10% become edge caches
                        sim.node_metadata[node_id] = {"type": "edge_cache"}
                    else:
                        sim.node_metadata[node_id] = {"type": "client"}