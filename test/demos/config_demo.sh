#!/usr/bin/env bash

set -e  # exit on error

# printf "\033c" resets the output
function log { printf "\033c"; echo -e "\033[32m[$BASH_SOURCE] $1\033[0m"; }
function echo_and_run { echo -e "\$ $@" ; read input; "$@" ; read input; }

# always run in script directory
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
cd "$parent_path"

log "show package settings"
echo_and_run evo_config show

if [ -e cfg.json ]; then
    log "show arbitrary .json config"
    echo_and_run evo_config show cfg.json
fi

log "set some package settings"
echo_and_run sudo evo_config set plot_figsize 6 5 plot_usetex plot_fontfamily serif

if [ -e cfg.json ]; then
    log "set parameter of some arbitrary .json config"
    echo_and_run evo_config set -c cfg.json mode speed
fi

log "reset package settings to defaults"
echo_and_run sudo evo_config reset

log "generate a .json config from arbitrary command line options"
echo_and_run sudo evo_config generate --flag --number 2.5 --string plot.pdf --list 1 2.3 4