import random
from collections import OrderedDict
from .Heapdict import Heapdict


class RandomCache:
    def __init__(self, max_bytes = 5_000_000):
        # Cache Node uses random strategy
        self.max_bytes = max_bytes
        self.curr_bytes = 0
        # Payload_id -> {data, size, idx}
        self.store = {}
        # An array for O(1) random picking payload_id
        self.random_keys_list = []

    def get(self, payload_id):
        if self.store.get(payload_id):
            return self.store.get(payload_id).get("data") 
        return None
    
    def put(self, payload_id, data, size):
        if size > self.max_bytes:
            return None
        # For new design, we would assume payload_id, data and size are fixed
        if payload_id not in self.store:
            while self.curr_bytes + size > self.max_bytes :
                self.evict()
            
            self.random_keys_list.append(payload_id)
            self.curr_bytes += size

            self.store[payload_id] = {
                "data": data, 
                "size": size, 
                "idx": len(self.random_keys_list) -1
            }
        return None

    def evict(self):
        # Pick an random element in O(1) time
        random_idx = random.randint(0, len(self.random_keys_list) - 1)
        key_to_evict = self.random_keys_list[random_idx]
        self.curr_bytes -= self.store[key_to_evict]["size"]

        # Swap the evict key with the last key
        last_key = self.random_keys_list[-1]
        self.random_keys_list[random_idx] = last_key
        self.store[last_key]["idx"] = random_idx

        # Pop the last element from the array in O(1) time
        self.random_keys_list.pop()

        # Clean up the dictionaries
        del self.store[key_to_evict]

class LRUCache:
    def __init__(self, max_bytes = 5_000_000):
        # Cache Node uses LRU strategy
        self.max_bytes = max_bytes
        self.curr_bytes = 0

        # LRU: Least Recently Used, a double linked hashmap
        self.store = OrderedDict()
    
    def get(self, payload_id):
        if payload_id in self.store:
            self.store.move_to_end(payload_id)
            return self.store[payload_id]["data"]
        return None

    def put(self, payload_id, data, size):
        if size > self.max_bytes:
            return None
        # Again, we assume payload_id, data, size are fixed
        if payload_id not in self.store:
            while self.curr_bytes + size > self.max_bytes:
                self.evict()
            self.store[payload_id] = {
                "data": data,
                "size": size
            }
            self.curr_bytes += size
        else:
            self.store.move_to_end(payload_id)
        return None

    def evict(self):
        _, value = self.store.popitem(last=False)
        self.curr_bytes -= value.get("size")

class LFUCache:
    def __init__(self, max_bytes = 5_000_000):
        # Cache Node uses random strategy
        self.max_bytes = max_bytes
        self.curr_bytes = 0
        self.store = {}
        self.density_score_map = Heapdict(OrderedDict)
    
    def get(self, payload_id):
        if payload_id in self.store:
            score = self.store[payload_id]["freq"] / self.store[payload_id]["size"]

            self.store[payload_id]["freq"] += 1

            del self.density_score_map[score][payload_id]
            
            if not self.density_score_map[score]:
                del self.density_score_map[score]

            score = self.store[payload_id]["freq"] / self.store[payload_id]["size"]
            self.density_score_map[score][payload_id] = self.store[payload_id]["freq"]

            return self.store[payload_id]["data"]
        return None


    def put(self, payload_id, data, size):
        if size > self.max_bytes:
            return None
        # Again, we assume id, data, size is fixed tuple
        if payload_id in self.store:
            self.get(payload_id)
            return
        else:
            while self.curr_bytes + size > self.max_bytes:
                self.evict()

            self.store[payload_id] = {
                "data": data,
                "size": size,
                "freq": 1
            }
            self.curr_bytes += size
            score = 1 / size 
            self.density_score_map[score][payload_id] = 1
            return


    def evict(self):
        min_score = self.density_score_map.gettop()
        key_to_evict, _ = self.density_score_map[min_score].popitem(last=False)
        if not self.density_score_map[min_score]:
            del self.density_score_map[min_score]
        self.curr_bytes -= self.store[key_to_evict]["size"]
        del self.store[key_to_evict]

