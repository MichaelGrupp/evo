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

log "read single info"
echo_and_run evo_traj tum ../data/fr2_desk_ORB.txt

log "verbose mode: -v or --verbose"
echo_and_run evo_traj tum ../data/fr2_desk_ORB.txt -v

log "do a full check of the trajectory"
echo_and_run evo_traj tum ../data/fr2_desk_ORB.txt --full_check

log "load multiple trajectories"
echo_and_run evo_traj tum ../data/fr2_desk_*

log "plot trajectories: -p or --plot"
echo_and_run evo_traj tum ../data/fr2_desk_* --ref=../data/fr2_desk_groundtruth.txt --plot_mode xyz $p

log "align to reference to resolve mess: -a or --align"
echo_and_run evo_traj tum ../data/fr2_desk_* --ref=../data/fr2_desk_groundtruth.txt --plot_mode=xyz -a $p

log "additionally, scale for monocular trajectories"
echo_and_run evo_traj tum ../data/fr2_desk_* --ref=../data/fr2_desk_groundtruth.txt --plot_mode=xyz -as $p

log "save in other format - here: bagfile"
echo_and_run evo_traj tum ../data/fr2_desk_* --ref=../data/fr2_desk_groundtruth.txt -as --save_as_bag

log "plot bag contents"
echo_and_run evo_traj bag *.bag --all_topics --ref=fr2_desk_groundtruth $p

log "yaw-only alignment"
echo_and_run evo_traj tum ../data/V101_openvins.txt --ref=../data/V101_gt.txt -a --yaw_only $p -v

