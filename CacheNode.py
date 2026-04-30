import random
from collections import OrderedDict, defaultdict

class CacheNode:
    def __init__(self, capacity = 5, strategy = "LRU"):
        self.capacity = capacity
        self.strategy = strategy
    
        # LRU: Least Recently Used, a double linked hashmap
        if strategy == "LRU":
            self.store = OrderedDict()

        elif strategy == "RANDOM":
            self.store = {}
            # We need an array for O(1) random picking
            self.random_keys_list = []
            # We need to track where each key lives in the array
            self.random_key_indices = {}

        elif strategy == "LFU":
            # Payload_id -> current frequency count
            self.payload_freq = {}
            # Frequency count -> OrderedDict(payload_id -> data)
            self.freq_map = defaultdict(OrderedDict)
            self.min_freq = 0
        
    def get(self, payload_id):
        if self.strategy == "LRU":
            if payload_id in self.store:
                # Move the item to the end (Most Recently Used)
                self.store.move_to_end(payload_id)
            return self.store.get(payload_id)
        
        elif self.strategy == "RANDOM":
            return self.store.get(payload_id) 
        
        elif self.strategy == "LFU":
            if payload_id not in self.payload_freq:
                return None
            
            # Get current frequency and data
            freq = self.payload_freq[payload_id]
            data = self.freq_map[freq][payload_id]

            # Remove from current frequency bucket
            del self.freq_map[freq][payload_id]
 
            # If bucket is now empty and its the minimum, increment min_freq
            if not self.freq_map[freq] and self.min_freq == freq:
                self.min_freq += 1
            
            # Promte to the next freq bucket
            self.payload_freq[payload_id] = freq + 1
            self.freq_map[freq + 1][payload_id] = data

            return data
    
    def put(self, payload_id, data):
        # LFU strategy
        if self.strategy == "LFU":
            if payload_id in self.payload_freq:
                # if exists, call get () to trigger the frequency increment
                self.get(payload_id)
                new_freq = self.payload_freq[payload_id]
                self.freq_map[new_freq][payload_id] = data
                return
            
            if len(self.payload_freq) >= self.capacity:
                self.evict()

            # Otherwise insert brand new item with freq 1
            self.payload_freq[payload_id] = 1
            self.freq_map[1][payload_id] = data
            self.min_freq = 1
            return
        
        # LRU/Random strategy
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
        
        elif self.strategy == "LFU":
            # Pop the item with the least frequency that is least used
            # Note: we only call evict in put method, no need to set the min_freq here
            key_to_evict, _ = self.freq_map[self.min_freq].popitem(last=False)
            del self.payload_freq[key_to_evict]