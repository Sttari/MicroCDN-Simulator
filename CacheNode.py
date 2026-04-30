import random
from collections import OrderedDict

class CacheNode:
    def __init__(self, capacity = 5, strategy = "LRU"):
        self.capacity = capacity
        self.strategy = strategy
    
        # LRU: Least Recently Used, a double linked hashmap
        if strategy == "LRU":
            self.store = OrderedDict()
        else:
            self.store = {}
            # We need an array for O(1) random picking
            self.random_keys_list = []
            # We need to track where each key lives in the array
            self.random_key_indices = {}
        
    def get(self, payload_id):
        if payload_id in self.store:
            if self.strategy == "LRU":
                # Move the item to the end (Most Recently Used)
                self.store.move_to_end(payload_id)
            return self.store[payload_id]
        return None
    
    def put(self, payload_id, data):
        # if it is alrady there, make as MRU
        if payload_id in self.store:
            if self.strategy == "LRU":
                self.store.move_to_end(payload_id)
            self.store[payload_id] = data
            return
        
        # if Capacity is reached, we MUST evict
        if len(self.store) >= self.capacity:
            self.evict()
        
        self.store[payload_id] = data
        
        if self.strategy == "RANDOM":
            # Append to tracking array and record its index
            self.random_keys_list.append(payload_id)
            self.random_key_indices[payload_id] = len(self.random_keys_list) -1
    
    def evict(self):
        if self.strategy == "LRU":
            self.store.popitem(last=False)

        elif self.strategy == "RANDOM":
            # Pick an random element in O(1) time
            random_idx = random.randint(0, len(self.random_keys_list) - 1)
            key_to_evict = self.random_keys_list[random_idx]

            # Swap the evict key with the last key
            last_key = self.random_keys_list[-1]
            self.random_keys_list[random_idx] = last_key
            self.random_key_indices[last_key] = random_idx

            # Pop the last element from the array in O(1) time
            self.random_keys_list.pop()
            
            # Clean up the dictionaries
            del self.random_key_indices[key_to_evict]
            del self.store[key_to_evict]