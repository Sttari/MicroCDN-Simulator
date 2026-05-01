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

        # LFU: Least Frequently Used, using a Hashmap to track payload frequency, a Hashmap of doublely linked hashmap for frequency to data
        # Also keep the min_freq for easy access
        elif strategy == "LFU":
            # Payload_id -> current frequency count
            self.payload_freq = {}
            # Frequency count -> OrderedDict(payload_id -> data)
            self.freq_map = defaultdict(OrderedDict)
            self.min_freq = 0

        # W-TinyLFU
        elif strategy == "W-TINYLFU":
            # 1. Allocate (20% Window, 80% Main)
            self.window_capacity = max(1, int(capacity * 0.2))
            self.main_capacity = capacity - self.window_capacity

            # 2. The 20% LRU
            self.window_lru = OrderedDict()

            #3. The 80% LFU
            self.main_payload_freq = {}
            self.main_freq_map = defaultdict(OrderedDict)

            # 4. Historical
            self.freq_sketch = defaultdict(int)
        
    
        
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
        
        elif self.strategy == "W-TINYLFU":
            # Alaways update frequency here
            self.freq_sketch[payload_id] += 1 

            # Case item in 20% LRU
            if payload_id in self.window_lru:
                self.window_lru.move_to_end(payload_id)
                return self.window_lru.get(payload_id)
            
            # Case item in 80% LFU
            if payload_id in self.main_payload_freq:
                freq = self.main_payload_freq[payload_id]
                data = self.main_freq_map[freq][payload_id]
            
                # Promote to next frequency bucket
                del self.main_freq_map[freq][payload_id]
                self.main_payload_freq[payload_id] = freq + 1
                self.main_freq_map[freq + 1][payload_id] = data
                return data

            # Otherwise not in the cache
            return None

    
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

        elif self.strategy == "W-TINYLFU":
            self.freq_sketch[payload_id] += 1

            # Case item in 20% LRU
            if payload_id in self.window_lru:
                self.window_lru.move_to_end(payload_id)
                self.window_lru[payload_id] = data
                return
            
            # Case item in 80% LFU
            if payload_id in self.main_payload_freq:
                self.get(payload_id)
                new_freq = self.main_payload_freq[payload_id]
                self.main_freq_map[new_freq][payload_id] = data
                return

            # New item
            self.window_lru[payload_id] = data

            # window full
            if len(self.window_lru) > self.window_capacity:
                out_id, out_data = self.window_lru.popitem(last=False)

                # Case main is empty
                if len(self.main_payload_freq) < self.main_capacity:
                    self._insert_to_main(out_id, out_data)
                else:
                    # Find low freq:
                    low_freq = min(self.main_payload_freq.values())
                    def_id, _ = next(iter(self.main_freq_map[low_freq].items()))

                    # Compare score
                    if self.freq_sketch[out_id] > self.freq_sketch[def_id]:
                        del self.main_freq_map[low_freq][def_id]
                        del self.main_payload_freq[def_id]
                        self._insert_to_main(out_id, out_data)
                    # Otherwise, no effect
            return
        
        elif self.strategy == "LRU":
            if payload_id in self.store:
                self.store.move_to_end(payload_id)
                self.store[payload_id] = data
                return

            if len(self.store) >= self.capacity:
                self.evict()
            
            self.store[payload_id] = data
            return

        elif self.strategy == "RANDOM":
            if payload_id in self.store:
                self.store[payload_id] = data
                return
            # Append to tracking array and record its index
            if len(self.store) >= self.capacity:
                self.evict()

            self.random_keys_list.append(payload_id)
            self.random_key_indices[payload_id] = len(self.random_keys_list) -1

            self.store[payload_id] = data
            return

    def evict(self):
        # Note : W-TinyLFU is handled by put() method, no need to add evict()
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

        
    # --- W-TINYLFU Helper ---
    def _insert_to_main(self, payload_id, data):
        """
        A Helper function to insert payload to main
        """
        freq = self.freq_sketch[payload_id]
        self.main_payload_freq[payload_id] = freq
        self.main_freq_map[freq][payload_id] = data
