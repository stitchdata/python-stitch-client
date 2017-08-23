import unittest
import stitchclient.client
import time

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


tiny_record = {'action': 'upsert', 'data': 'apple'}
big_record  = 'a' * 1500000
huge_record = 'a' * 5000000

class TestBuffer(unittest.TestCase):

    buffer = None

    def setUp(self):
        self.client = stitchclient.client.Client(123, 'abc', batch_delay_millis=1000000)        
    
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
                         
    # def test_withhold_until_bytes_available(self):
    #     buf = stitchclient.client.Buffer()
    #     batch_delay_millis = 1000000000
    #     put = lambda: buf.put(tiny_record, None)
    #     take = lambda: buf.take(batch_delay_millis)

    #     put()
    #     self.assertTrue(take() is [])
    #     put()
    #     self.assertTrue(take() is [])
    #     print(take())
    #     put()
    #     res = take()
    #     self.assertEqual([x.value for x in res], ['apple', 'apple', 'apple'])

    # def test_buffer_empty_after_batch(self):
    #     buf = stitchclient.client.Buffer()
    #     put = lambda: buf.put(tiny_record, None)
    #     take = lambda: buf.take(0)
    #     put()
    #     put()
    #     put()
    #     self.assertIsNotNone(take())
    #     self.assertIsNone(take())

    # def test_does_not_exceed_max_batch_size(self):
    #     buf = stitchclient.client.Buffer()
    #     put = lambda: buf.put(big_record, None)
    #     take = lambda: buf.take(0)

    #     put()
    #     put()
    #     put()

    #     b1 = take()
    #     b2 = take()
    #     b3 = take()

    #     b1len = 0
    #     b2len = 0

    #     for x in b1:
    #         b1len += len(x.value)
    #     for x in b2:
    #         b2len += len(x.value)
    #     self.assertTrue(b1len < MAX_BATCH_SIZE_BYTES)
    #     self.assertTrue(b2len < b1len)
    #     self.assertIsNone(b3)

    # def test_cant_put_record_larger_than_max_message_size(self):
    #     buf = stitchclient.client.Buffer()
    #     buf.put(huge_record, None)
    #     with self.assertRaises(ValueError):
    #         buf.take(0, True)

    # def test_trigger_batch_at_10k_messages(self):
    #     buf = stitchclient.client.Buffer()
    #     put = lambda: buf.put(tiny_record, None)
    #     take = lambda: buf.take(60000)
    #     for i in range(9999):
    #         put()
    #     self.assertEqual(list(take()), [])
    #     put()
    #     self.assertIsNotNone(take())
