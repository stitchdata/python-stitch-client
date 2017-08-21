import time
import collections

from collections import deque

BufferEntry = collections.namedtuple(
    'BufferEntry',
    'timestamp value callback_arg')

MAX_BATCH_SIZE_BYTES = 4194304
MAX_MESSAGES_PER_BATCH = 8000


class Buffer(object):

    def __init__(self):
        self._queue = deque()

    def put(self, value, callback_arg):
        '''value is a nested dict / array structure'''
        # We need two extra bytes for the [ and ] wrapping the record.
        max_len = MAX_BATCH_SIZE_BYTES - 2

        if len(value) > max_len:
            raise ValueError(
                "Can't accept a record larger than {} bytes".format(max_len))

        self._queue.append(BufferEntry(timestamp=time.time()*1000,
                                       value=value,
                                       callback_arg=callback_arg))

    def take(self, batch_delay_millis):
        if len(self._queue) == 0:
            return None

        t = time.time() * 1000
        t0 = self._queue[0].timestamp
        enough_messages = len(self._queue) >= MAX_MESSAGES_PER_BATCH
        enough_time = t - t0 >= batch_delay_millis
        ready = enough_messages or enough_time

        if not ready:
            return None

        entries = []

        while len(self._queue) > 0:
            entries.append(self._queue.popleft())

        return entries
