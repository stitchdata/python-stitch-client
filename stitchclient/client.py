import os
import time
import logging
import collections

import urllib.request

from collections import deque
from io import StringIO
from transit.writer import Writer
from transit.reader import Reader

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE_BYTES = 4194304
DEFAULT_BATCH_DELAY_MILLIS = 60000
DEFAULT_STITCH_URL = 'https://api.stitchdata.com/v2/import/push'

BufferEntry = collections.namedtuple('BufferEntry', 'timestamp value callback_arg')

class Client(object):

    class Buffer(object):

        MAX_BATCH_SIZE_BYTES = 4194304
        MAX_MESSAGES_PER_BATCH = 10000

        _queue = deque()
        _available_bytes = 0

        def put(self, value, callback_arg):
            self._queue.append(BufferEntry(timestamp=time.time()*1000, value=value, callback_arg=callback_arg))
            self._available_bytes += len(value.encode("utf8"))

        def take(self, batch_size_bytes, batch_delay_millis):
            if len(self._queue) == 0:
                return None

            ready = self._available_bytes >= batch_size_bytes or \
                    len(self._queue) >= self.MAX_MESSAGES_PER_BATCH or \
                    time.time()*1000 - self._queue[0].timestamp >= batch_delay_millis

            if not ready:
                return None

            entries = []
            size = 2

            while len(self._queue) > 0 and \
                  size + len(self._queue[0].value.encode("utf8")) < self.MAX_BATCH_SIZE_BYTES:
                entry = self._queue.popleft()

                # add one for the comma that will be needed to link entries together
                entry_size = len(entry.value.encode("utf8"))
                size += entry_size + 1
                self._available_bytes -= entry_size
                entries.append(entry)

            return entries

    _buffer = Buffer()

    def __init__(self,
                 client_id,
                 token,
                 table_name=None,
                 key_names=None,
                 callback_function=None,
                 stitch_url=DEFAULT_STITCH_URL,
                 batch_size_bytes=DEFAULT_BATCH_SIZE_BYTES,
                 batch_delay_millis=DEFAULT_BATCH_DELAY_MILLIS):

        assert isinstance(client_id, int), 'client_id is not an integer: {}'.format(client_id)

        self.client_id = client_id
        self.token = token
        self.table_name = table_name
        self.key_names = key_names
        self.stitch_url = stitch_url
        self.batch_size_bytes = batch_size_bytes
        self.batch_delay_millis = batch_delay_millis
        self.callback_function = callback_function

    def push(self, message, callback_arg = None):
        """
        message must be a dict with at least these keys:
            action, table_name, key_names, sequence, data
        and optionally these keys:
            table_version
        """

        if message['action'] == 'upsert':
            message.setdefault('key_names', self.key_names)
        elif message['action'] == 'switch_view':
            pass
        else:
            raise ValueError('Message action property must be one of: "upsert", "switch_view"')

        message['client_id'] = self.client_id
        message.setdefault('table_name', self.table_name)

        with StringIO() as s:
            writer = Writer(s, "json")
            writer.write(message)
            self._buffer.put(s.getvalue(), callback_arg)

        batch = self._buffer.take(self.batch_size_bytes, self.batch_delay_millis)
        if batch is not None:
            self._send_batch(batch)

    def _serialize_entries(self, entries):
        deserialized_entries = []
        for entry in entries:
            reader = Reader("json")
            deserialized_entries.append(reader.read(StringIO(entry.value)))

        with StringIO() as s:
            writer = Writer(s, "json")
            writer.write(deserialized_entries)
            return s.getvalue()

    def _stitch_request(self, body):
        headers = {'Authorization': 'Bearer {}'.format(self.token),
                   'Content-Type': 'application/transit+json'}
        req = urllib.request.Request(self.stitch_url, body.encode("utf8"), headers)

        try:
            with urllib.request.urlopen(req) as response:
                return response
        except urllib.error.HTTPError as e:
            logger.error(e.read())
            raise e

    def _send_batch(self, batch):
        logger.debug("Sending batch of %s entries", len(batch))
        body = self._serialize_entries(batch)
        response = self._stitch_request(body)
        if response.status < 300:
            if self.callback_function is not None:
                self.callback_function([x.callback_arg for x in batch])
        else:
            raise RuntimeError("Error sending data to the Stitch API, with response status code {}".format(response.status))


    def flush(self):
        while True:
            batch = self._buffer.take(0,0)
            if batch is None:
                return

            self._send_batch(batch)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.flush()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    with Client(int(os.environ['STITCH_CLIENT_ID']), os.environ['STITCH_TOKEN'], callback_function=print) as c:
        for i in range(1,10):
            c.push({'action': 'upsert',
                    'table_name': 'test_table',
                    'key_names': ['id'],
                    'sequence': i,
                    'data': {'id': i, 'value': 'abc'}}, i)
