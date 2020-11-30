#!/usr/bin/env python

from setuptools import setup, find_packages
import subprocess

setup(name="stitchclient",
      version="0.8.1.post1",
      description="A Stitch API client for Python",
      author="Stitch",
      author_email="support@stitchdata.com",
      url="https://github.com/stitchdata/python-stitch-client",
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      packages=find_packages(),
      install_requires=[
          "python-dateutil==2.7.3",
          "msgpack-python",
          "requests==2.24.0",
      ]
)
