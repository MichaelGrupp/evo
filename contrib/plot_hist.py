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

def add_colorbar(axis):
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
    XLIM_MAX = 0.30
    YLIM_MAX = 50000
    pipeline_type = "S_P_R"
    plot_hist(pipeline_type, filename, metric,
              XLIM_MAX, YLIM_MAX)

    pipeline_type = "S_P"
    plot_hist(pipeline_type, filename, metric,
              XLIM_MAX, YLIM_MAX)

    XLIM_MAX = 0.30
    YLIM_MAX = 30000
    filename = "Histogram"
    metric = "completeness"
    pipeline_type = "S_P_R"
    plot_hist(pipeline_type, filename, metric,
              XLIM_MAX, YLIM_MAX)

    pipeline_type = "S_P"
    plot_hist(pipeline_type, filename, metric,
              XLIM_MAX, YLIM_MAX)

def plot_hist(pipeline_type, file_name, metric, xlim_max, ylim_max):
    path = "/home/tonirv/code/evo/results/" + pipeline_type + "_Mesh/Histogram/"
    filename = file_name + "_" + metric + ".csv"
    output_filename = file_name + "_" + metric + "_" + pipeline_type

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

    # Create figure
    fig, axarr = plt.subplots(2, sharex=False, figsize=(8, 12), dpi=1000)

    # This is  the colormap I'd like to use.
    cm = plt.cm.get_cmap('jet')
    if metric == "accuracy":
        cm = plt.cm.get_cmap('jet')
    elif metric == "completeness":
        cm = plt.cm.get_cmap('viridis')

    # Use latex
    plt.rc('text', usetex=True)

    # Plot histogram in first subplot.
    n, bins, patches = axarr[0].hist(x, bins=256, weights = weights)
    color_hist_faces(plt, cm, bins, patches)

    # Plot cumulative histogram in second subplot.
    n_2, bins_2, patches_2 = axarr[1].hist(x, bins=256, weights = weights, cumulative=True, density=True)
    color_hist_faces(plt, cm, bins_2, patches_2)

    # Draw vertical lines with text:
    sample_distances = [0.01, 0.04, 0.10]
    y_init = ylim_max
    for i, x in enumerate(sample_distances):
        bin_idx = int(math.floor(x*256/0.3))
        axarr[0].vlines(x=x, ymin=0, ymax=y_init, color = 'r', linewidth = 0.5, linestyle = '--')
        if metric == "accuracy":
            axarr[0].text(x+0.001, y_init * (1 - 0.05),
                          r"$A(\tau={x:.0f}cm)$".format(x=x*100) + '\n' +
                          "$= {v:.0f}\%$".format(v=n_2[bin_idx]*100),
                          rotation=0,
                          verticalalignment='center')
        elif metric == "completeness":
            axarr[0].text(x+0.001, y_init * (1 - 0.05),
                          r"$C(\tau={x:.0f}cm)$".format(x=x*100) + '\n' +
                          "$= {v:.0f}\%$".format(v=n_2[bin_idx]*100),
                          rotation=0,
                          verticalalignment='center')
        else:
            print "Metric argument should be either: accuracy or completeness."
        y_init = ylim_max * (1-0.1*(i+1))

    # Plot formatting
    axarr[0].set_xlim((0.0, xlim_max))   # set the xlim to xmin, xmax
    axarr[0].set_ylim((0.0, ylim_max))   # set the xlim to xmin, xmax
    axarr[1].set_xlim((0.0, xlim_max))   # set the xlim to xmin, xmax
    axarr[1].set_ylim((0.0, 1.05))   # set the ylim to ymin, ymay
    axarr[1].vlines(x=sample_distances, ymin=0, ymax=axarr[1].get_ylim()[1], color = 'r', linewidth = 0.5, linestyle = '--')

    axarr[0].set_ylabel(r'Points Count')
    axarr[0].grid(axis='y', linestyle='dashed', linewidth=1)
    axarr[0].set_axisbelow(True)
    axarr[0].ticklabel_format(style='sci', axis='y', scilimits=(0,0),useOffset=False)

    axarr[1].set_xlabel(r'$\tau$ [m]')
    if metric == "accuracy":
        axarr[0].set_xlabel(r'$d_{r \to \mathcal{G}}$ [m]')
        axarr[1].set_ylabel(r'Mesh Accuracy $A(\tau)$ [%]')
    elif metric == "completeness":
        axarr[0].set_xlabel(r'$d_{g \to \mathcal{R}}$ [m]')
        axarr[1].set_ylabel(r'Mesh Completeness $C(\tau)$ [%]')
    axarr[1].grid(axis='y', linestyle='dashed', linewidth=1)
    axarr[1].set_axisbelow(True)
    vals = axarr[1].get_yticks()
    axarr[1].set_yticklabels(['{:,.0%}'.format(x) for x in vals])

    # Make subplots close to each other and hide x ticks for all but bottom plot
    # fig.subplots_adjust(hspace=0)
    # plt.setp([a.get_xticklabels() for a in fig.axes[:-1]], visible=False)

    # Save figure
    output_path_viz = os.path.join(path, output_filename + ".pdf")
    output_path = os.path.join(path, output_filename + ".pgf")
    plt.savefig(output_path_viz, bbox_inches='tight', transparent=True, dpi=1000)
    plt.savefig(output_path, bbox_inches='tight', transparent=True, dpi=1000)

    # plt.show()

    # Convert saved figure to latex format.
    # subprocess.call("inkscape -D -z --file={} --export-pdf={}.pdf --export-latex".format(
                     # output_path, path + "Histogram_"+pipeline_type), shell=True)

if __name__ == '__main__':
    main()

