"""Direct-mapped cache for employee records.

[CA&PP | Unit 4 - Memory Organization] Cache memory with DIRECT MAPPING:
    cache line = key mod number_of_lines
Two keys that map to the same line evict each other (conflict miss). Hits/misses are counted
so the hit ratio and the average access time can be calculated (see metrics.py).
"""
import threading

from metrics import hit_ratio


class DirectMappedCache:
    def __init__(self, lines=4):
        self.lines = lines
        self.table = [None] * lines          # each line holds (tag, value) or None
        self.hits = 0
        self.misses = 0
        self._lock = threading.Lock()

    def get(self, key, loader):
        """Return the value for key; on a miss call loader(key) (slow main-store access)."""
        line = key % self.lines                               # direct mapping
        with self._lock:
            entry = self.table[line]
            if entry is not None and entry[0] == key:         # tag match -> HIT
                self.hits += 1
                return entry[1]
            self.misses += 1                                  # MISS (cold or conflict)
        value = loader(key)                                   # fetch from main store
        with self._lock:
            self.table[line] = (key, value)                   # replace the line
        return value

    def ratio(self):
        return hit_ratio(self.hits, self.misses)
