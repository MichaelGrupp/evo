# -*- coding: UTF8 -*-
"""
some plotting functionality for different tasks
author: Michael Grupp

This file is part of evo (github.com/MichaelGrupp/evo).

evo is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

evo is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with evo.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import print_function  # Python 2.7 backwards compatibility

import os
import logging
import pickle
import collections
from enum import Enum

import matplotlib as mpl
from evo.tools.settings import SETTINGS

mpl.use(SETTINGS.plot_backend)
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import mpl_toolkits.mplot3d.art3d as art3d
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.collections import LineCollection

import numpy as np
import seaborn as sns

from evo import EvoException
from evo.tools import user
from evo.core import trajectory

# configure matplotlib and seaborn according to package settings
# TODO: 'color_codes=False' to work around this bug:
# https://github.com/mwaskom/seaborn/issues/1546
sns.set(style=SETTINGS.plot_seaborn_style, font=SETTINGS.plot_fontfamily,
        font_scale=SETTINGS.plot_fontscale, color_codes=False,
        palette=SETTINGS.plot_seaborn_palette)
rc = {
    "lines.linewidth": SETTINGS.plot_linewidth,
    "text.usetex": SETTINGS.plot_usetex,
    "font.family": SETTINGS.plot_fontfamily,
    "pgf.texsystem": SETTINGS.plot_texsystem
}
mpl.rcParams.update(rc)

logger = logging.getLogger(__name__)


class PlotException(EvoException):
    pass


class PlotMode(Enum):
    xy = "xy"
    xz = "xz"
    yx = "yx"
    yz = "yz"
    zx = "zx"
    zy = "zy"
    xyz = "xyz"


class PlotCollection:
    def __init__(self, title="", deserialize=None):
        self.title = " ".join(title.splitlines())  # one line title
        self.figures = collections.OrderedDict()  # remember placement order
        # hack to avoid premature garbage collection with Qt
        # (stackoverflow.com/questions/600289)
        self.root_window = None  # for now: init later in tabbed_qt_window
        if deserialize is not None:
            logger.debug("Deserializing PlotCollection from " + deserialize +
                         "...")
            self.figures = pickle.load(open(deserialize, 'rb'))

    def __str__(self):
        return self.title + " (" + str(len(self.figures)) + " figure(s))"

    def add_figure(self, name, fig):
        fig.tight_layout()
        self.figures[name] = fig

    def tabbed_qt4_window(self):
        from PyQt4 import QtGui
        from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg, NavigationToolbar2QT
        # mpl backend can already create instance
        # https://stackoverflow.com/a/40031190
        app = QtGui.QApplication.instance()
        if app is None:
            app = QtGui.QApplication([self.title])
        self.root_window = QtGui.QTabWidget()
        self.root_window.setWindowTitle(self.title)
        for name, fig in self.figures.items():
            tab = QtGui.QWidget(self.root_window)
            tab.canvas = FigureCanvasQTAgg(fig)
            vbox = QtGui.QVBoxLayout(tab)
            vbox.addWidget(tab.canvas)
            toolbar = NavigationToolbar2QT(tab.canvas, tab)
            vbox.addWidget(toolbar)
            tab.setLayout(vbox)
            for axes in fig.get_axes():
                if isinstance(axes, Axes3D):
                    # must explicitly allow mouse dragging for 3D plots
                    axes.mouse_init()
            self.root_window.addTab(tab, name)
        self.root_window.show()
        app.exec_()

    def tabbed_qt5_window(self):
        from PyQt5 import QtGui, QtWidgets
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
        # mpl backend can already create instance
        # https://stackoverflow.com/a/40031190
        app = QtGui.QGuiApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([self.title])
        self.root_window = QtWidgets.QTabWidget()
        self.root_window.setWindowTitle(self.title)
        for name, fig in self.figures.items():
            tab = QtWidgets.QWidget(self.root_window)
            tab.canvas = FigureCanvasQTAgg(fig)
            vbox = QtWidgets.QVBoxLayout(tab)
            vbox.addWidget(tab.canvas)
            toolbar = NavigationToolbar2QT(tab.canvas, tab)
            vbox.addWidget(toolbar)
            tab.setLayout(vbox)
            for axes in fig.get_axes():
                if isinstance(axes, Axes3D):
                    # must explicitly allow mouse dragging for 3D plots
                    axes.mouse_init()
            self.root_window.addTab(tab, name)
        self.root_window.show()
        app.exec_()

    def tabbed_tk_window(self):
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
        import sys
        if sys.version_info[0] < 3:
            import Tkinter as tkinter
            import ttk
        else:
            import tkinter
            from tkinter import ttk
        self.root_window = tkinter.Tk()
        self.root_window.title(self.title)
        # quit if the window is deleted
        self.root_window.protocol("WM_DELETE_WINDOW", self.root_window.quit)
        nb = ttk.Notebook(self.root_window)
        nb.grid(row=1, column=0, sticky='NESW')
        for name, fig in self.figures.items():
            fig.tight_layout()
            tab = ttk.Frame(nb)
            canvas = FigureCanvasTkAgg(self.figures[name], master=tab)
            canvas.draw()
            canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH,
                                        expand=True)
            toolbar = NavigationToolbar2Tk(canvas, tab)
            toolbar.update()
            canvas._tkcanvas.pack(side=tkinter.TOP, fill=tkinter.BOTH,
                                  expand=True)
            for axes in fig.get_axes():
                if isinstance(axes, Axes3D):
                    # must explicitly allow mouse dragging for 3D plots
                    axes.mouse_init()
            nb.add(tab, text=name)
        nb.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=True)
        self.root_window.mainloop()
        self.root_window.destroy()

    def show(self):
        if len(self.figures.keys()) == 0:
            return
        if not SETTINGS.plot_split:
            if SETTINGS.plot_backend.lower() == "qt4agg":
                self.tabbed_qt4_window()
            elif SETTINGS.plot_backend.lower() == "qt5agg":
                self.tabbed_qt5_window()
            elif SETTINGS.plot_backend.lower() == "tkagg":
                self.tabbed_tk_window()
            else:
                plt.show()
        else:
            plt.show()

    def serialize(self, dest, confirm_overwrite=True):
        logger.debug("Serializing PlotCollection to " + dest + "...")
        if confirm_overwrite and not user.check_and_confirm_overwrite(dest):
            return
        else:
            pickle.dump(self.figures, open(dest, 'wb'))

    def export(self, file_path, confirm_overwrite=True):
        fmt = SETTINGS.plot_export_format.lower()
        if fmt == "pdf" and not SETTINGS.plot_split:
            if confirm_overwrite and not user.check_and_confirm_overwrite(
                    file_path):
                return
            import matplotlib.backends.backend_pdf
            pdf = matplotlib.backends.backend_pdf.PdfPages(file_path)
            for name, fig in self.figures.items():
                # fig.tight_layout()  # TODO
                pdf.savefig(fig)
            pdf.close()
            logger.info("Plots saved to " + file_path)
        else:
            for name, fig in self.figures.items():
                base, ext = os.path.splitext(file_path)
                dest = base + '_' + name + ext
                if confirm_overwrite and not user.check_and_confirm_overwrite(
                        dest):
                    return
                fig.tight_layout()
                fig.savefig(dest, fmt=fmt)
                logger.info("Plot saved to " + dest)


def set_aspect_equal_3d(ax):
    """
    kudos to https://stackoverflow.com/a/35126679
    :param ax: matplotlib 3D axes object
    """
    xlim = ax.get_xlim3d()
    ylim = ax.get_ylim3d()
    zlim = ax.get_zlim3d()

    from numpy import mean
    xmean = mean(xlim)
    ymean = mean(ylim)
    zmean = mean(zlim)

    plot_radius = max([
        abs(lim - mean_)
        for lims, mean_ in ((xlim, xmean), (ylim, ymean), (zlim, zmean))
        for lim in lims
    ])

    ax.set_xlim3d([xmean - plot_radius, xmean + plot_radius])
    ax.set_ylim3d([ymean - plot_radius, ymean + plot_radius])
    ax.set_zlim3d([zmean - plot_radius, zmean + plot_radius])


def prepare_axis(fig, plot_mode=PlotMode.xy, subplot_arg="111"):
    """
    prepares an axis according to the plot mode (for trajectory plotting)
    :param fig: matplotlib figure object
    :param plot_mode: PlotMode
    :param subplot_arg: optional if using subplots - the subplot id (e.g. '122')
    :return: the matplotlib axis
    """
    if plot_mode == PlotMode.xyz:
        ax = fig.add_subplot(subplot_arg, projection="3d")
    else:
        ax = fig.add_subplot(subplot_arg)
        ax.axis("equal")
    if plot_mode in {PlotMode.xy, PlotMode.xz, PlotMode.xyz}:
        xlabel = "$x$ (m)"
    elif plot_mode in {PlotMode.yz, PlotMode.yx}:
        xlabel = "$y$ (m)"
    else:
        xlabel = "$z$ (m)"
    if plot_mode in {PlotMode.xy, PlotMode.zy, PlotMode.xyz}:
        ylabel = "$y$ (m)"
    elif plot_mode in {PlotMode.zx, PlotMode.yx}:
        ylabel = "$x$ (m)"
    else:
        ylabel = "$z$ (m)"
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if plot_mode == PlotMode.xyz:
        ax.set_zlabel('$z$ (m)')
    if SETTINGS.plot_invert_xaxis:
        plt.gca().invert_xaxis()
    if SETTINGS.plot_invert_yaxis:
        plt.gca().invert_yaxis()
    return ax


def plot_mode_to_idx(plot_mode):
    if plot_mode == PlotMode.xy or plot_mode == PlotMode.xyz:
        x_idx = 0
        y_idx = 1
    elif plot_mode == PlotMode.xz:
        x_idx = 0
        y_idx = 2
    elif plot_mode == PlotMode.yx:
        x_idx = 1
        y_idx = 0
    elif plot_mode == PlotMode.yz:
        x_idx = 1
        y_idx = 2
    elif plot_mode == PlotMode.zx:
        x_idx = 2
        y_idx = 0
    elif plot_mode == PlotMode.zy:
        x_idx = 2
        y_idx = 1
    z_idx = 2 if plot_mode == PlotMode.xyz else None
    return x_idx, y_idx, z_idx


def traj(ax, plot_mode, traj, style='-', color='black', label="", alpha=1.0):
    """
    plot a path/trajectory based on xyz coordinates into an axis
    :param ax: the matplotlib axis
    :param plot_mode: PlotMode
    :param traj: trajectory.PosePath3D or trajectory.PoseTrajectory3D object
    :param style: matplotlib line style
    :param color: matplotlib color
    :param label: label (for legend)
    :param alpha: alpha value for transparency
    """
    x_idx, y_idx, z_idx = plot_mode_to_idx(plot_mode)
    x = traj.positions_xyz[:, x_idx]
    y = traj.positions_xyz[:, y_idx]
    if plot_mode == PlotMode.xyz:
        z = traj.positions_xyz[:, z_idx]
        ax.plot(x, y, z, style, color=color, label=label, alpha=alpha)
        if SETTINGS.plot_xyz_realistic:
            set_aspect_equal_3d(ax)
    else:
        ax.plot(x, y, style, color=color, label=label, alpha=alpha)
    if label:
        ax.legend(frameon=True)


def colored_line_collection(xyz, colors, plot_mode=PlotMode.xy,
                            linestyles="solid", step=1):
    if len(xyz) / step != len(colors):
        raise PlotException(
            "color values don't have correct length: %d vs. %d" %
            (len(xyz) / step, len(colors)))
    x_idx, y_idx, z_idx = plot_mode_to_idx(plot_mode)
    xs = [[x_1, x_2]
          for x_1, x_2 in zip(xyz[:-1:step, x_idx], xyz[1::step, x_idx])]
    ys = [[x_1, x_2]
          for x_1, x_2 in zip(xyz[:-1:step, y_idx], xyz[1::step, y_idx])]
    if plot_mode == PlotMode.xyz:
        zs = [[x_1, x_2]
              for x_1, x_2 in zip(xyz[:-1:step, z_idx], xyz[1::step, z_idx])]
        segs = [list(zip(x, y, z)) for x, y, z in zip(xs, ys, zs)]
        line_collection = art3d.Line3DCollection(segs, colors=colors,
                                                 linestyles=linestyles)
    else:
        segs = [list(zip(x, y)) for x, y in zip(xs, ys)]
        line_collection = LineCollection(segs, colors=colors,
                                         linestyle=linestyles)
    return line_collection


def traj_colormap(ax, traj, array, plot_mode, min_map, max_map, title=""):
    """
    color map a path/trajectory in xyz coordinates according to
    an array of values
    :param ax: plot axis
    :param traj: trajectory.PosePath3D or trajectory.PoseTrajectory3D object
    :param array: Nx1 array of values used for color mapping
    :param plot_mode: PlotMode
    :param min_map: lower bound value for color mapping
    :param max_map: upper bound value for color mapping
    :param title: plot title
    """
    pos = traj.positions_xyz
    norm = mpl.colors.Normalize(vmin=min_map, vmax=max_map, clip=True)
    mapper = cm.ScalarMappable(
        norm=norm,
        cmap=SETTINGS.plot_trajectory_cmap)  # cm.*_r is reversed cmap
    mapper.set_array(array)
    colors = [mapper.to_rgba(a) for a in array]
    line_collection = colored_line_collection(pos, colors, plot_mode)
    ax.add_collection(line_collection)
    if plot_mode == PlotMode.xyz:
        ax.set_zlim(
            np.amin(traj.positions_xyz[:, 2]),
            np.amax(traj.positions_xyz[:, 2]))
        if SETTINGS.plot_xyz_realistic:
            set_aspect_equal_3d(ax)
    fig = plt.gcf()
    cbar = fig.colorbar(
        mapper, ticks=[min_map, (max_map - (max_map - min_map) / 2), max_map])
    cbar.ax.set_yticklabels([
        "{0:0.3f}".format(min_map),
        "{0:0.3f}".format(max_map - (max_map - min_map) / 2),
        "{0:0.3f}".format(max_map)
    ])
    if title:
        ax.legend(frameon=True)
        plt.title(title)


def draw_coordinate_axes(ax, traj, plot_mode, marker_scale=0.1, x_color="r",
                         y_color="g", z_color="b"):
    """
    Draws a coordinate frame axis for each pose of a trajectory.
    :param ax: plot axis
    :param traj: trajectory.PosePath3D or trajectory.PoseTrajectory3D object
    :param plot_mode: PlotMode value
    :param marker_scale: affects the size of the marker (1. * marker_scale)
    :param x_color: color of the x-axis
    :param x_color: color of the y-axis
    :param x_color: color of the z-axis
    """
    if marker_scale <= 0:
        return

    unit_x = np.array([1 * marker_scale, 0, 0, 1])
    unit_y = np.array([0, 1 * marker_scale, 0, 1])
    unit_z = np.array([0, 0, 1 * marker_scale, 1])

    # Transform start/end vertices of each axis to global frame.
    x_vertices = np.array([[p[:3, 3], p.dot(unit_x)[:3]]
                           for p in traj.poses_se3])
    y_vertices = np.array([[p[:3, 3], p.dot(unit_y)[:3]]
                           for p in traj.poses_se3])
    z_vertices = np.array([[p[:3, 3], p.dot(unit_z)[:3]]
                           for p in traj.poses_se3])

    n = traj.num_poses
    # Concatenate all line segment vertices in order x, y, z.
    vertices = np.concatenate((x_vertices, y_vertices, z_vertices)).reshape(
        (n * 2 * 3, 3))
    # Concatenate all colors per line segment in order x, y, z.
    colors = np.array(n * [x_color] + n * [y_color] + n * [z_color])

    rgb_axes = colored_line_collection(vertices, colors, plot_mode, step=2)
    ax.add_collection(rgb_axes)


def traj_xyz(axarr, traj, style='-', color='black', label="", alpha=1.0,
             start_timestamp=None):
    """
    plot a path/trajectory based on xyz coordinates into an axis
    :param axarr: an axis array (for x, y & z)
                  e.g. from 'fig, axarr = plt.subplots(3)'
    :param traj: trajectory.PosePath3D or trajectory.PoseTrajectory3D object
    :param style: matplotlib line style
    :param color: matplotlib color
    :param label: label (for legend)
    :param alpha: alpha value for transparency
    :param start_timestamp: optional start time of the reference
                            (for x-axis alignment)
    """
    if len(axarr) != 3:
        raise PlotException("expected an axis array with 3 subplots - got " +
                            str(len(axarr)))
    if isinstance(traj, trajectory.PoseTrajectory3D):
        x = traj.timestamps - (traj.timestamps[0]
                               if start_timestamp is None else start_timestamp)
        xlabel = "$t$ (s)"
    else:
        x = range(0, len(traj.positions_xyz))
        xlabel = "index"
    ylabels = ["$x$ (m)", "$y$ (m)", "$z$ (m)"]
    for i in range(0, 3):
        axarr[i].plot(x, traj.positions_xyz[:, i], style, color=color,
                      label=label, alpha=alpha)
        axarr[i].set_ylabel(ylabels[i])
    axarr[2].set_xlabel(xlabel)
    if label:
        axarr[0].legend(frameon=True)


def traj_rpy(axarr, traj, style='-', color='black', label="", alpha=1.0,
             start_timestamp=None):
    """
    plot a path/trajectory's Euler RPY angles into an axis
    :param axarr: an axis array (for R, P & Y)
                  e.g. from 'fig, axarr = plt.subplots(3)'
    :param traj: trajectory.PosePath3D or trajectory.PoseTrajectory3D object
    :param style: matplotlib line style
    :param color: matplotlib color
    :param label: label (for legend)
    :param alpha: alpha value for transparency
    :param start_timestamp: optional start time of the reference
                            (for x-axis alignment)
    """
    if len(axarr) != 3:
        raise PlotException("expected an axis array with 3 subplots - got " +
                            str(len(axarr)))
    angles = traj.get_orientations_euler(SETTINGS.euler_angle_sequence)
    if isinstance(traj, trajectory.PoseTrajectory3D):
        x = traj.timestamps - (traj.timestamps[0]
                               if start_timestamp is None else start_timestamp)
        xlabel = "$t$ (s)"
    else:
        x = range(0, len(angles))
        xlabel = "index"
    ylabels = ["$roll$ (deg)", "$pitch$ (deg)", "$yaw$ (deg)"]
    for i in range(0, 3):
        axarr[i].plot(x, np.rad2deg(angles[:, i]), style, color=color,
                      label=label, alpha=alpha)
        axarr[i].set_ylabel(ylabels[i])
    axarr[2].set_xlabel(xlabel)
    if label:
        axarr[0].legend(frameon=True)


def trajectories(fig, trajectories, plot_mode=PlotMode.xy, title="",
                 subplot_arg="111"):
    """
    high-level function for plotting multiple trajectories
    :param fig: matplotlib figure
    :param trajectories: instances or iterables of PosePath3D or derived
    - if it's a dictionary, the keys (names) will be used as labels
    :param plot_mode: e.g. plot.PlotMode.xy
    :param title: optional plot title
    :param subplot_arg: optional matplotlib subplot ID if used as subplot
    """
    ax = prepare_axis(fig, plot_mode)
    cmap_colors = None
    if SETTINGS.plot_multi_cmap.lower() != "none":
        cmap = getattr(cm, SETTINGS.plot_multi_cmap)
        cmap_colors = iter(cmap(np.linspace(0, 1, len(trajectories))))

    # helper function
    def draw(t, name=""):
        if cmap_colors is None:
            color = next(ax._get_lines.prop_cycler)['color']
        else:
            color = next(cmap_colors)
        if SETTINGS.plot_usetex:
            name = name.replace("_", "\\_")
        traj(ax, plot_mode, t, '-', color, name)

    if isinstance(trajectories, trajectory.PosePath3D):
        draw(trajectories)
    elif isinstance(trajectories, dict):
        for name, t in trajectories.items():
            draw(t, name)
    else:
        for t in trajectories:
            draw(t)


def error_array(fig, err_array, x_array=None, statistics=None, threshold=None,
                cumulative=False, color='grey', name="error", title="",
                xlabel="index", ylabel=None, subplot_arg='111', linestyle="-",
                marker=None):
    """
    high-level function for plotting raw error values of a metric
    :param fig: matplotlib figure
    :param err_array: an nx1 array of values
    :param x_array: an nx1 array of x-axis values
    :param statistics: optional dictionary of {metrics.StatisticsType: value}
    :param threshold: optional value for horizontal threshold line
    :param cumulative: set to True for cumulative plot
    :param name: optional name of the value array
    :param title: optional plot title
    :param xlabel: optional x-axis label
    :param ylabel: optional y-axis label
    :param subplot_arg: optional matplotlib subplot ID if used as subplot
    :param linestyle: matplotlib linestyle
    :param marker: optional matplotlib marker style for points
    :return: the matplotlib figure with the plot
    """
    ax = fig.add_subplot(subplot_arg)
    if cumulative:
        if x_array:
            ax.plot(x_array, np.cumsum(err_array), linestyle=linestyle,
                    marker=marker, color=color, label=name)
        else:
            ax.plot(np.cumsum(err_array), linestyle=linestyle, marker=marker,
                    color=color, label=name)
    else:
        if x_array:
            ax.plot(x_array, err_array, linestyle=linestyle, marker=marker,
                    color=color, label=name)
        else:
            ax.plot(err_array, linestyle=linestyle, marker=marker, color=color,
                    label=name)
    if statistics is not None:
        for stat_name, value in statistics.items():
            color = next(ax._get_lines.prop_cycler)['color']
            if stat_name == "std" and "mean" in statistics:
                mean, std = statistics["mean"], statistics["std"]
                ax.axhspan(mean - std / 2, mean + std / 2, color=color,
                           alpha=0.5, label=stat_name)
            else:
                ax.axhline(y=value, color=color, linewidth=2.0,
                           label=stat_name)
    if threshold is not None:
        ax.axhline(y=threshold, color='red', linestyle='dashed', linewidth=2.0,
                   label="threshold")
    plt.ylabel(ylabel if ylabel else name)
    plt.xlabel(xlabel)
    plt.title(title)
    plt.legend(frameon=True)
    return fig
