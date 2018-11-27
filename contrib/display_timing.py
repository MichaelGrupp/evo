#!/usr/bin/env python

import matplotlib
from matplotlib.backends.backend_pgf import FigureCanvasPgf
matplotlib.backend_bases.register_backend('pdf', FigureCanvasPgf)

import matplotlib.pyplot as plt
import numpy as np

pgf_with_latex = {
    "pgf.texsystem": "xelatex",     # Use xetex for processing
    "text.usetex": True,            # use LaTeX to write all text
    "font.family": "serif",         # use serif rather than sans-serif
    "font.serif": "Ubuntu",         # use Ubuntu as the font
    "font.sans-serif": [],          # unset sans-serif
    "font.monospace": "Ubuntu Mono",# use Ubuntu for monospace
    "axes.labelsize": 12,
    "font.size": 20,
    "legend.fontsize": 12,
    "axes.titlesize": 20,           # Title size when one figure
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.titlesize": 12,         # Overall figure title
    "pgf.rcfonts": False,           # Ignore Matplotlibrc
    "text.latex.unicode": True,     # Unicode in LaTeX
    "pgf.preamble": [               # Set-up LaTeX
        r'\usepackage{fontspec}',
        r'\setmainfont{Ubuntu}',
        r'\setmonofont{Ubuntu Mono}',
        r'\usepackage{unicode-math}',
        r'\setmathfont{Ubuntu}'
    ]
}

matplotlib.rcParams.update(pgf_with_latex)

def draw_plot(filename, ylabel, display, display_x_label, keyframe_ids, update_times, ymax = -1.0):
    fig = plt.figure(figsize=[6, 3], dpi=1000)
    linestyles = ['-', '-', '-']
    colors = ['r', 'g', 'b']
    labels = ['S', 'SP', 'SPR']
    i = 0
    for update_time in update_times:
        plt.plot(keyframe_ids, update_time, linestyle=linestyles[i], color=colors[i], linewidth=0.5,
                label="$t_{"+labels[i]+"}^{opt}$")
        i = i +1
    plt.ylabel(ylabel)
    if display_x_label:
        plt.xlabel('Keyframe Index [-]')
    plt.xlim(min(keyframe_ids), max(keyframe_ids))
    plt.ylim(0, 0.35)
    plt.grid(axis='both', linestyle='--')
    if ymax > 0:
        plt.ylim((0, ymax))   # set the ylim to ymin, ymax
    plt.legend()
    plt.savefig(filename, bbox_inches='tight', transparent=True, dpi=1000)
    if display:
        plt.show()

def draw_single_plot(filename, ylabel, display, display_x_label, keyframe_ids, update_times, ymax = -1.0):
    fig = plt.figure(figsize=[6, 2], dpi=1000)
    plt.plot(keyframe_ids, update_times, linewidth=1)
    plt.ylabel(ylabel)
    if display_x_label:
        plt.xlabel('Keyframe Index [-]')
    plt.xlim(min(keyframe_ids), max(keyframe_ids))
    plt.ylim(0, 0.35)
    plt.grid(axis='both', linestyle='--')
    if ymax > 0:
        plt.ylim((0, ymax))   # set the ylim to ymin, ymax
    fig.savefig(filename, bbox_inches='tight', transparent=True, dpi=1000)
    if display:
        plt.show()

def main():
    root = "/home/tonirv/code/evo/results/V1_01_easy/"
    filename = open(root + "SPR/output/output_timingVIO.txt", 'r')
    keyframe_ids_spr, update_times_spr = np.loadtxt(filename, delimiter=' ', usecols=(0,3), unpack=True)
    # draw_single_plot(root + "timing/spr_timing_for_paper.pgf", "Optimization time $t_{S + P + R}^{opt}$ [s]", False, True, keyframe_ids_spr, update_times_spr, 0.35)

    filename = open(root + "SP/output/output_timingVIO.txt", 'r')
    keyframe_ids_sp, update_times_sp = np.loadtxt(filename, delimiter=' ', usecols=(0,3), unpack=True)
    # draw_single_plot(root + "timing/sp_timing_for_paper.pgf", "Optimization time $t_{S + P}^{opt}$ [s]", False, False, keyframe_ids_sp, update_times_sp, 0.35)

    filename = open(root + "S/output/output_timingVIO.txt", 'r')
    keyframe_ids_s, update_times_s = np.loadtxt(filename, delimiter=' ', usecols=(0,3), unpack=True)
    # draw_single_plot(root + "timing/s_timing_for_paper.pgf", "Optimization time $t_{S}^{opt}$ [s]", False, False, keyframe_ids_s, update_times_s, 0.35)

    update_times = [update_times_s, update_times_sp, update_times_spr]
    draw_plot(root + "timing/all_timing_for_paper.pgf", "Optimization time [s]", True, True, keyframe_ids_s, update_times, 0.35)


    # SP - S
    sp_s = update_times_sp - update_times_s
    print "Max SP - S"
    print max(sp_s)
    print "Mean SP - S"
    print sum(sp_s)/len(sp_s)

    # SPR - SP
    spr_sp = update_times_spr - update_times_sp
    print "Max SPR - SP"
    print max(spr_sp)
    print "Mean SPR - SP"
    print sum(spr_sp)/len(spr_sp)

if __name__ == "__main__":
    main()
