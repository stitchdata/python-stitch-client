#!/usr/bin/env python

from setuptools import setup, find_packages
import subprocess

setup(name="python-stitch-client",
      version="0.4.0",
      description="Send records to the Stitch API from Python",
      author="Stitch",
      url="https://github.com/stitchdata/python-stitch-client"
      packages=find_packages(),
      install_requires=["transit-python"])
