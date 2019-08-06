class BlockArrLike(object):
    """Divides data in an array-like object into fixed length blocks.

    To use with Python lists, give [] as the `buffer` argument and operator.add
    as the `concatenate` argument of the constructor. Pass in lists for the
    `data` argument of `put`.

    To use with numpy arrays, give np.array([]) as the `buffer` argument
    and `np.append` as the `concatenate` argument of the constructor. Pass in
    numpy arrays for the `data` argument of `put`.
    """
    def __init__(self, block_size, buffer, concatenate):
        """
        Parameters
        ----------
        block_size : int
            The length of each block.
        buffer : array-like
            A buffer to which data input via `put` will be added using `concatenate`.
            The buffer must be empty.
        concatenate : callable
            Accepts two parameters, `buffer` and `data`. Returns a new buffer
            containing both `buffer` and `data`. `uffer` is of the type given
            in the `buffer` parameter. `data` is of the type given in calls to
            `put`.
        """
        self._block_size = block_size
        self._buffer = buffer
        self._concatenate = concatenate

        self._times = []
        self._output_buffer = []
        self._prev_end_time = None

    def __iter__(self):
        return self

    def next(self):
        if not self._output_buffer:
            raise StopIteration
        return self._output_buffer.pop(0)

    def _get_start_time(self):
        return self._times[0]['start_time']

    def _get_end_time(self, block_length):
        # Skip until the time window in which the block ends
        while block_length > self._times[0]['length']:
            block_length -= self._times[0]['length']
            del self._times[0]

        diff = self._times[0]['end_time'] - self._times[0]['start_time']
        proportion = float(block_length) / self._times[0]['length']
        self._times[0]['start_time'] += diff * proportion
        self._times[0]['length'] -= block_length
        return self._times[0]['start_time']

    def put(self, data, start_time, end_time):
        """
        Parameters
        ----------
        data : array-like
            An array-like containing individual datum.
        start_time : implements __add__, __sub__, __mul__, __div__
            The start time associated with `data`.
        end_time : implements __add__, __sub__, __mul__, __div__
            The end time associatd with `data`.
        """
        self._buffer = self._concatenate(self._buffer, data)
        self._times.append({
            'length': len(data),
            'start_time': start_time,
            'end_time': end_time
        })
        while len(self._buffer) >= self._block_size:
            block = self._buffer[:self._block_size]
            blk_start_time = self._get_start_time()
            blk_end_time = self._get_end_time(len(block))
            self._output_buffer.append((block, blk_start_time, blk_end_time))
            self._buffer = self._buffer[self._block_size:]

class Neighborhood(object):
    """Determine is there is a valid group of contiguous data around some datum.

    Each datum is considered party to neighborhoods of data. A neighborhood
    of data is some successively input (via the `put` method) data. Each datum,
    except for the first `length` - 1 data, are party to `length` neighborhoods
    of length `length`.

    This class determines if any of the neighborhoods of some fixed length
    to which a datum is party is valid. To determine validity, each neighborhood
    is passed to the provided `is_valid` function. Note that validity does not
    suggest properly formatted but rather something more abstract.

    If a datum is found to be an a valid neighborhood, this information is made
    immediately available. The class will not wait to evaluate every neighborhood
    to which the datum is party.
    """
    def __init__(self, is_valid, length):
        """
        Parameters
        ---------
        is_valid : callable
            A function that accepts a list of data and returns a bool.
        length : int
            The length to use when forming neighborhoods.
        """
        self._is_valid = is_valid
        self._length = length
        self._buffer = []
        self._output_buffer = []

    def __iter__(self):
        return self

    def next(self):
        """
        Returns
        -------
        any
            A datum.
        bool
            True if the datum with the following start, end times is in a valid
            neighborhood, False otherwise.
        any
            The start time of the datum.
        any
            The end time of the datum.

        Raises
        ------
        StopIteration
            When there are no more processed datum.
        """
        if not self._output_buffer:
            raise StopIteration
        return self._output_buffer.pop(0)

    def put(self, datum, start_time, end_time):
        """Add `datum` to the buffer. Evalute the neighborhoods it is party to.

        Parameters
        ----------
        datum: any
            Anything.
        start_time : any
            The start time associated with `datum`.
        end_time : any
            The end time associated with `datum`.
        """
        self._buffer.append({
            'datum': datum,
            'start_time': start_time,
            'end_time': end_time,
            'handled': False
        })
        # Check if the buffer contains a full neighborhood
        if len(self._buffer) == self._length:
            nbhd = [x['datum'] for x in self._buffer]
            if self._is_valid(nbhd):
                # Handle all unhandled data in valid neighborhood
                for x in self._buffer:
                    if not x['handled']:
                        self._output_buffer.append(
                            (x['datum'], True, x['start_time'], x['end_time']))
                        x['handled'] = True
            # Remove the first datum from the buffer
            # All of its neighborhoods have been evaluated
            first = self._buffer.pop(0)
            # Output as invalid if not yet handled
            if not first['handled']:
                self._output_buffer.append(
                    (x['datum'], False, first['start_time'], first['end_time']))
