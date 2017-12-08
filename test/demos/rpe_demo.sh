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

log "minimal command (delta = 1 frame)"
echo_and_run evo_rpe kitti ../data/KITTI_00_gt.txt ../data/KITTI_00_ORB.txt

log "show more output and plot: -v or --verbose and -p or --plot"
echo_and_run evo_rpe kitti ../data/KITTI_00_gt.txt ../data/KITTI_00_ORB.txt -v $p

log "use a different delta between the pose pairs:\n-d or --delta and -u or --delta_unit"
echo_and_run evo_rpe kitti ../data/KITTI_00_gt.txt ../data/KITTI_00_ORB.txt -v -d 10 -u m $p

log "use other pose_relation (e.g. angle) with -r or --pose_relation"
echo_and_run evo_rpe kitti ../data/KITTI_00_gt.txt ../data/KITTI_00_ORB.txt -v -d 10 -u m -r angle_deg $p

log "save results"
echo_and_run evo_rpe kitti ../data/KITTI_00_gt.txt ../data/KITTI_00_ORB.txt -v -d 10 -u m --save_results ORB_rpe.zip

log "run multiple and save results"
log "first..."
echo_and_run evo_rpe kitti ../data/KITTI_00_gt.txt ../data/KITTI_00_ORB.txt -d 10 -u m --save_results ORB_rpe.zip
log "second..."
echo_and_run evo_rpe kitti ../data/KITTI_00_gt.txt ../data/KITTI_00_SPTAM.txt -d 10 -u m --save_results SPTAM_rpe.zip