#!/bin/sh

. venv/bin/activate
# ensure all dependencies are installed
python3 setup.py develop
pyinstaller crypted-container-ctl.spec
