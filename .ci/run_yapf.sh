#!/bin/bash

set -e

if [ ! -f setup.py ]; then
  echo "Error: please execute it in the base directory of the repository."
  exit 1
fi


# Exclude 3rd party files.
yapf --recursive --in-place -vv . \
  --exclude "fastentrypoints.py" \
  --exclude "evo/core/transformations.py" \
  --exclude "test/tum_benchmark_tools/*" \
