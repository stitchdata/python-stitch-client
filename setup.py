#!/usr/bin/env python

from setuptools import setup, find_packages


##########
# NOTICE #
##########

# This file was changed to loosen the requirements to install stitchclient.
# Also, an unused import was removed.


setup(
    name="stitchclient",
    version="1.0.1",
    description="A Stitch API client for Python",
    author="Stitch",
    author_email="support@stitchdata.com",
    url="https://github.com/stitchdata/python-stitch-client",
    classifiers=['Programming Language :: Python :: 3 :: Only'],
    packages=find_packages(),
    install_requires=[
        "python-dateutil>=2.6.1,<3.0",
        "msgpack-python",
        "requests>=2.20.0,<3.0",
    ],
)
