#!/bin/bash
cd /home/josh/feedler/feedler
mkdir temp
export PYTHONPATH=./temp
python setup.py build develop --install-dir ./temp
cp ./temp/Feedler.egg-link /home/josh/.config/deluge/plugins
rm -fr ./temp
