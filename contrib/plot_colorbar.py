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

def add_colorbar(axis, fig, cmap, label):
    # Now adding the colorbar
    # Set the colormap and norm to correspond to the data for which
    # the colorbar will be used.
    norm = matplotlib.colors.Normalize(vmin=0.0, vmax=0.30)

    # ColorbarBase derives from ScalarMappable and puts a colorbar
    # in a specified axes, so it has everything needed for a
    # standalone colorbar.  There are many more kwargs, but the
    # following gives a basic continuous colorbar with ticks
    # and labels.
    pos1 = axis.get_position() # get the original position
    ax1 = fig.add_axes([pos1.x0+0.03, pos1.y0-0.025, pos1.width-0.06, 0.02])
    cb1 = matplotlib.colorbar.ColorbarBase(ax1, cmap=cmap,
                                           norm=norm,
                                           orientation='horizontal')
    cb1.set_label(label)

def main():
    # S_P_R
    pipeline_type = "S_P_R"

    # Completeness
    path = "/home/tonirv/code/evo/results/" + pipeline_type + "_Mesh/Histogram/"
    filename = "completeness"
    plot_img(path, pipeline_type, filename)

    # Accuracy 1
    filename="frame_000000"
    path= "/home/tonirv/code/evo/results/" + pipeline_type + "_Mesh/frames_animation/"
    plot_img(path, pipeline_type, filename)

    # Accuracy 2
    filename="frame_000109"
    path= "/home/tonirv/code/evo/results/" + pipeline_type + "_Mesh/frames_animation/"
    plot_img(path, pipeline_type, filename)

    # S_P
    pipeline_type = "S_P"

    # Completeness
    path = "/home/tonirv/code/evo/results/" + pipeline_type + "_Mesh/Histogram/"
    filename = "completeness"
    plot_img(path, pipeline_type, filename)

    # Accuracy 1
    path= "/home/tonirv/code/evo/results/" + pipeline_type + "_Mesh/animation_frames/"
    filename="frame_000000"
    plot_img(path, pipeline_type, filename)

    # Accuracy 2
    filename="frame_000109"
    plot_img(path, pipeline_type, filename)

def plot_img(path, pipeline_type, file_name):
    filename = file_name + ".png"
    output_filename = file_name + "_" + pipeline_type + ".eps"

    import matplotlib.image as mpimg
    img = mpimg.imread(os.path.join(path, filename))
    fig = plt.figure(figsize=(6,6*0.70635)) # For an image of 1679x2377
    imgplot = plt.imshow(img)
    ax = plt.gca()
    ax.set_ylabel('')
    ax.set_xlabel('')

    # Turn off tick labels
    ax.set_yticklabels([])
    ax.set_xticklabels([])
    plt.xticks([])
    plt.yticks([])
    plt.autoscale(enable=True, axis='both', tight=True)

    cmap = matplotlib.cm.jet
    label = r'$d_{r \to \mathcal{G}}$ [m]'
    if file_name == "completeness":
        cmap = matplotlib.cm.viridis
        label = r'$d_{g \to \mathcal{R}}$ [m]'
    add_colorbar(ax, fig, cmap, label)

    # Save figure
    output_path = os.path.join(path, output_filename)
    plt.savefig(output_path, bbox_inches='tight', transparent=True, dpi=1000, pad_inches=0)

    # plt.show()

if __name__ == '__main__':
    main()

