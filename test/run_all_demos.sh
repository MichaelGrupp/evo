#!/usr/bin/env bash

set -e  # exit on error

n=""
if [[ $* == *--no_plots* ]]; then
    n="--no_plots"
fi

# run all demo scripts to get cheap app tests
yes | demos/traj_demo.sh "$n"
yes | demos/ape_demo.sh "$n"
yes | demos/rpe_demo.sh "$n"
yes | demos/res_demo.sh "$n"
yes | demos/latex_demo.sh "$n"

echo "enter 'y' to clean, any other key to exit"
read input
if [[ $input == y ]]; then
    demos/clean.sh
    exit 0
fi