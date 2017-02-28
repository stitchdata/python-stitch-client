import unittest
import stitchclient.client
import time
from stitchclient.buffer import MAX_BATCH_SIZE_BYTES

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

        
    def test_single_record_available_immediately(self):
        buf = stitchclient.client.Buffer()
        buf.put(tiny_record, None)
        self.assertEqual(buf.take(0, 0)[0].value,
                         tiny_record)

    def test_withhold_until_bytes_available(self):
        buf = stitchclient.client.Buffer()        
        batch_size_bytes = int(len(tiny_record) * 2 + len(tiny_record) / 2.0)
        batch_delay_millis = 1000000000
        put = lambda: buf.put(tiny_record, None)
        take = lambda: buf.take(batch_size_bytes, batch_delay_millis)
        
        put()
        self.assertTrue(take() is None)
        put()
        self.assertTrue(take() is None)
        put()
        res = take()
        self.assertEqual([x.value for x in res], ['apple', 'apple', 'apple'])
        
    def test_buffer_empty_after_batch(self):
        buf = stitchclient.client.Buffer()        
        put = lambda: buf.put(tiny_record, None)
        take = lambda: buf.take(0, 0)        
        put()
        put()
        put()
        self.assertIsNotNone(take())
        self.assertIsNone(take())

    def test_does_not_exceed_max_batch_size(self):
        buf = stitchclient.client.Buffer()        
        put = lambda: buf.put(big_record, None)
        take = lambda: buf.take(0, 0)

        put()
        put()
        put()

        b1 = take()
        b2 = take()
        b3 = take()

        b1len = 0
        b2len = 0

        for x in b1:
            b1len += len(x.value)
        for x in b2:
            b2len += len(x.value)            
        self.assertTrue(b1len < MAX_BATCH_SIZE_BYTES)
        self.assertTrue(b2len < b1len)
        self.assertIsNone(b3)

    def test_cant_put_record_larger_than_max_message_size(self):
        buf = stitchclient.client.Buffer()        
        with self.assertRaises(ValueError):
            buf.put(huge_record, None)

    def test_trigger_batch_at_10k_messages(self):
        buf = stitchclient.client.Buffer()        
        put = lambda: buf.put(tiny_record, None)
        take = lambda: buf.take(MAX_BATCH_SIZE_BYTES, 60000)
        for i in range(9999):
            put()
        self.assertTrue(take() is None)
        put()
        self.assertIsNotNone(take())
