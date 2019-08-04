class BlockBuffer(object):
    """Divides items from an iterable into blocks.

    Accepts a list (or other iterable) of data. Adds each item from the list
    into a block of size `block_size`. The class is itself a generator and
    yields blocks.
    """

    def __init__(self, block_size):
        self._block_size = block_size
        self._buffer = []
        self.reset()

    def reset(self):
        """Resets the buffer"""
        self._buffer = []

    def put(self, data):
        """Appends data to the buffer"""
        self._buffer.extend(data)

    def __iter__(self):
        return self

    def next(self):
        """Extracts the next block in the buffer"""
        if self._block_size > len(self._buffer):
            raise StopIteration
        out = self._buffer[:self._block_size]
        self._buffer = self._buffer[self._block_size:]
        return out
