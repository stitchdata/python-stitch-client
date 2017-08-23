import collections
from io import StringIO
import logging
import os
import requests
import time

from transit.writer import Writer

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE_BYTES = 4194304
DEFAULT_BATCH_DELAY_SECONDS = 60.0
MAX_MESSAGES_PER_BATCH = 10000
DEFAULT_STITCH_URL = 'https://api.stitchdata.com/v2/import/push'

def encode_transit(records):
    '''Returns the records serialized as Transit/json in utf8'''
    with StringIO() as s:
        writer = Writer(s, "json")
        writer.write(records)
        return s.getvalue().encode('utf8')

def partition_batch(entries):
    '''yields one [transit_encoded_records, callback_args] for each partition'''
    start = 0
    end = len(entries)

    while start < end:
        partitioned_entries = entries[start : end]
        records = [e.value for e in partitioned_entries]
        encoded = encode_transit(records)
        if len(encoded) < MAX_BATCH_SIZE_BYTES:
            yield (encoded, [e.callback_arg for e in partitioned_entries])

            # If end is less than length of entries we're not done yet.
            # Advance start to end, and advance end by the number of
            # records we just put in the batch.
            if end < len(entries):
                start = end
                end = min(end + len(records), len(entries))

            # If end is at the end of the input entries, we're done.
            else:                
                return

        # The size of the encoded records is too large. Cut the size of
        # the partition in half and try again.
        else:
            end = start + (end - start) / 2

    raise ValueError('Too big')

BufferEntry = collections.namedtuple(
    'BufferEntry',
    ['value', 'callback_arg'])

class Client(object):

    def __init__(self,
                 client_id,
                 token,
                 table_name=None,
                 key_names=None,
                 callback_function=None,
                 stitch_url=DEFAULT_STITCH_URL,
                 batch_size_bytes=DEFAULT_BATCH_SIZE_BYTES,
                 batch_delay_millis=DEFAULT_BATCH_DELAY_SECONDS):

        assert isinstance(client_id, int), 'client_id is not an integer: {}'.format(client_id)  # nopep8

        self.max_records_per_batch = MAX_MESSAGES_PER_BATCH
        self.client_id = client_id
        self.token = token
        self.table_name = table_name
        self.key_names = key_names
        self.stitch_url = stitch_url
        self.batch_size_bytes = batch_size_bytes
        self.batch_delay_millis = batch_delay_millis
        self.callback_function = callback_function
        self.time_last_batch_sent = time.time()        
        self._buffer = []


    def _add_message(self, message, callback_arg):
        self._buffer.append(BufferEntry(value=message,
                                        callback_arg=callback_arg))        
        
    def push(self, message, callback_arg=None):
        """message should be a dict recognized by the Stitch Import API.

        See https://www.stitchdata.com/docs/integrations/import-api.
        """

        if message['action'] == 'upsert':
            message.setdefault('key_names', self.key_names)

        message['client_id'] = self.client_id
        message.setdefault('table_name', self.table_name)

        self.add_message(message, callback_arg)
        
        batch = self._take_batch(self.max_records_per_batch)
        for body, callback_args in partition_batch(batch):
            self._send_batch(body, callback_args)


    def _take_batch(self, min_records):
        '''If we have enough data to build a batch, returns all the data in the
        buffer and then clears the buffer.'''

        if len(self._buffer) == 0:
            return []

        t = time.time()
        enough_messages = len(self._buffer) >= min_records
        enough_time = t - self.time_last_batch_sent >= self.batch_delay_millis
        ready = enough_messages or enough_time

        if not ready:
            return []

        result = list(self._buffer)
        self._buffer.clear()
        return result
            

    def _stitch_request(self, body):
        headers = {'Authorization': 'Bearer {}'.format(self.token),
                   'Content-Type': 'application/transit+json'}
        print('Headers is ' + str(headers))
        print('Data is' + body[:1000])
        return requests.post(self.stitch_url, headers=headers, data=body)

    def _send_batch(self, body, callback_args):
        logger.debug("Sending batch of %d entries, %d bytes", len(callback_args), len(body))
        response = self._stitch_request(body)

        if response.status_code < 300:
            if self.callback_function is not None:
                self.callback_function(callback_args)
        else:
            raise RuntimeError("Error sending data to the Stitch API. {0.status_code} - {0.content}"  # nopep8
                               .format(response))
        self.time_last_batch_sent = time.time()

    def flush(self):
        for body, callback_args in partition_batch(self._take_batch(0)):
            self._send_batch(body, callback_args)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.flush()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    with Client(int(os.environ['STITCH_CLIENT_ID']),
                os.environ['STITCH_TOKEN'],
                callback_function=print) as c:
        for i in range(1, 10):
            c.push({'action': 'upsert',
                    'table_name': 'test_table',
                    'key_names': ['id'],
                    'sequence': i,
                    'data': {'id': i, 'value': 'abc'}}, i)
