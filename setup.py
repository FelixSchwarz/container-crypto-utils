#!/usr/bin/env python3

from setuptools import setup

setup(
    name='ContainerCryptoUtils',
    version='0.1',
    description='Utilities to mount/unmount encrypted container files.',
    license='MIT',
    packages=['schwarz.containercrypto'],
    scripts=[
        'scripts/crypted-container-ctl',
    ],
    install_requires=(
        'docopt',
    ),
    tests_require=(
        'PythonicTestcase',
    ),
    zip_safe=False,
    python_requires='>=3.6',
)

