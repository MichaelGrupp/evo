#!/usr/bin/env bash

# always run in script directory
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
cd "$parent_path"

rm -I *.bag *.kitti *.tum *.csv *.pdf *.zip *.pgf *.log *.aux *.json
