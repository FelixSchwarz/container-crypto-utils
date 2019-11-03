#!/bin/sh

for DIR_NAME in build dist; do
    if [ -e "${DIR_NAME}" ]; then
        trash "${DIR_NAME}"
    fi
done

. venv/bin/activate
# ensure all dependencies are installed
python3 setup.py develop
pyinstaller crypted-container-ctl.spec

trash build

