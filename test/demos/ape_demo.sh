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

log "minimal command"
echo_and_run evo_ape kitti ../data/KITTI_00_gt.txt ../data/KITTI_00_ORB.txt

log "show more output and plot: -v or --verbose and -p or --plot"
echo_and_run evo_ape kitti ../data/KITTI_00_gt.txt ../data/KITTI_00_ORB.txt -v $p

log "align the trajectories"
echo_and_run evo_ape kitti ../data/KITTI_00_gt.txt ../data/KITTI_00_ORB.txt -va $p

log "use other pose_relation (e.g. angle) with -r or --pose_relation"
echo_and_run evo_ape kitti ../data/KITTI_00_gt.txt ../data/KITTI_00_ORB.txt -va $p --pose_relation angle_deg

log "save results"
echo_and_run evo_ape kitti ../data/KITTI_00_gt.txt ../data/KITTI_00_ORB.txt -va --save_results ORB_ape.zip

log "run multiple and save results"
log "first..."
echo_and_run evo_ape kitti ../data/KITTI_00_gt.txt ../data/KITTI_00_ORB.txt -a --save_results ORB_ape.zip
log "second..."
echo_and_run evo_ape kitti ../data/KITTI_00_gt.txt ../data/KITTI_00_SPTAM.txt -a --save_results SPTAM_ape.zip