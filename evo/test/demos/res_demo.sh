#!/usr/bin/env bash

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

for m in ape rpe rpe-for-each
do
    ls *$m.zip > /dev/null
    retcode=$?; if [ $retcode != 0 ]; then
        echo "missing files: "*$m.zip
        echo "run [ape, rpe, rpe-for-each]_demo.sh before this demo"
        exit 1
    else
        echo "found files for $m"
    fi
done

set -e  # exit on error

for m in ape rpe rpe-for-each
do
    log "load results from evo_ape..."
    echo_and_run evo_res *"$m".zip

    log "load results from evo_$m and plot them"
    echo_and_run evo_res *"$m".zip $p

    log "load results from evo_$m and save plots in pdf"
    echo_and_run evo_res *"$m".zip --save_plot "$m".pdf

    log "load results from evo_$m and save stats in table"
    echo_and_run evo_res *"$m".zip --save_table "$m".csv
done

log "bonus content: --plot_markers"
echo_and_run evo_res *rpe-for-each.zip $p --plot_markers