#!/usr/bin/env python

from setuptools import setup, find_packages
import subprocess

setup(name="stitchclient",
      version="0.8.8.post1",
      description="A Stitch API client for Python",
      author="Stitch",
      author_email="support@stitchdata.com",
      url="https://github.com/stitchdata/python-stitch-client",
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      packages=find_packages() + find_packages(where="./transit"),
      install_requires=[
          "python-dateutil==2.8.1",
          "msgpack-python",
          "requests==2.24.0",
      ]
)
