#!/bin/sh

for DIR_NAME in build dist; do
    if [ -e "${DIR_NAME}" ]; then
        trash "${DIR_NAME}"
    fi
done

if [ ! -e "venv.release" ]; then
    echo "virtualenv to create release builds not found (directory './venv.release')"
fi
. venv.release/bin/activate

# ensure all dependencies are installed
pip install -e .
pyinstaller crypted-container-ctl.spec

trash build

