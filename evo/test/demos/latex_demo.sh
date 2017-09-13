#!/usr/bin/env bash

set -e  # exit on error

# printf "\033c" resets the output
function log { printf "\033c"; echo -e "\033[32m[$BASH_SOURCE] $1\033[0m"; }
function echo_and_run { echo -e "\$ $@" ; read input; "$@" ; read input; }

# always run in script directory
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
cd "$parent_path"

log "configure LaTeX-friendly settings"
echo_and_run sudo evo_config set plot_figsize 5 5 plot_usetex plot_fontfamily serif plot_linewidth 0.5 plot_seaborn_style whitegrid plot_export_format pgf

log "generate .pgf figures"
echo_and_run evo_res *rpe.zip --save_plot example.pgf

log "generate .pdf from .tex"
echo_and_run pdflatex example.tex
if [[ ! $* == *--no_plots* ]]; then
    evince example.pdf
fi

yes | sudo evo_config reset