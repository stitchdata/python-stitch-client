import unittest
from unittest.mock import MagicMock
import collections
import time

import stitchclient.client
from stitchclient.client import BufferEntry, Client

class TestTargetStitch(unittest.TestCase):

    client_id = 1
    token = 'asdf'
    table_name = 'users'
    key_names = ['id']

    def test_push(self):
        pass
        # client = stitchclient.Client(
        #     client_id=client_id,
        #     token=token,
        #     table_name=table_name,
        #     key_names=key_names,
        #     batch_size_bytes=1000,
        #     batch_delay_millis=100000)


tiny_record = 'apple'
big_record  = 'a' * 1500000
huge_record = 'a' * 5000000

class TestBuffer(unittest.TestCase):

    buffer = None

    def setUp(self):
        self.client = Client(123, 'abc', batch_delay_seconds=1000000)
        
    def test_push_and_force_take(self):
        self.client._add_message(tiny_record, 1)
        self.client._add_message(tiny_record, 2)
        self.assertEqual(self.client._take_batch(0),
                         [(tiny_record, 1),
                          (tiny_record, 2)])

    def test_take_respects_min_records(self):
        min_records = 2
        self.client._add_message(tiny_record, 1)
        self.assertEqual(self.client._take_batch(min_records),
                         [])
        self.client._add_message(tiny_record, 2)
        self.assertEqual(self.client._take_batch(min_records),
                         [(tiny_record, 1),
                          (tiny_record, 2)])

    def test_take_is_empty_after_take(self):
        self.client._add_message(tiny_record, 1)
        self.client._add_message(tiny_record, 2)
        self.assertEqual(2, len(self.client._take_batch(0)))
        self.assertEqual(0, len(self.client._take_batch(0)))        

    def test_trigger_batch_at_10k_messages(self):
        self.client._add_message(tiny_record, None)
        
        put = lambda: self.client._add_message(tiny_record, None)
        take = lambda: self.client._take_batch(60000)
        
        for i in range(9999):
            put()
            
        self.assertEqual(list(take()), [])
        put()
        self.assertIsNotNone(take())        


class TestPartitionBatch(unittest.TestCase):

    def test_cant_use_larger_than_max_message_size(self):
        with self.assertRaises(stitchclient.client.MessageTooLargeException):
            entry = BufferEntry('a record that is far too long', None)
            stitchclient.client.partition_batch([entry], 10)

    def test_get_single_record(self):
        entry = BufferEntry('a', None)
        partitioned = stitchclient.client.partition_batch([entry], 10)
        self.assertEqual(partitioned, [(b'["a"]', [None])])

    def test_get_multiple_records(self):
        entry_a = BufferEntry('a', 1)
        entry_b = BufferEntry('b', 2)
        partitioned = stitchclient.client.partition_batch([entry_a, entry_b], 10)
        self.assertEqual(partitioned, [(b'["a","b"]', [1, 2])])

    def test_get_multiple_records_split(self):
        entry_a = BufferEntry('a', 1)
        entry_b = BufferEntry('b', 2)
        partitioned = stitchclient.client.partition_batch([entry_a, entry_b], 6)
        self.assertEqual(partitioned, [(b'["a"]', [1]),
                                       (b'["b"]', [2])])

    def test_get_many_records(self):
        letters = 'abcdefghijklmnopqrstuvwxyz'
        entries = [BufferEntry(x, None) for x in letters]
        partitioned = stitchclient.client.partition_batch(entries, 25)
        partitioned_messages = [x[0] for x in partitioned]

        self.assertEqual(
            partitioned_messages,
            [b'["a","b","c","d","e","f"]',
             b'["g","h","i","j","k","l"]',
             b'["m","n","o","p","q","r"]',
             b'["s","t","u","v","w","x"]',
             b'["y","z"]'])

DummyResponse = collections.namedtuple('DummyResponse', ['status_code'])
        
class TestClient(unittest.TestCase):

    def create_stitch_message(self, table_name, key_names, data):
        return {
            'action': 'upsert',
            'table_name': table_name,
            'key_names': key_names,
            'sequence': int(time.time() * 1000),
            'data': data
        }
    
    def setUp(self):
        self.callback_args = []
        self.client = Client(123, 'abc', batch_delay_seconds=1000000)
        self.client._stitch_request = MagicMock(return_value=DummyResponse(200))

    def accumulate_callbacks(self, callback_args):
        self.callback_args.append(callback_args)
        
    # def test_it(self):
    #     self.client._stitch_request('hello')
    #     self.client._stitch_request('world')
    #     print(self.client._stitch_request.mock_calls)

    def test_push_one_too_small(self):
        message = self.create_stitch_message('foo', ['bar'], {'bar': 1, 'apple': 'red'})
        self.client.push(message)
        self.assertEqual([], self.client._stitch_request.mock_calls)

    def test_push_two_triggers_send(self):
        self.client.target_messages_per_batch = 2
        self.client.callback_function = self.accumulate_callbacks
        message_a = self.create_stitch_message('foo', ['bar'], {'bar': 1, 'letter': 'a'})
        message_b = self.create_stitch_message('foo', ['bar'], {'bar': 2, 'letter': 'b'})
        
        self.client.push(message_a, 1)
        self.client.push(message_b, 2)
        self.assertEqual(1, len(self.client._stitch_request.mock_calls))
        self.assertEqual([[1, 2]], self.callback_args)

    def test_push_two_partitioned(self):
        self.client.target_messages_per_batch = 2
        self.client.max_batch_size_bytes = 200
        self.client.callback_function = self.accumulate_callbacks
        message_a = self.create_stitch_message('foo', ['bar'], {'bar': 1, 'letter': 'a'})
        message_b = self.create_stitch_message('foo', ['bar'], {'bar': 2, 'letter': 'b'})
        
        self.client.push(message_a, 1)
        self.client.push(message_b, 2)
        self.assertEqual(2, len(self.client._stitch_request.mock_calls))
        self.assertEqual([[1], [2]], self.callback_args)
        
    def test_exit_triggers_send(self):

        with self.client as client:
            client.target_messages_per_batch = 100
            client.callback_function = self.accumulate_callbacks
            message_a = self.create_stitch_message('foo', ['bar'], {'bar': 1, 'letter': 'a'})
            message_b = self.create_stitch_message('foo', ['bar'], {'bar': 2, 'letter': 'b'})

            client.push(message_a, 1)
            client.push(message_b, 2)
            self.assertEqual(0, len(self.client._stitch_request.mock_calls))
        self.assertEqual(1, len(self.client._stitch_request.mock_calls))
        self.assertEqual([[1, 2]], self.callback_args)

    def test_time_triggers_send(self):

        self.client.target_messages_per_batch = 100
        self.client.callback_function = self.accumulate_callbacks
        message_a = self.create_stitch_message('foo', ['bar'], {'bar': 1, 'letter': 'a'})
        message_b = self.create_stitch_message('foo', ['bar'], {'bar': 2, 'letter': 'b'})
        self.client.push(message_a, 1)
        self.client.batch_delay_seconds = -1            
        self.client.push(message_b, 2)
        self.assertEqual(1, len(self.client._stitch_request.mock_calls))
        self.assertEqual([[1, 2]], self.callback_args)
        
