import collections
from io import StringIO
import os
import time

import requests
from transit.writer import Writer


DEFAULT_MAX_BATCH_SIZE_BYTES = 4194304
DEFAULT_BATCH_DELAY_SECONDS = 60.0
MAX_MESSAGES_PER_BATCH = 20000
DEFAULT_STITCH_URL = 'https://api.stitchdata.com/v2/import/push'
EU_STITCH_URL = 'https://api.eu-central-1.stitchdata.com/v2/import/push'


class MessageTooLargeException(Exception):
    pass


def encode_transit(records):
    '''Returns the records serialized as Transit/json in utf8'''
    with StringIO() as buf:
        writer = Writer(buf, "json")
        writer.write(records)
        return buf.getvalue().encode('utf8')


def partition_batch(entries, max_batch_size_bytes):
    start = 0
    end = len(entries)
    result = []
    while start < end:
        partitioned_entries = entries[start : end]
        records = [e.value for e in partitioned_entries]
        encoded = encode_transit(records)

        if len(encoded) <= max_batch_size_bytes:
            result.append((encoded, [e.callback_arg for e in partitioned_entries]))

            # If end is less than length of entries we're not done yet.
            # Advance start to end, and advance end by the number of
            # records we just put in the batch.
            if end < len(entries):
                start = end
                end = min(end + len(records), len(entries))

            # If end is at the end of the input entries, we're done.
            else:
                break

        # The size of the encoded records in our range is too large. If we
        # have more than one record in our range, cut the range in half
        # and try again.
        elif end - start > 1:
            end = start + (end - start) // 2

        else:
            raise MessageTooLargeException(
                ('A single message is larger then the maximum batch size. '
                 'Message size: {}. Max batch size: {}')
                .format(len(encoded), max_batch_size_bytes))

    return result


BufferEntry = collections.namedtuple(
    'BufferEntry',
    ['value', 'callback_arg'],
)


BatchStatsEntry = collections.namedtuple(
    'BatchStatsEntry',
    ['num_records', 'num_bytes'],
)


class Client(object):
    def __init__(
            self,
            client_id,
            token,
            region="us",
            table_name=None,
            key_names=None,
            callback_function=None,
            override_stitch_url=None,
            max_batch_size_bytes=DEFAULT_MAX_BATCH_SIZE_BYTES,
            batch_delay_seconds=DEFAULT_BATCH_DELAY_SECONDS):

        try:
            self.client_id = int(client_id)
        except:
            raise ValueError("client_id must be an integer: %s.".format(client_id))

        if not token:
            raise ValueError("token is null")

        self.token = token
        self.max_messages_per_batch = MAX_MESSAGES_PER_BATCH
        self.table_name = table_name
        self.key_names = key_names
        self.max_batch_size_bytes = max_batch_size_bytes
        self.batch_delay_seconds = batch_delay_seconds
        self.callback_function = callback_function

        self._buffer = []

        # Stats we update as we send records
        self.time_last_batch_sent = time.time()
        self.batch_stats = collections.deque(maxlen=100)

        # We'll try using a big batch size to start out
        self.target_messages_per_batch = self.max_messages_per_batch

        if override_stitch_url:
            self.stitch_url = override_stitch_url
        elif region.lower() == "us":
            self.stitch_url = DEFAULT_STITCH_URL
        elif region.lower() == "eu":
            self.stitch_url = EU_STITCH_URL
        else:
            raise ValueError(
                "Invalid region selected: %s. "
                "Options are 'us' and 'eu' or set the override_stitch_url."
                .format(region)
            )

    def _add_message(self, message, callback_arg):
        self._buffer.append(BufferEntry(value=message, callback_arg=callback_arg))

    def moving_average_bytes_per_record(self):
        num_records = 0
        num_bytes = 0
        for stats in self.batch_stats:
            num_records += stats.num_records
            num_bytes += stats.num_bytes

        return num_bytes // num_records

    def push(self, message, callback_arg=None):
        """message should be a dict recognized by the Stitch Import API.

        See https://www.stitchdata.com/docs/integrations/import-api.
        """

        if message['action'] == 'upsert':
            message.setdefault('key_names', self.key_names)

        message['client_id'] = self.client_id
        message.setdefault('table_name', self.table_name)

        self._add_message(message, callback_arg)

        batch = self._take_batch(self.target_messages_per_batch)
        if batch:
            self._send_batch(batch)

    def _take_batch(self, min_records):
        '''If we have enough data to build a batch, returns all the data in the
        buffer and then clears the buffer.'''

        if not self._buffer:
            return []

        enough_messages = len(self._buffer) >= min_records
        enough_time = time.time() - self.time_last_batch_sent >= self.batch_delay_seconds
        ready = enough_messages or enough_time

        if not ready:
            return []

        result = list(self._buffer)
        self._buffer.clear()
        return result

    def _send_batch(self, batch):
        for body, callback_args in partition_batch(batch, self.max_batch_size_bytes):
            self._send(body, callback_args)

        try:
            moving_average = self.moving_average_bytes_per_record()
            self.target_messages_per_batch = \
                min(self.max_messages_per_batch,
                    0.8 * (self.max_batch_size_bytes / moving_average))
        except ZeroDivisionError:
            # Handle the case where there are no records
            pass

    def _stitch_request(self, body):
        headers = {
            'Authorization': 'Bearer {}'.format(self.token),
            'Content-Type': 'application/transit+json',
        }
        return requests.post(self.stitch_url, headers=headers, data=body)

    def _send(self, body, callback_args):
        response = self._stitch_request(body)

        if response.status_code < 300:
            if self.callback_function is not None:
                self.callback_function(callback_args)
        else:
            raise RuntimeError(
                "Error sending data to the Stitch API. {0.status_code} - {0.content}"
                .format(response))
        self.time_last_batch_sent = time.time()
        self.batch_stats.append(BatchStatsEntry(len(callback_args), len(body)))

    def flush(self):
        batch = self._take_batch(0)
        self._send_batch(batch)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.flush()


if __name__ == "__main__":
    with Client(
            os.environ.get('STITCH_CLIENT_ID'),
            os.environ.get('STITCH_TOKEN'),
            os.environ.get('STITCH_REGION'),
            callback_function=print,
    ) as client:
        for i in range(1, 10):
            client.push({
                'action': 'upsert',
                'table_name': 'test_table',
                'key_names': ['id'],
                'sequence': i,
                'data': {
                    'id': i,
                    'value': 'abc',
                },
            }, i)
