from cache.cacheByte import RandomCache, LRUCache, LFUCache

class CacheNode:
    def __init__(self, max_bytes = 5_000_000, strategy = "LRU"):
        self.capacity = max_bytes
        self.strategy = strategy
    
        if strategy == "LRU":
            self.cache = LRUCache(max_bytes)

        elif strategy == "RANDOM":
            self.cache = RandomCache(max_bytes)

        elif strategy == "LFU":
            self.cache = LFUCache(max_bytes)

    def get(self, payload_id):
       return self.cache.get(payload_id)

    
    def put(self, payload_id, data, size):
        return self.cache.put(payload_id, data, size)

    def evict(self):
        self.cache.evict()