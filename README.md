# Micro-CDN: Distributed Systems Simulator

A high-performance, from-scratch Python simulation of a Global Content Delivery Network (CDN). 

Micro-CDN is not a wrapper around existing network libraries; it is a theoretical testbed built entirely in pure Python to empirically study the data structures, routing algorithms, and memory management architectures that power Tier-1 internet providers like Cloudflare, Netflix, and Akamai.

##  Project Objective
The goal of this project is to explore the mathematical and systemic realities of network architecture. By simulating hostile internet conditions (link flapping, botnets, flash crowds), this tool provides a measurable environment to prove *why* modern enterprise systems require advanced algorithms like W-TinyLFU and Anycast routing to survive the modern internet.

##  Core Features & Architecture

### 1. Network Topology & Routing
* **Scale-Free Internet Generation:** Generates node clusters using an $O(1)$ memory-optimized Barabási-Albert model with preferential attachment, perfectly mimicking the "Hub and Edge" reality of Tier-1 ISPs and local routers.
* **Anycast Routing:** Implements Dijkstra's algorithm to resolve Anycast IP requests, dynamically routing clients to the topologically closest edge cache.
* **Adaptive Routing (Fault Tolerance):** Network pathways are dynamically recalculated per request, allowing the network to auto-heal when links are severed.

### 2. Edge Cache Lifecycle Management
Features multiple custom-built caching mechanisms tested against each other in real-time:
* **W-TinyLFU (Enterprise Grade):** A custom implementation of the Window-TinyLFU architecture, featuring an LRU "Waiting Room," a Count-Min Sketch historical frequency tracker, and time-based aging/decay to eliminate "Zombie Data."
* **Standard Caches:** Includes pure LRU, LFU, and Random eviction strategies for baseline A/B/C testing.

### 3. Adversarial Traffic Generation
Simulates the chaotic nature of the global internet:
* **Zipfian (Power-Law) Distributions:** Models the "fat tail" of the internet, testing caches against a realistic ratio of viral content vs. obscure noise.
* **Trending Phase Shifts:** Dynamically alters the viral corpus mid-simulation to test if cache algorithms can drop old trends and adopt new ones ("Phase Shift Hangovers").
* **Flash Crowds & Scraper Botnets:** Injects sudden localized DDOS-style spikes and malicious cache-flushing scraper bots to stress-test the W-TinyLFU protection window.
* **The Chaos Monkey:** An asynchronous background process that randomly severs and restores fiber-optic links (link flapping) while traffic is actively flowing.

##  Getting Started

### Prerequisites
* Python 3.8+ (No external libraries required; uses pure standard library).

### Usage
Run the main simulation benchmark, which spawns isolated Python processes for each caching strategy to guarantee a mathematically fair, identically-seeded A/B/C test.
```bash
python Run.py
```

### Example Benchmark Output
```
--- BOOTING SYNCHRONIZED PARALLEL CDN SIMULATION ---
Master Seed: 9944
Total Nodes: 100 | Requests: 15000
Dispatching tasks to CPU cores... please wait.

Building Scale-Free Network (100 nodes, m=2)...
Building Scale-Free Network (100 nodes, m=2)...
Building Scale-Free Network (100 nodes, m=2)...
Building Scale-Free Network (100 nodes, m=2)...
[W-TINYLFU] CPU Core finished! Hit Rate: 87.5%
[W-TINYLFU] Hit Flash Crowds 63 times, hit Chaos Monkey 289 times

[LRU] CPU Core finished! Hit Rate: 81.5%
[LRU] Hit Flash Crowds 63 times, hit Chaos Monkey 289 times

[LFU] CPU Core finished! Hit Rate: 77.2%
[LFU] Hit Flash Crowds 63 times, hit Chaos Monkey 289 times

[RANDOM] CPU Core finished! Hit Rate: 76.3%
[RANDOM] Hit Flash Crowds 76 times, hit Chaos Monkey 332 times


==================================================
             PARALLEL A/B TEST REPORT
==================================================
Execution Time: 3.74 seconds
--------------------------------------------------
Control Group (RANDOM)   : 76.3% Hit Rate
Experimental  (LRU)      : 81.5% Hit Rate
Experimental  (LFU)      : 77.2% Hit Rate
Experimental  (W-TINYLFU): 87.5% Hit Rate
--------------------------------------------------
Control Group (RANDOM)   : Avg. 133.7 latency Cost
Experimental  (LRU)      : Avg. 113.9 latency Cost
Experimental  (LFU)      : Avg. 114.1 latency Cost
Experimental  (W-TINYLFU): Avg. 110.4 latency Cost
--------------------------------------------------
LFU beat RANDOM by:         +0.9% hit rate
LFU beat LRU by:            +-4.3% hit rate
W-TINYLFU beat LRU by:      +5.9% hit rate
W-TINYLFU beat LFU by:      +10.2% hit rate
--------------------------------------------------
==================================================
```

# Lessons Learned & Theoretical Findings

1. The New Item Slaughterhouse: Pure LFU instantly deletes newly viral items because they cannot immediately compete with historically viral "Zombie Data."

2. The Zipfian Fat Tail: Pure LRU fails under real internet traffic because the sheer volume of "long-tail" obscure requests constantly flushes valuable viral data from the cache.

3. The W-TinyLFU Synthesis: By routing all new traffic through an LRU window and only promoting items to the main LFU cache via a historical "Challenge," W-TinyLFU flawlessly absorbs botnet scrapers while permanently retaining highly requested items.