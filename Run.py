import time
import math
import random
import concurrent.futures
from Simulator import MicroCDNSimulator
from Builder import NetworkTopologyBuilder

def get_zipf_weights(num_videos, alpha = 1.5):
    """Generates realistic power-law traffic weights."""
    return [1.0 / math.pow(i, alpha) for i in range(1, num_videos + 1) ]


def run_single_strategy_on_scale_free(strategy, num_nodes, num_requests, cache_size, video_library, seed, isAnycast = True):
    """This function runs on an isolated CPU core."""

    # Synchronize with the same seed
    random.seed(seed)

    # Initiate the simulator and the graph builder for simulation
    sim = MicroCDNSimulator(capacity=cache_size, strategy=strategy)
    NetworkTopologyBuilder.build_scale_free_network(sim, num_nodes, m = 2)
    
    # Initiate a list of client node to simulator request from client
    client_nodes = [node for node in sim.graph.keys() if sim.node_metadata[node].get("type") == "client"]

    # Initiate the stats for simulation
    hits = 0
    total_latency_cached = 0
    flash_crowd = 0
    chaos_monkey = 0
    phase_length = num_requests // 3


    # Actual Simulation Loop
    for i in range(num_requests):

        # Generate a zipf function to simulator the concentration of videos with centered wieght
        base_zipf = get_zipf_weights(500, alpha=1.5)
        current_phase = i // phase_length

        # Introducing viral shifts
        if current_phase == 0:
            # Phase 1 (Morning): Videos 0-4 are viral
            traffic_weights = base_zipf

        elif current_phase == 1:
            # Phase 2 (Afternoon): Videos 10-14 are viral. Videos 0-4 drop to noise.
            traffic_weights = base_zipf[5:15] + base_zipf[0:5] + base_zipf[15:]

        else:
            # Phase 3 (Evening): Videos 20-24 are viral.
            traffic_weights = base_zipf[15:35] + base_zipf[0:15] + base_zipf[35:]

        # Randomly select our client to start
        client = random.choice(client_nodes)
        target_video = random.choices(video_library, weights= traffic_weights, k = 1)[0]

        
        res = sim.fetch_payload(client, target_video, isAnycast)

        if res:
            total_latency_cached += res["latency"]
            if res["status"] == "hit":
                hits += 1

        # 0.1% chance of a "Flash Crowd" event occurring
        # This simulates a sudden spike massive spike of 50 simultaneous requests for the exact same video
        if random.random() < 0.005:
            if current_phase == 0: viral_target = "video_10.mp4"
            elif current_phase == 1: viral_target = "video_20.mp4"
            else: viral_target = "video_0.mp4"
            flash_crowd += 1
        
            for _ in range(50):
                # All coming from random clients 
                client = random.choice(client_nodes)
                
                res = sim.fetch_payload(client, target_video, isAnycast)

                if res:
                    total_latency_cached += res["latency"]
                    # if res["status"] == "hit":
                    #     hits += 1
    
        # 0.5% chance of a Malicious Botnet / Web Scraper
        if random.random() < 0.005:
            # The bot requests 50 random, highly unpopular videos exactly once
            scraper_targets = random.sample(range(100, 500), 50) 
            
            for bot_target_id in scraper_targets:
                bot_video = f"video_{bot_target_id}.mp4"
                client = random.choice(client_nodes)
                
                res = sim.fetch_payload(client, target_video, isAnycast)
                
                if res:
                    total_latency_cached += res["latency"]
                    # if res["status"] == "hit": 
                    #     hits += 1

        # 2% chance the Chaos Monkey attacks the network during this tick
        if random.random() < 0.02:
            broken = sim.unleash_chaos_monkey(failure_rate=0.03)
            chaos_monkey += 1

    hit_rate = (hits / num_requests) * 100
    return strategy, hit_rate, total_latency_cached, flash_crowd, chaos_monkey




def run_parallel_cache_test(num_requests = 15000, cache_size = 10, num_nodes = 100, isAnycast = True):
    regions = ["us-east", "us-west", "eu-central", "ap-south"]
    nodes_per_region = 50

    # Generate the video library and traffic weights
    video_library = [f"video_{i}.mp4" for i in range(500)]


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
                strategy, num_nodes, num_requests, cache_size, video_library, master_seed, isAnycast
            )
            futures.append(future)

        for future in concurrent.futures.as_completed(futures):
            strategy_name, hit_rate, latency, fresh, monkey = future.result()
            results[strategy_name] = {"hit_rate": hit_rate, "latency": latency}
            print(f"[{strategy_name}] CPU Core finished! Hit Rate: {hit_rate:.1f}%")
            print(f"[{strategy_name}] Hit Flash Crowds {fresh} times, hit Chaos Monkey {monkey} times\n")

    execution_time = time.perf_counter() - start_time

    # Print Comparison
    print("\n==================================================")
    print("             PARALLEL A/B TEST REPORT")
    print("==================================================")
    print(f"Execution Time: {execution_time:.2f} seconds")
    print("--------------------------------------------------")
    print(f"Control Group (RANDOM)   : {results['RANDOM']['hit_rate']:.1f}% Hit Rate")
    print(f"Experimental  (LRU)      : {results['LRU']['hit_rate']:.1f}% Hit Rate")
    print(f"Experimental  (LFU)      : {results['LFU']['hit_rate']:.1f}% Hit Rate")
    print(f"Experimental  (W-TINYLFU): {results['W-TINYLFU']['hit_rate']:.1f}% Hit Rate")
    print("--------------------------------------------------")
    print(f"Control Group (RANDOM)   : Avg. {(results['RANDOM']['latency']/num_requests):.1f} latency Cost")
    print(f"Experimental  (LRU)      : Avg. {(results['LRU']['latency']/num_requests):.1f} latency Cost")
    print(f"Experimental  (LFU)      : Avg. {(results['LFU']['latency']/num_requests):.1f} latency Cost")
    print(f"Experimental  (W-TINYLFU): Avg. {(results['W-TINYLFU']['latency']/num_requests):.1f} latency Cost")
    print("--------------------------------------------------")

    lfu_vs_random_diff = results['LFU']['hit_rate'] - results['RANDOM']['hit_rate']
    lfu_vs_lru_diff = results['LFU']['hit_rate'] - results['LRU']['hit_rate']
    wtlfu_vs_lru_diff = results['W-TINYLFU']['hit_rate'] - results['LRU']['hit_rate']
    wtlfu_vs_lfu_diff = results['W-TINYLFU']['hit_rate'] - results['LFU']['hit_rate']
    
    print(f"LFU beat RANDOM by:         +{lfu_vs_random_diff:.1f}% hit rate")
    print(f"LFU beat LRU by:            +{lfu_vs_lru_diff:.1f}% hit rate")
    print(f"W-TINYLFU beat LRU by:      +{wtlfu_vs_lru_diff:.1f}% hit rate")
    print(f"W-TINYLFU beat LFU by:      +{wtlfu_vs_lfu_diff:.1f}% hit rate")
    print("--------------------------------------------------")
    

    print("==================================================\n")

if __name__ == "__main__":
    run_parallel_cache_test(num_requests = 30000, cache_size = 10, num_nodes = 500)