import time
import collections

from collections import deque

BufferEntry = collections.namedtuple(
    'BufferEntry',
    'timestamp value callback_arg')

MAX_BATCH_SIZE_BYTES = 4194304
MAX_MESSAGES_PER_BATCH = 10000


class Buffer(object):

    def __init__(self):
        self._queue = deque()
        self._available_bytes = 0

    def put(self, value, callback_arg):
        # We need two extra bytes for the [ and ] wrapping the record.
        max_len = MAX_BATCH_SIZE_BYTES - 2

        if len(value) > max_len:
            raise ValueError(
                "Can't accept a record larger than {} bytes".format(max_len))

        self._queue.append(BufferEntry(timestamp=time.time()*1000,
                                       value=value,
                                       callback_arg=callback_arg))
        self._available_bytes += len(value.encode("utf8"))

    def take(self, batch_size_bytes, batch_delay_millis):
        if len(self._queue) == 0:
            return None

        t = time.time() * 1000
        t0 = self._queue[0].timestamp
        enough_bytes = self._available_bytes >= batch_size_bytes
        enough_messages = len(self._queue) >= MAX_MESSAGES_PER_BATCH
        enough_time = t - t0 >= batch_delay_millis
        ready = enough_bytes or enough_messages or enough_time

        if not ready:
            return None

        entries = []
        size = 2

        while (len(self._queue) > 0 and
               size + len(self._queue[0].value.encode("utf8")) <
               MAX_BATCH_SIZE_BYTES):
            entry = self._queue.popleft()

            # add one for the comma that will be needed to link entries
            # together
            entry_size = len(entry.value.encode("utf8"))
            size += entry_size + 1
            self._available_bytes -= entry_size
            entries.append(entry)

        return entries
