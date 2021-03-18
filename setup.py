#!/usr/bin/env python3

from distutils.core import setup

setup(
    name="dcp1602",
    version='0.1',
    description="Brother network scanner protocol implementation, based on Vladimir Shapranov work for DCP-1610w",
    author='Guilherme Chehab',
    author_email='guilherme.chehab@gmail.com',
    url='https://github.com/gchehab/dcp1602',
    packages=['dcp1610','dcp1602'],
    scripts=['dcp1610-scan','dcp1602-scan'],
    requires=['easysnmp', 'zeroconf', 'Pillow', 'pyusb']
)

