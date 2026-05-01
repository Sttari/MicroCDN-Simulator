import time
import random
import concurrent.futures
from Simulator import MicroCDNSimulator
from Builder import NetworkTopologyBuilder

def run_single_strategy_on_regional_clusters(strategy, regions, nodes_per_region, num_requests, cache_size, video_library, traffic_weights, seed):
    """This function runs on an isolated CPU core."""

    # 1. Synchronize with the same seed
    random.seed(seed)

    sim = MicroCDNSimulator(capacity=cache_size, strategy=strategy)
    NetworkTopologyBuilder.build_regional_clusters(sim, regions, nodes_per_region)
    
    client_node = [node for node in sim.graph.keys() if sim.node_metadata[node].get("type") == "client"]

    hits = 0
    total_latency_cached = 0

    for i in range(num_requests):
        client = random.choice(client_node)
        target_video = random.choices(video_library, weights= traffic_weights, k = 1)[0]

        res = sim.fetch_payload(client, target_video)

        if res:
            total_latency_cached += res["latency"]
            if res["status"] == "hit":
                hits += 1

    hit_rate = (hits / num_requests) * 100
    return strategy, hit_rate, total_latency_cached

def run_single_strategy_on_scale_free(strategy, num_nodes, num_requests, cache_size, video_library, traffic_weights, seed):
    """This function runs on an isolated CPU core."""

    # 1. Synchronize with the same seed
    random.seed(seed)

    sim = MicroCDNSimulator(capacity=cache_size, strategy=strategy)
    NetworkTopologyBuilder.build_scale_free_network(sim, num_nodes, m = 2)
    
    client_nodes = [node for node in sim.graph.keys() if sim.node_metadata[node].get("type") == "client"]


    hits = 0
    total_latency_cached = 0
    flash_crowd = 0
    chaos_monkey = 0

    for _ in range(num_requests):
        client = random.choice(client_nodes)
        target_video = random.choices(video_library, weights= traffic_weights, k = 1)[0]

        res = sim.fetch_payload(client, target_video)

        # 0.1% chance of a "Flash Crowd" event occurring
        if random.random() < 0.001:
            # A massive spike of 50 simultaneous requests for the exact same video
            viral_target = "video_17.mp4" 
            flash_crowd += 1
        
            for _ in range(50):
                # All coming from random clients 
                client = random.choice(client_nodes)
                res = sim.fetch_payload(client, viral_target)
            
                if res:
                    total_latency_cached += res["latency"]
                    if res["status"] == "hit":
                        hits += 1
    
        # 2% chance the Chaos Monkey attacks the network during this tick
        if random.random() < 0.02:
            broken = sim.unleash_chaos_monkey(failure_rate=0.03)
            chaos_monkey += 1

        if res:
            total_latency_cached += res["latency"]
            if res["status"] == "hit":
                hits += 1

    hit_rate = (hits / num_requests) * 100
    return strategy, hit_rate, total_latency_cached, flash_crowd, chaos_monkey


def run_parallel_cache_test():
    regions = ["us-east", "us-west", "eu-central", "ap-south"]
    nodes_per_region = 50
    
    num_requests = 15000
    cache_size = 10
    num_nodes = 100

    # Generate the video library and traffic weights
    video_library = [f"video_{i}.mp4" for i in range(50)]
    # First 5 videos get heavy traffic, the rest get low traffic
    traffic_weights = [100] * 5 + [5] * 45 

    # Generate random seed for entire brenchmark run
    master_seed = random.randint(1, 999999)

    results = {}
    strategies = ["RANDOM", "LRU", "LFU", "W-TINYLFU"]

    print(f"\n--- BOOTING SYNCHRONIZED PARALLEL CDN SIMULATION ---")
    print(f"Master Seed: {master_seed}")
    print(f"Total Nodes: {num_nodes} | Requests: {num_requests}")
    # print(f"Nodes per region: {nodes_per_region} | Requests: {num_requests}")
    print("Dispatching tasks to CPU cores... please wait.\n")

    start_time = time.perf_counter()

    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = []
        for strategy in strategies:
            future = executor.submit(
                # run_single_strategy_on_regional_clusters,
                # strategy, regions, nodes_per_region, num_requests, cache_size, video_library, traffic_weights, master_seed
                run_single_strategy_on_scale_free,
                strategy, num_nodes, num_requests, cache_size, video_library, traffic_weights, master_seed
            )
            futures.append(future)

        for future in concurrent.futures.as_completed(futures):
            strategy_name, hit_rate, latency, fresh, monkey = future.result()
            results[strategy_name] = {"hit_rate": hit_rate, "latency": latency}
            print(f"[{strategy_name}] CPU Core finished! Hit Rate: {hit_rate:.1f}%")
            print(f"[{strategy_name}] Hit Flash Crowds {fresh} times, hit Chaos Monkey {monkey} times")

    execution_time = time.perf_counter() - start_time

    # Print Comparison
    print("\n==================================================")
    print("             PARALLEL A/B/C TEST REPORT")
    print("==================================================")
    print(f"Execution Time: {execution_time:.2f} seconds")
    print("--------------------------------------------------")
    print(f"Control Group (RANDOM)   : {results['RANDOM']['hit_rate']:.1f}% Hit Rate")
    print(f"Experimental  (LRU)      : {results['LRU']['hit_rate']:.1f}% Hit Rate")
    print(f"Experimental  (LFU)      : {results['LFU']['hit_rate']:.1f}% Hit Rate")
    print(f"Experimental  (W-TINYLFU): {results['W-TINYLFU']['hit_rate']:.1f}% Hit Rate")
    print("--------------------------------------------------")
    
    lfu_vs_random_diff = results['LFU']['hit_rate'] - results['RANDOM']['hit_rate']
    lfu_vs_lru_diff = results['LFU']['hit_rate'] - results['LRU']['hit_rate']
    wtlfu_vs_lru_diff = results['W-TINYLFU']['hit_rate'] - results['LRU']['hit_rate']
    wtlfu_vs_lfu_diff = results['W-TINYLFU']['hit_rate'] - results['LFU']['hit_rate']
    
    print(f"LFU beat RANDOM by:         +{lfu_vs_random_diff:.1f}% hit rate")
    print(f"LFU beat LRU by:            +{lfu_vs_lru_diff:.1f}% hit rate")
    print(f"W-TINYLFU beat LRU by:      +{wtlfu_vs_lru_diff:.1f}% hit rate")
    print(f"W-TINYLFU beat LFU by:      +{wtlfu_vs_lfu_diff:.1f}% hit rate")
    print("==================================================\n")

if __name__ == "__main__":
    run_parallel_cache_test()