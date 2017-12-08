#!/usr/bin/env bash

set -e  # exit on error

# printf "\033c" resets the output
function log { printf "\033c"; echo -e "\033[32m[$BASH_SOURCE] $1\033[0m"; }
function echo_and_run { echo -e "\$ $@" ; read input; "$@" ; read input; }

# always run in script directory
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
cd "$parent_path"

p="-p"
if [[ $* == *--no_plots* ]]; then
    p=
fi

log "hard way: specify parameters in command"
echo_and_run evo_rpe-for-each bag ../data/ROS_example.bag groundtruth ORB-SLAM -v $p --mode path --bins 10 20 30 40 50 --tols 0.1 0.1 0.1 0.1 0.1

log "smart way: store parameters in a config .json..."
echo_and_run evo_config generate -o cfg.json --mode path --bins 10 20 30 40 50 --tols 0.1 0.1 0.1 0.1 0.1

log "...and use it to run the executable"
echo_and_run evo_rpe-for-each bag ../data/ROS_example.bag groundtruth ORB-SLAM -c cfg.json -v $p --save_results orb_rpe-for-each.zip

log "save results of another trajectory"
echo_and_run evo_rpe-for-each bag ../data/ROS_example.bag groundtruth S-PTAM -c cfg.json -v $p --save_results sptam_rpe-for-each.zip
