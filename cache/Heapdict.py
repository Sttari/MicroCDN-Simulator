from collections import defaultdict
import heapq
 
class Heapdict:
    def __init__(self, default_type = None):
        if default_type is not None:
            self.map = defaultdict(default_type)
        else: 
            self.map = {}
        self.heap = []

    def __setitem__(self, key, value):
        # Enable map[1] = a
        # Key has to be numerical
        if key not in self.map:
            heapq.heappush(self.heap, key)
        self.map[key] = value 

    def __getitem__(self, key):
        is_new = key not in self.map
        if is_new and isinstance(self.map, defaultdict):
            heapq.heappush(self.heap, key)
        return self.map[key]
    
    def __delitem__(self, key):
        # Using Lazy deletion: 
        # keep item still in heap for faster deletion
        if key in self.map:
            del self.map[key]
    
    def __contains__(self, key):
        return key in self.map
    
    def _purge_stale(self):
        while self.heap and self.heap[0] not in self.map:
            heapq.heappop(self.heap)

    def popitem(self):
        self._purge_stale()
        if not self.heap:
            raise KeyError("pop from empty Heapdict")
        
        min_key = heapq.heappop(self.heap)
        value = self.hash_map.pop(min_key)
        return min_key, value
    
    def gettop(self):
        self._purge_stale()
        return self.heap[0]