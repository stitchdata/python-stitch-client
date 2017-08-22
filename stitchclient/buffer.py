import time
import collections

from collections import deque
from io import StringIO
from transit.writer import Writer

BufferEntry = collections.namedtuple(
    'BufferEntry',
    'timestamp value callback_arg')

MAX_BATCH_SIZE_BYTES = 4194304
MAX_MESSAGES_PER_BATCH = 10000


def encode_transit(records):
    '''Returns the records serialized as Transit/json in utf8'''
    with StringIO() as s:
        writer = Writer(s, "json")
        writer.write(records)
        return s.getvalue().encode('utf8')

class Buffer(object):

    def __init__(self):
        self._queue = []

    def put(self, value, callback_arg):
        '''value is a nested dict / array structure'''
        self._queue.append(BufferEntry(timestamp=time.time()*1000,
                                       value=value,
                                       callback_arg=callback_arg))

    def take(self, batch_delay_millis, force_flush=False):
        '''If we have enough data to build a batch, returns it as a
        transit-encoded array of records'''
        
        if len(self._queue) == 0:
            return []

        t = time.time() * 1000
        t0 = self._queue[0].timestamp
        enough_messages = len(self._queue) >= MAX_MESSAGES_PER_BATCH
        enough_time = t - t0 >= batch_delay_millis
        ready = enough_messages or enough_time or force_flush

        if not ready:
            return []

        start = 0
        end = len(self.entries)
        bad_record = None

        while start < end:
            records = [rec.value for rec in self.entries[start : end]]
            encoded = encode_transit(records)
            if len(encoded) < MAX_BATCH_SIZE_BYTES:
                yield encoded
                if end < len(self.entries):
                    start = end
                    end = min(end + len(records), len(entries))
                else:
                    self.entries = []
                    return
            else:
                end = start + (end - start) / 2            

        raise ValueError('Too big')        
