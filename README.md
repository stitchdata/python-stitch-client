python-stitch-client
====================

A Stitch Import API client library for python

Use
---

This library depends on python3 - if that's not your default python, try this:

```bash
› mkvirtualenv -p python3 stitch
```

Next, install this library:

```bash
› workon stitch
› pip install stitchclient
```

Now you're ready to use the library. From the same `virtualenv`:

```python
from stitchclient.client import Client

with Client(int(os.environ['STITCH_CLIENT_ID']), os.environ['STITCH_TOKEN'], callback_function=print) as c:
        for i in range(1,10):
            c.push({'action': 'upsert',
                    'table_name': 'test_table',
                    'key_names': ['id'],
                    'sequence': i,
                    'data': {'id': i, 'value': 'abc'}}, i)
```

License
-------

python-stitch-client is Copyright © 2016 Stitch and Distributed under
the Apache License Version 2.0

transit-python is Copyright © 2014-2016 Cognitect and Distributed
under the Apache License Version 2.0
