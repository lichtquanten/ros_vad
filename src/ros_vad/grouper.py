import buffer

class Block(object):
    """Divides data into blocks of fixed length.

    Wrapper to BlockBuffer that tracks start, end time of blocks.
    Accepts timestamped input data. Produces timestamped blocks.
    """
    def __init__(self, block_size=None, block_buffer=None):
        if block_size is None and block_buffer is None:
            raise Exception('Must specify block_size or block_buffer')
        if block_buffer is not None:
            self._block_buffer = block_buffer
        elif block_size is not None:
            self._block_buffer = buffer.BlockBuffer(block_size)
        self._times = []
        self._last = None

    def __iter__(self):
        for block in self._block_buffer:
            if not self._last:
                self._last = self._times[0][1]
            l = len(block)
            while l > 0:
                if self._times[0][0] >= l:
                    t = self._len2time(l, *self._times[0])
                    end = self._times[0][1] + t
                    self._times[0][0] -= l
                    self._times[0][1] += t
                    l = 0
                else:
                    l -= self._times[0][0]
                    del self._times[0]

            yield (block, self._last, end)
            self._last = end

    @staticmethod
    def _len2time(segment_length, length, start, end):
        """
        Args:
            segment_length:
            length:
            start:
            end:
        """
        return (end - start) * float(segment_length) / length

    def put(self, data, start_time, end_time):
        """Add data to the buffer."""
        self._block_buffer.put(data)
        self._times.append([len(data), start_time, end_time])

class Neighborhood(object):
    def __init__(self, is_valid, length):
        self.is_valid = is_valid
        self.length = length
        self.buffer = []

    def __iter__(self):
        while len(self.buffer) > self.length:
          if self.is_valid([x['data'] for x in self.buffer[:self.length]]):
              for x in self.buffer:
                  if not x['handled']:
                      yield x['data'], True, x['start_time'], x['end_time']
                      x['handled'] = True
          else:
              if not self.buffer[0]['handled']:
                  yield x['data'], False, self.buffer[0]['start_time'], self.buffer[0]['end_time']
          del self.buffer[0]

    def put(self, data, start_time, end_time):
        self.buffer.append({
            'data': data,
            'start_time': start_time,
            'end_time': end_time,
            'handled': False
        })
