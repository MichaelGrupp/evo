#!/usr/bin/env python3
# Set-up PGF as the backend for saving a PDF
import matplotlib
from matplotlib.pyplot import text
from evo.tools import file_interface
import numpy as np
import os
import subprocess
import math

from matplotlib.backends.backend_pgf import FigureCanvasPgf
matplotlib.backend_bases.register_backend('pdf', FigureCanvasPgf)

import matplotlib.pyplot as plt
import textwrap as tw

# Style works - except no Grey background
#plt.style.use('fivethirtyeight')

pgf_with_latex = {
    "pgf.texsystem": "xelatex",     # Use xetex for processing
    "text.usetex": True,            # use LaTeX to write all text
    "font.family": "serif",         # use serif rather than sans-serif
    "font.serif": "Ubuntu",         # use Ubuntu as the font
    "font.sans-serif": [],          # unset sans-serif
    "font.monospace": "Ubuntu Mono",# use Ubuntu for monospace
    "axes.labelsize": 10,
    "font.size": 10,
    "legend.fontsize": 8,
    "axes.titlesize": 14,           # Title size when one figure
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
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

def add_colorbar(fig, axis):
    # Now adding the colorbar
    # Set the colormap and norm to correspond to the data for which
    # the colorbar will be used.
    cmap = matplotlib.cm.jet
    norm = matplotlib.colors.Normalize(vmin=0.0, vmax=0.30)

    # ColorbarBase derives from ScalarMappable and puts a colorbar
    # in a specified axes, so it has everything needed for a
    # standalone colorbar.  There are many more kwargs, but the
    # following gives a basic continuous colorbar with ticks
    # and labels.
    pos1 = axis.get_position() # get the original position
    ax1 = fig.add_axes([0.9, pos1.y0, 0.02, pos1.height])
    cb1 = matplotlib.colorbar.ColorbarBase(ax1, cmap=cmap,
                                           norm=norm,
                                           orientation='vertical')
    cb1.set_label('Some Units')

def color_hist_faces(plt, colormap, bins, patches):
    # Color faces of the histogram with colormap.
    # Scale values to interval [0,1]
    bin_centers = 0.5 * (bins[:-1] + bins[1:])
    col = bin_centers - min(bin_centers)
    col /= max(col)
    for c, p in zip(col, patches):
        plt.setp(p, 'facecolor', colormap(c))
    # draw very last rectangle
    # last_rectangle = matplotlib.patches.Rectangle(xy=(patches[-1].xy[0],
                                   # patches[-1].xy[1]),
                               # width=2*patches[-1].get_width(),
                               # height=patches[-1].get_height(),
                               # angle=patches[-1].angle)
    # plt.setp(last_rectangle, 'facecolor', colormap(0.9))

def main():
    filename = "Histogram"
    metric = "accuracy"
    XLIM_MAX = 0.10
    YLIM_MAX = 1
    pipeline_types = ["S_P", "S_P_R"]
    # plot_hist(pipeline_types[0], filename, metric,
              # XLIM_MAX, YLIM_MAX)

    # plot_hist(pipeline_types[1], filename, metric,
              # XLIM_MAX, YLIM_MAX)

    plot_joint_hist(pipeline_types, filename, metric,
              XLIM_MAX, YLIM_MAX)

def plot_joint_hist(pipeline_types, file_name, metric, xlim_max, ylim_max):
    filename = file_name + "_" + metric + ".csv"
    # Create figure
    fig, axarr = plt.subplots(1, 2, sharey=True, figsize=(5, 3), dpi=1000)

    # Use latex
    plt.rc('text', usetex=True)

    # This is  the colormap I'd like to use.
    cm = plt.cm.get_cmap('jet')
    if metric == "accuracy":
        cm = plt.cm.get_cmap('jet')
    elif metric == "completeness":
        cm = plt.cm.get_cmap('viridis')

    k = -1
    for pipeline_type in pipeline_types:
        k = k + 1
        print k
        path = "/home/tonirv/code/evo/results/" + pipeline_type + "_Mesh/Histogram/"
        output_filename = file_name + "_for_paper_" + metric + "_" + pipeline_type

        # TODO remove the ; at the end of each line of the csv, or you will have a
        # "could not convert string to float"
        mat = np.array(file_interface.csv_read_matrix(os.path.join(path, filename), delim=";", comment_str="#")).astype(float)
        bin_id = mat[:, 0]
        value = mat[:, 1]
        bin_lower_bounds = mat[:, 2]
        bin_upper_bounds = mat[:, 3]

        x = bin_lower_bounds
        weights = value
        bins = bin_lower_bounds + bin_upper_bounds[-1]

        # Create unplotted hist to calculate n_2.
        fig_2, axarr_2 = plt.subplots(1, sharex=False, figsize=(8, 8), dpi=1000)
        # Plot cumulative histogram in second subplot.
        n_2, bins_2, patches_2 = axarr_2.hist(x, bins=256, weights = weights, cumulative=True, density=True)

        # Plot histogram in first subplot.
        n, bins, patches = axarr[k].hist(x, bins=256, weights = weights, cumulative=True, density=True)
        color_hist_faces(plt, cm, bins, patches)

        # Draw vertical lines with text:
        # sample_distances = [0.01, 0.04, 0.10]
        # max_y_vlines= [ylim_max, ylim_max-10000, ylim_max-20000]
        # for i, x in enumerate(sample_distances):
            # bin_idx = int(math.floor(x*256/0.3))
            # axarr[k].vlines(x=x, ymin=0, ymax=max_y_vlines[i]-1000, color = 'r', linewidth = 0.5, linestyle = '--')
            # if metric == "accuracy":
                # axarr[k].text(x+0.001, max_y_vlines[i] - 5000,
                              # r"$A(\tau={x:.0f}cm)$".format(x=x*100) + '\n' +
                              # "$= {v:.0f}\%$".format(v=n_2[bin_idx]*100),
                              # rotation=0,
                              # verticalalignment='center')
            # else:
                # print "Metric argument should be either: accuracy or completeness."

        # Plot formatting
        axarr[k].set_xlim((0.0, xlim_max))   # set the xlim to xmin, xmax
        axarr[k].set_ylim((0.0, ylim_max))   # set the xlim to xmin, xmax
        if k == 0:
            axarr[k].set_ylabel(r'Points Count')
        axarr[k].grid(axis='y', linestyle='dashed', linewidth=1)
        axarr[k].set_axisbelow(True)
        axarr[k].ticklabel_format(style='sci', axis='y', scilimits=(0,0),useOffset=False)

        if metric == "accuracy":
            axarr[k].set_xlabel(r'$d_{r \to \mathcal{G}}$ [m]')

    # Make subplots close to each other and hide x ticks for all but bottom plot
    # fig.subplots_adjust(hspace=0)
    # plt.setp([a.get_xticklabels() for a in fig.axes[:-1]], visible=False)

    # Save figure
    # fig.subplots_adjust(wspace=.5)
    fig.show()
    output_path_viz = os.path.join(path, output_filename + ".pdf")
    output_path = os.path.join(path, output_filename + ".pgf")
    fig.savefig(output_path_viz, bbox_inches='tight', transparent=True, dpi=1000)
    fig.savefig(output_path, bbox_inches='tight', transparent=True, dpi=1000)


    # Convert saved figure to latex format.
    # subprocess.call("inkscape -D -z --file={} --export-pdf={}.pdf --export-latex".format(
                     # output_path, path + "Histogram_"+pipeline_type), shell=True)

def plot_hist(pipeline_type, file_name, metric, xlim_max, ylim_max):
    path = "/home/tonirv/code/evo/results/" + pipeline_type + "_Mesh/Histogram/"
    filename = file_name + "_" + metric + ".csv"
    output_filename = file_name + "_for_paper_" + metric + "_" + pipeline_type

    # TODO remove the ; at the end of each line of the csv, or you will have a
    # "could not convert string to float"
    mat = np.array(file_interface.csv_read_matrix(os.path.join(path, filename), delim=";", comment_str="#")).astype(float)
    bin_id = mat[:, 0]
    value = mat[:, 1]
    bin_lower_bounds = mat[:, 2]
    bin_upper_bounds = mat[:, 3]

    x = bin_lower_bounds
    weights = value
    bins = bin_lower_bounds + bin_upper_bounds[-1]

    # This is  the colormap I'd like to use.
    cm = plt.cm.get_cmap('jet')
    if metric == "accuracy":
        cm = plt.cm.get_cmap('jet')
    elif metric == "completeness":
        cm = plt.cm.get_cmap('viridis')

    # Create unplotted hist to calculate n_2.
    fig_2, axarr_2 = plt.subplots(1, sharex=False, figsize=(8, 8), dpi=1000)
    # Plot cumulative histogram in second subplot.
    n_2, bins_2, patches_2 = axarr_2.hist(x, bins=256, weights = weights, cumulative=True, density=True)

    # Create figure
    fig, axarr = plt.subplots(1, sharey=False, figsize=(5, 3), dpi=1000)

    # Use latex
    plt.rc('text', usetex=True)

    # Plot histogram in first subplot.
    n, bins, patches = axarr[k].hist(x, bins=256, weights = weights)
    color_hist_faces(axarr[k], cm, bins, patches)

    # Draw vertical lines with text:
    sample_distances = [0.01, 0.04, 0.10]
    max_y_vlines= [ylim_max, ylim_max-10000, ylim_max-20000]
    for i, x in enumerate(sample_distances):
        bin_idx = int(math.floor(x*256/0.3))
        axarr.vlines(x=x, ymin=0, ymax=max_y_vlines[i]-1000, color = 'r', linewidth = 0.5, linestyle = '--')
        if metric == "accuracy":
            axarr.text(x+0.001, max_y_vlines[i] - 5000,
                          r"$A(\tau={x:.0f}cm)$".format(x=x*100) + '\n' +
                          "$= {v:.0f}\%$".format(v=n_2[bin_idx]*100),
                          rotation=0,
                          verticalalignment='center')
        else:
            print "Metric argument should be either: accuracy or completeness."

    # Plot formatting
    axarr.set_xlim((0.0, xlim_max))   # set the xlim to xmin, xmax
    axarr.set_ylim((0.0, ylim_max))   # set the xlim to xmin, xmax

    axarr.set_ylabel(r'Points Count')
    axarr.grid(axis='y', linestyle='dashed', linewidth=1)
    axarr.set_axisbelow(True)
    axarr.ticklabel_format(style='sci', axis='y', scilimits=(0,0),useOffset=False)

    if metric == "accuracy":
        axarr.set_xlabel(r'$d_{r \to \mathcal{G}}$ [m]')

    # Make subplots close to each other and hide x ticks for all but bottom plot
    # fig.subplots_adjust(hspace=0)
    # plt.setp([a.get_xticklabels() for a in fig.axes[:-1]], visible=False)

    # Save figure
    output_path_viz = os.path.join(path, output_filename + ".pdf")
    output_path = os.path.join(path, output_filename + ".pgf")
    plt.savefig(output_path_viz, bbox_inches='tight', transparent=True, dpi=1000)
    plt.savefig(output_path, bbox_inches='tight', transparent=True, dpi=1000)

    plt.show()

    # Convert saved figure to latex format.
    # subprocess.call("inkscape -D -z --file={} --export-pdf={}.pdf --export-latex".format(
                     # output_path, path + "Histogram_"+pipeline_type), shell=True)

if __name__ == '__main__':
    main()

