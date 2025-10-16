#!/bin/bash

set -e

if [ ! -f pyproject.toml ]; then
  echo "Error: please execute it in the base directory of the repository."
  exit 1
fi


# Exclude 3rd party files.
black . \
  --exclude "fastentrypoints.py|evo/core/transformations.py|test/tum_benchmark_tools/*"
