import time
import collections
from collections import deque

BufferEntry = collections.namedtuple(
    'BufferEntry',
    'timestamp value callback_arg')

class Buffer(object):

    def __init__(self):
        self._queue = []

    def put(self, value, callback_arg):
        '''value is a nested dict / array structure'''
        self._queue.append(BufferEntry(timestamp=time.time()*1000,
                                       value=value,
                                       callback_arg=callback_arg))

    def take(self, batch_delay_millis, min_records):
        '''If we have enough data to build a batch, returns it as a
        transit-encoded array of records'''

        if len(self._queue) == 0:
            return []

        t = time.time() * 1000
        t0 = self._queue[0].timestamp
        enough_messages = len(self._queue) >= min_records
        enough_time = t - t0 >= batch_delay_millis
        ready = enough_messages or enough_time

        if not ready:
            return []

        result = list(self._queue)
        self._queue.clear()
        return result
