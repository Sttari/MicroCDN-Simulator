# RFC-001: Byte-Bound Caching & Density-Based Eviction

**Author:** Staff CDN Engineering Team  
**Status:** Approved for Implementation  
**Component:** `CacheNode` Core Engine  

## 1. Background & Motivation
Currently, the Micro-CDN simulation uses a slot-based capacity model (e.g., `capacity=10`). This assumes all objects consume identical memory, which misrepresents physical network constraints. A 4K video consumes vastly more IOPS and RAM than a JSON payload. 

To accurately model memory pressure, we are deprecating slot-based capacity in favor of **Byte-Bound Caching**. Cache admittance and eviction will be strictly governed by `current_used_bytes` and `max_bytes`.

## 2. The Core Mechanic: Density-Based Scoring
When memory is bounded by bytes rather than item count, eviction decisions must maximize the "utility" of the limited RAM. We will introduce **Density-Based Scoring (Cost-Aware Caching)**.

**The Formula:**  
`Density Score = Historical Frequency / File Size (in MB)`

*Rationale:* A 5MB file accessed 10 times (Score: 2.0) is mathematically more valuable to the cache than a 500MB file accessed 50 times (Score: 0.1), because the massive file monopolizes space that could serve dozens of other highly-requested smaller files.

## 3. Impact on Existing Algorithms
Shifting to a byte-bound model fundamentally changes how our baseline algorithms operate:

### A. Pure LRU (Least Recently Used)
* **Mechanic:** Pure LRU is strictly temporal; it has no concept of frequency. Therefore, density scoring *does not apply* to pure LRU.
* **Execution:** If a new 500MB file arrives and the cache is full, LRU will simply enter a `while (current_bytes + 500MB > max_bytes)` loop. It will ruthlessly pop the oldest items off the tail of the queue, one by one, whether it takes 1 item or 100 items, until 500MB is freed.

### B. Pure LFU (Least Frequently Used)
* **Mechanic:** LFU will transition from sorting by raw `frequency` to sorting by `density_score`. 
* **Execution:** When memory is needed, LFU will evict the items with the lowest density score first. This naturally purges massive, infrequently accessed files (the "fat tail") while aggressively retaining tiny, highly-accessed files (e.g., website logos, manifests).

### C. W-TinyLFU (The Hybrid Challenge)
* **The Window (LRU):** Operates on standard LRU multi-eviction to free bytes.
* **The Arena (LFU):** Operates on Density-Based Scoring.
* **The Challenge Logic (Asymmetric Combat):** When a 500MB file drops out of the Window, it needs 500MB of space in the Main Arena. It identifies a "cohort" of the lowest-density items in the Arena whose combined size is $\ge 500MB$. 
* The Challenger's Density Score is compared against the *average Density Score* of the defending cohort. If the Challenger wins, the entire cohort is evicted.

## 4. System Invariants & Admittance Policies
To prevent system crashes and infinite loops, the following invariants must be strictly enforced in the new implementation:
1. **The Object Limit:** If `file_size > max_bytes`, the object is automatically flagged as `UNCACHEABLE`. It is served to the client via direct passthrough but bypasses the cache entirely.
2. **Atomic Eviction:** An eviction loop must complete entirely before the new item is admitted. If a challenge fails halfway, the state must rollback (or fail fast).
3. **Data Model Update:** The `video_library` must be converted from a `List[str]` to a `Dict[str, int]` mapping `payload_id` -> `size_in_bytes`.

## 5. Telemetry Updates
Evaluating algorithms purely on "Request Hit Rate" is no longer sufficient. An algorithm that caches 1,000 tiny images but misses on 10 massive 4K videos might have a 99% Request Hit Rate but cost the company millions in egress bandwidth.
* **New Metric:** `Byte Hit Rate (%)` = `(Total Bytes Served from Cache) / (Total Bytes Requested by Clients)`
* *Success Criteria:* W-TinyLFU must demonstrate superior performance in both Request Hit Rate *and* Byte Hit Rate.