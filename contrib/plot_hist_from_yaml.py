#!/usr/bin/env python3
# Set-up PGF as the backend for saving a PDF
import matplotlib
from matplotlib.pyplot import text
from evo.tools import file_interface
import numpy as np
import os
import yaml
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

def main():
    path = "/home/tonirv/code/spark_vio/scripts"
    plot(path, "histogram_2")

def plot(path, filename):
    from matplotlib.colors import LogNorm
    import matplotlib.pyplot as plt
    import numpy as np

    # normal distribution center at x=0 and y=5
    x = np.random.randn(100000)
    y = np.random.randn(100000) + 5

    plt.hist2d(x, y, bins=40, norm=LogNorm())
    plt.colorbar()
    plt.show()

def plot_1D(path, filename):
    # Create figure
    fig, axarr = plt.subplots(1, sharex=False, #figsize=(8, 12),
                              dpi=1000)

    # Use latex
    plt.rc('text', usetex=True)

    # First subplot.
    skip_lines = 6
    with open(os.path.join(path, filename + '.yaml')) as infile:
        for i in range(skip_lines):
            _ = infile.readline()
        data = yaml.load(infile)
        plot_implementation(axarr, data['data'])

    # Save figure
    output_filename = filename
    output_path = os.path.join("/home/tonirv/Documents/Master Thesis/master_thesis/final_thesis/img/",
                               output_filename + ".pgf")
    plt.savefig(output_path, bbox_inches='tight', transparent=True, dpi=1000)
    plt.show(block=False)

    # Second plot
    fig, axarr = plt.subplots(1, sharex=False, #figsize=(8, 12),
                              dpi=1000)

    # Use latex
    plt.rc('text', usetex=True)
    with open(os.path.join(path, filename + '_smoothed.yaml')) as infile:
        for i in range(skip_lines):
            _ = infile.readline()
        data = yaml.load(infile)
        plot_implementation(axarr, data['data'])
    # Save figure
    output_filename = filename + "_smoothed"
    output_path = os.path.join("/home/tonirv/Documents/Master Thesis/master_thesis/final_thesis/img/",
                               output_filename + ".pgf")
    plt.savefig(output_path, bbox_inches='tight', transparent=True, dpi=1000)
    plt.show()

def plot_implementation(axarr, data):
    # Plot histogram in axarr.

    # Range of the histogram in meters
    labels_x = [float(z)* (-0.75 + 3.0)/512 - 0.75 for z in range(len(data))]

    n, bins, patches = axarr.hist(labels_x, bins=256, weights = data)
    # plt.bar(list(range(len(data))), height=data, width=1, align='center')

    # Plot formatting
    axarr.set_xlim((-0.5, 0.5))   # set the xlim to xmin, xmax
    #axarr.set_ylim((0.0, ylim_max))   # set the xlim to xmin, xmax

    axarr.set_ylabel(r'Count of Points [-]')
    axarr.grid(axis='y', linestyle='dashed', linewidth=0.5)
    axarr.set_axisbelow(True)
    # axarr.ticklabel_format(style='sci', axis='y', scilimits=(0,0), useOffset=False)

    axarr.set_xlabel(r'Elevation [m]')

if __name__ == '__main__':
    main()

