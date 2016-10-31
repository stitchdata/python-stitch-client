python-stitch-client
====================

A python client library for the Stitch Import API

Use
---

This library depends on python3 and a to-be-released version of
`transit-python`. The first step is to setup the python environment
and manually install the correct version of that library:

```bash
› mkvirtualenv -p python3 stitch
```

```bash
› workon stitch
› git clone https://github.com/cognitect/transit-python
› cd transit-python
› python setup.py install
```

Next, install this library:

```bash
› workon stitch
› git clone http://github.com/stitchdata/python-stitch-client
› cd python-stitch-client
› python setup.py install
```

Now you're ready to use the library.  Using the same `virtualenv`:

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

Copyright © 2016 Stitch

Distributed under the Apache License Version 2.0
