#!/usr/bin/env bash

# Install ffmpeg
apt-get update && apt-get install -y ffmpeg

# Proceed with the normal build process
pip install -r requirements.txt
