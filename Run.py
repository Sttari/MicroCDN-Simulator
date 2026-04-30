import time
import random
import concurrent.futures
from Simulator import NetworkTopologyBuilder, MicroCDNSimulator

def run_single_strategy(strategy, regions, nodes_per_region, num_requests, cache_size, video_library, traffic_weights, seed):
    """This function runs on an isolated CPU core."""

    # 1. Synchronize with the same seed
    random.seed(seed)

    sim = MicroCDNSimulator(capacity=cache_size, strategy=strategy)
    NetworkTopologyBuilder.build_regional_clusters(sim, regions, nodes_per_region)
    
    origin_server = len(sim.graph) - 1
    sim.node_metadata[origin_server] = {"type": "origin"}
    client_node = [node for node in sim.graph.keys() if node != origin_server]

    hits = 0
    total_latency_cached = 0

    for i in range(num_requests):
        client = random.choice(client_node)
        target_video = random.choices(video_library, weights= traffic_weights, k = 1)[0]

        res = sim.fetch_payload(client, origin_server, target_video)

        if res:
            total_latency_cached += res["latency"]
            if res["status"] == "hit":
                hits += 1

    hit_rate = (hits / num_requests) * 100
    return strategy, hit_rate, total_latency_cached


def run_parallel_cache_test():
    regions = ["us-east", "us-west", "eu-central", "ap-south"]
    nodes_per_region = 50
    num_requests = 15000
    cache_size = 10
    
    # Generate the video library and traffic weights
    video_library = [f"video_{i}.mp4" for i in range(50)]
    # First 5 videos get heavy traffic, the rest get low traffic
    traffic_weights = [100] * 5 + [5] * 45 

    # Generate random seed for entire brenchmark run
    master_seed = random.randint(1, 999999)

    results = {}
    strategies = ["RANDOM", "LRU", "LFU"]

    print(f"\n--- BOOTING SYNCHRONIZED PARALLEL CDN SIMULATION ---")
    print(f"Master Seed: {master_seed}")
    print(f"Nodes per region: {nodes_per_region} | Requests: {num_requests}")
    print("Dispatching tasks to CPU cores... please wait.\n")

    start_time = time.perf_counter()

    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = []
        for strategy in strategies:
            future = executor.submit(
                run_single_strategy,
                strategy, regions, nodes_per_region, num_requests, cache_size, video_library, traffic_weights, master_seed
            )
            futures.append(future)

        for future in concurrent.futures.as_completed(futures):
            strategy_name, hit_rate, latency = future.result()
            results[strategy_name] = {"hit_rate": hit_rate, "latency": latency}
            print(f"[{strategy_name}] CPU Core finished! Hit Rate: {hit_rate:.1f}%")

    execution_time = time.perf_counter() - start_time

    # Print Comparison
    print("\n==================================================")
    print("             PARALLEL A/B/C TEST REPORT")
    print("==================================================")
    print(f"Execution Time: {execution_time:.2f} seconds")
    print("--------------------------------------------------")
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
    run_parallel_cache_test()