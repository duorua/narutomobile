class Counter:
    def __init__(self):
        self.counts = {}

    def increment(self, key, amount=1):
        if key in self.counts:
            self.counts[key] += amount
        else:
            self.counts[key] = amount

    def get_count(self, key):
        return self.counts.get(key, 0)

    def reset(self, key=None):
        if key is not None:
            if key in self.counts:
                del self.counts[key]
        else:
            self.counts.clear()


counter = Counter()
