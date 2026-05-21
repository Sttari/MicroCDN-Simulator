import heapq
from collections import defaultdict, OrderedDict

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
        if key not in self.map and isinstance(self.map, defaultdict):
            heapq.heappush(self.heap, key)
        return self.map.get(key)
    
    def __delitem__(self, key):
        # Using Lazy deletion: 
        # keep item still in heap for faster deletion
        if key in self.map:
            del self.map[key]
    
    def popitem(self):
        while self.heap and self.heap[0] not in self.map:
            heapq.heappop(self.heap)
        
        if not self.heap:
            raise KeyError("pop from empty Heapdict")
        
        min_key = heapq.heappop(self.heap)
        value = self.hash_map.pop(min_key)
        return min_key, value
    
    def gettop(self):
        return self.heap[0]