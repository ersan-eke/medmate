#!/bin/sh
# Zip exactly what is committed at HEAD: never .venv, models, scratch files or untracked files.
cd "$(dirname "$0")/.." && git archive --format=zip --prefix=medmate/ -o medmate.zip HEAD && echo "medmate.zip from $(git rev-parse --short HEAD)"
