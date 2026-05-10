import threading


class Counter:
    def __init__(self):
        self.counts = {}
        self._lock = threading.Lock()

    def increment(self, key, amount=1):
        with self._lock:
            if key in self.counts:
                self.counts[key] += amount
            else:
                self.counts[key] = amount

    def get_count(self, key):
        with self._lock:
            return self.counts.get(key, 0)

    def reset(self, key=None):
        with self._lock:
            if key is not None:
                if key in self.counts:
                    del self.counts[key]
            else:
                self.counts.clear()


counter = Counter()
