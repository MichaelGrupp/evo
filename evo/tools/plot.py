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

import os
import collections
import logging
import pickle
import typing
from enum import Enum

import matplotlib as mpl
from evo.tools.settings import SETTINGS

mpl.use(SETTINGS.plot_backend)
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import mpl_toolkits.mplot3d.art3d as art3d
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.backend_bases import FigureCanvasBase
from matplotlib.collections import LineCollection
from matplotlib.transforms import Affine2D

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

ListOrArray = typing.Union[typing.Sequence[float], np.ndarray]


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
    def __init__(self, title: str = "",
                 deserialize: typing.Optional[str] = None):
        self.title = " ".join(title.splitlines())  # one line title
        self.figures = collections.OrderedDict()  # remember placement order
        # hack to avoid premature garbage collection when serializing with Qt
        # initialized later in tabbed_{qt, tk}_window
        self.root_window: typing.Optional[typing.Any] = None
        if deserialize is not None:
            logger.debug("Deserializing PlotCollection from " + deserialize +
                         "...")
            self.figures = pickle.load(open(deserialize, 'rb'))

    def __str__(self) -> str:
        return self.title + " (" + str(len(self.figures)) + " figure(s))"

    def add_figure(self, name: str, fig: plt.Figure) -> None:
        fig.tight_layout()
        self.figures[name] = fig

    @staticmethod
    def _bind_mouse_events_to_canvas(axes: Axes3D, canvas: FigureCanvasBase):
        axes.mouse_init()
        # Event binding was possible through mouse_init() up to matplotlib 3.2.
        # In 3.3.0 this was moved, so we are forced to do it here.
        if mpl.__version__ >= "3.3.0":
            canvas.mpl_connect("button_press_event", axes._button_press)
            canvas.mpl_connect("button_release_event", axes._button_release)
            canvas.mpl_connect("motion_notify_event", axes._on_move)

    def tabbed_qt5_window(self) -> None:
        from PyQt5 import QtGui, QtWidgets
        from matplotlib.backends.backend_qt5agg import (FigureCanvasQTAgg,
                                                        NavigationToolbar2QT)
        # mpl backend can already create instance
        # https://stackoverflow.com/a/40031190
        app = QtGui.QGuiApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([self.title])
        self.root_window = QtWidgets.QTabWidget()
        self.root_window.setWindowTitle(self.title)
        sizes = [(0, 0)]
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
                    self._bind_mouse_events_to_canvas(axes, tab.canvas)
            self.root_window.addTab(tab, name)
            sizes.append(tab.canvas.get_width_height())
        # Resize window to avoid clipped axes.
        self.root_window.resize(*max(sizes))
        self.root_window.show()
        app.exec_()

    def tabbed_tk_window(self) -> None:
        from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                                       NavigationToolbar2Tk)
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
                    self._bind_mouse_events_to_canvas(axes, canvas)
            nb.add(tab, text=name)
        nb.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=True)
        self.root_window.mainloop()
        self.root_window.destroy()

    def show(self) -> None:
        if len(self.figures.keys()) == 0:
            return
        if not SETTINGS.plot_split:
            if SETTINGS.plot_backend.lower() == "qt5agg":
                self.tabbed_qt5_window()
            elif SETTINGS.plot_backend.lower() == "tkagg":
                self.tabbed_tk_window()
            else:
                plt.show()
        else:
            plt.show()

    def serialize(self, dest: str, confirm_overwrite: bool = True) -> None:
        logger.debug("Serializing PlotCollection to " + dest + "...")
        if confirm_overwrite and not user.check_and_confirm_overwrite(dest):
            return
        else:
            pickle.dump(self.figures, open(dest, 'wb'))

    def export(self, file_path: str, confirm_overwrite: bool = True) -> None:
        base, ext = os.path.splitext(file_path)
        if ext == ".pdf" and not SETTINGS.plot_split:
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
                dest = base + '_' + name + ext
                if confirm_overwrite and not user.check_and_confirm_overwrite(
                        dest):
                    return
                fig.tight_layout()
                fig.savefig(dest)
                logger.info("Plot saved to " + dest)


def set_aspect_equal_3d(ax: plt.Axes) -> None:
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


def prepare_axis(fig: plt.Figure, plot_mode: PlotMode = PlotMode.xy,
                 subplot_arg: int = 111) -> plt.Axes:
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


def plot_mode_to_idx(
        plot_mode: PlotMode) -> typing.Tuple[int, int, typing.Optional[int]]:
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


def traj(ax: plt.Axes, plot_mode: PlotMode, traj: trajectory.PosePath3D,
         style: str = '-', color: str = 'black', label: str = "",
         alpha: float = 1.0) -> None:
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


def colored_line_collection(
    xyz: np.ndarray, colors: ListOrArray, plot_mode: PlotMode = PlotMode.xy,
    linestyles: str = "solid", step: int = 1, alpha: float = 1.
) -> typing.Union[LineCollection, art3d.LineCollection]:
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
        segs_3d = [list(zip(x, y, z)) for x, y, z in zip(xs, ys, zs)]
        line_collection = art3d.Line3DCollection(segs_3d, colors=colors,
                                                 alpha=alpha,
                                                 linestyles=linestyles)
    else:
        segs_2d = [list(zip(x, y)) for x, y in zip(xs, ys)]
        line_collection = LineCollection(segs_2d, colors=colors, alpha=alpha,
                                         linestyle=linestyles)
    return line_collection


def traj_colormap(ax: plt.Axes, traj: trajectory.PosePath3D,
                  array: ListOrArray, plot_mode: PlotMode, min_map: float,
                  max_map: float, title: str = "",
                  fig: typing.Optional[mpl.figure.Figure] = None) -> None:
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
    :param fig: plot figure. Obtained with plt.gcf() if none is specified
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
    ax.autoscale_view(True, True, True)
    if plot_mode == PlotMode.xyz:
        ax.set_zlim(np.amin(traj.positions_xyz[:, 2]),
                    np.amax(traj.positions_xyz[:, 2]))
        if SETTINGS.plot_xyz_realistic:
            set_aspect_equal_3d(ax)
    if fig is None:
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
        ax.set_title(title)


def draw_coordinate_axes(ax: plt.Figure, traj: trajectory.PosePath3D,
                         plot_mode: PlotMode, marker_scale: float = 0.1,
                         x_color: str = "r", y_color: str = "g",
                         z_color: str = "b") -> None:
    """
    Draws a coordinate frame axis for each pose of a trajectory.
    :param ax: plot axis
    :param traj: trajectory.PosePath3D or trajectory.PoseTrajectory3D object
    :param plot_mode: PlotMode value
    :param marker_scale: affects the size of the marker (1. * marker_scale)
    :param x_color: color of the x-axis
    :param y_color: color of the y-axis
    :param z_color: color of the z-axis
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

    markers = colored_line_collection(vertices, colors, plot_mode, step=2)
    ax.add_collection(markers)


def draw_correspondence_edges(ax: plt.Axes, traj_1: trajectory.PosePath3D,
                              traj_2: trajectory.PosePath3D,
                              plot_mode: PlotMode, style: str = '-',
                              color: str = "black", alpha: float = 1.) -> None:
    """
    Draw edges between corresponding poses of two trajectories.
    Trajectories must be synced, i.e. having the same number of poses.
    :param ax: plot axis
    :param traj_{1,2}: trajectory.PosePath3D or trajectory.PoseTrajectory3D
    :param plot_mode: PlotMode value
    :param style: matplotlib line style
    :param color: matplotlib color
    :param alpha: alpha value for transparency
    """
    if not traj_1.num_poses == traj_2.num_poses:
        raise PlotException(
            "trajectories must have same length to draw pose correspondences"
            " - try to synchronize them first")
    n = traj_1.num_poses
    interweaved_positions = np.empty((n * 2, 3))
    interweaved_positions[0::2, :] = traj_1.positions_xyz
    interweaved_positions[1::2, :] = traj_2.positions_xyz
    colors = np.array(n * [color])
    markers = colored_line_collection(interweaved_positions, colors, plot_mode,
                                      step=2, alpha=alpha, linestyles=style)
    ax.add_collection(markers)


def traj_xyz(axarr: np.ndarray, traj: trajectory.PosePath3D, style: str = '-',
             color: str = 'black', label: str = "", alpha: float = 1.0,
             start_timestamp: typing.Optional[float] = None) -> None:
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
        if start_timestamp:
            x = traj.timestamps - start_timestamp
        else:
            x = traj.timestamps
        xlabel = "$t$ (s)"
    else:
        x = np.arange(0, len(traj.positions_xyz))
        xlabel = "index"
    ylabels = ["$x$ (m)", "$y$ (m)", "$z$ (m)"]
    for i in range(0, 3):
        axarr[i].plot(x, traj.positions_xyz[:, i], style, color=color,
                      label=label, alpha=alpha)
        axarr[i].set_ylabel(ylabels[i])
    axarr[2].set_xlabel(xlabel)
    if label:
        axarr[0].legend(frameon=True)


def traj_rpy(axarr: np.ndarray, traj: trajectory.PosePath3D, style: str = '-',
             color: str = 'black', label: str = "", alpha: float = 1.0,
             start_timestamp: typing.Optional[float] = None) -> None:
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
        if start_timestamp:
            x = traj.timestamps - start_timestamp
        else:
            x = traj.timestamps
        xlabel = "$t$ (s)"
    else:
        x = np.arange(0, len(angles))
        xlabel = "index"
    ylabels = ["$roll$ (deg)", "$pitch$ (deg)", "$yaw$ (deg)"]
    for i in range(0, 3):
        axarr[i].plot(x, np.rad2deg(angles[:, i]), style, color=color,
                      label=label, alpha=alpha)
        axarr[i].set_ylabel(ylabels[i])
    axarr[2].set_xlabel(xlabel)
    if label:
        axarr[0].legend(frameon=True)


def trajectories(fig: plt.Figure, trajectories: typing.Union[
        trajectory.PosePath3D, typing.Sequence[trajectory.PosePath3D],
        typing.Dict[str, trajectory.PosePath3D]], plot_mode=PlotMode.xy,
                 title: str = "", subplot_arg: int = 111) -> None:
    """
    high-level function for plotting multiple trajectories
    :param fig: matplotlib figure
    :param trajectories: instance or container of PosePath3D or derived
    - if it's a dictionary, the keys (names) will be used as labels
    :param plot_mode: e.g. plot.PlotMode.xy
    :param title: optional plot title
    :param subplot_arg: optional matplotlib subplot ID if used as subplot
    """
    ax = prepare_axis(fig, plot_mode, subplot_arg)
    cmap_colors = None
    if SETTINGS.plot_multi_cmap.lower() != "none" and isinstance(
            trajectories, collections.Iterable):
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


def error_array(ax: plt.Axes, err_array: ListOrArray,
                x_array: typing.Optional[ListOrArray] = None,
                statistics: typing.Optional[typing.Dict[str, float]] = None,
                threshold: float = None, cumulative: bool = False,
                color: str = 'grey', name: str = "error", title: str = "",
                xlabel: str = "index", ylabel: typing.Optional[str] = None,
                subplot_arg: int = 111, linestyle: str = "-",
                marker: typing.Optional[str] = None):
    """
    high-level function for plotting raw error values of a metric
    :param fig: matplotlib axes
    :param err_array: an nx1 array of values
    :param x_array: an nx1 array of x-axis values
    :param statistics: optional dictionary of {metrics.StatisticsType.value: value}
    :param threshold: optional value for horizontal threshold line
    :param cumulative: set to True for cumulative plot
    :param name: optional name of the value array
    :param title: optional plot title
    :param xlabel: optional x-axis label
    :param ylabel: optional y-axis label
    :param subplot_arg: optional matplotlib subplot ID if used as subplot
    :param linestyle: matplotlib linestyle
    :param marker: optional matplotlib marker style for points
    """
    if cumulative:
        if x_array is not None:
            ax.plot(x_array, np.cumsum(err_array), linestyle=linestyle,
                    marker=marker, color=color, label=name)
        else:
            ax.plot(np.cumsum(err_array), linestyle=linestyle, marker=marker,
                    color=color, label=name)
    else:
        if x_array is not None:
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


def ros_map(ax: plt.Axes, yaml_path: str, plot_mode: PlotMode,
            cmap: str = "Greys_r",
            mask_unknown_value: int = SETTINGS.ros_map_unknown_cell_value,
            alpha: float = SETTINGS.ros_map_alpha_value) -> None:
    """
    Inserts an image of an 2D ROS map into the plot axis.
    See: http://wiki.ros.org/map_server#Map_format
    :param ax: 2D matplotlib axes
    :param plot_mode: a 2D PlotMode
    :param yaml_path: yaml file that contains the metadata of the map image
    :param cmap: color map used to map scalar data to colors
                 (only for single channel image)
    :param mask_unknown_value: uint8 value that represents unknown cells.
                               If specified, these cells will be masked out.
                               If set to None or False, nothing will be masked.
    """
    import yaml

    if isinstance(ax, Axes3D):
        raise PlotException("ros_map can't be drawn into a 3D axis")
    if plot_mode in {PlotMode.xz, PlotMode.yz, PlotMode.zx, PlotMode.zy}:
        # Image lies in xy / yx plane, nothing to see here.
        return
    x_idx, y_idx, _ = plot_mode_to_idx(plot_mode)

    with open(yaml_path) as f:
        metadata = yaml.safe_load(f)

    # Load map image, mask unknown cells if desired.
    image_path = metadata["image"]
    if not os.path.isabs(image_path):
        image_path = os.path.join(os.path.dirname(yaml_path), image_path)
    image = plt.imread(image_path)

    if mask_unknown_value:
        # Support masking with single channel or RGB images, 8bit or normalized
        # float. For RGB all channels must be equal to mask_unknown_value.
        n_channels = image.shape[2] if len(image.shape) > 2 else 1
        if image.dtype == np.uint8:
            mask_unknown_value_rgb = np.array([mask_unknown_value] * 3,
                                              dtype=np.uint8)
        elif image.dtype == np.float32:
            mask_unknown_value_rgb = np.array([mask_unknown_value / 255.0] * 3,
                                              dtype=np.float32)
        if n_channels == 1:
            image = np.ma.masked_where(image == mask_unknown_value_rgb[0],
                                       image)
        elif n_channels == 3:
            # imshow ignores masked RGB regions for some reason,
            # add an alpha channel instead.
            # https://stackoverflow.com/questions/60561680
            mask = np.all(image == mask_unknown_value_rgb, 2)
            max_alpha = 255 if image.dtype == np.uint8 else 1.
            image = np.dstack((image, (~mask).astype(image.dtype) * max_alpha))
        else:
            # E.g. if there's already an alpha channel it doesn't make sense.
            logger.warn("masking unknown map cells is not supported with "
                        "{}-channel {} pixels".format(n_channels, image.dtype))

    # Squeeze extent to reflect metric coordinates.
    resolution = metadata["resolution"]
    n_rows, n_cols = image.shape[x_idx], image.shape[y_idx]
    extent = [0, n_cols * resolution, 0, n_rows * resolution]
    if plot_mode == PlotMode.yx:
        image = np.rot90(image)
        image = np.fliplr(image)
    ax_image = ax.imshow(image, origin="upper", cmap=cmap, extent=extent,
                         zorder=1, alpha=alpha)

    # Transform map frame to plot axis origin.
    map_to_pixel_origin = Affine2D()
    map_to_pixel_origin.translate(metadata["origin"][x_idx],
                                  metadata["origin"][y_idx])
    angle = metadata["origin"][2]
    if plot_mode == PlotMode.yx:
        # Rotation axis (z) points downwards.
        angle *= -1
    map_to_pixel_origin.rotate(angle)
    ax_image.set_transform(map_to_pixel_origin + ax.transData)

    # Initially flipped axes are lost for mysterious reasons...
    if SETTINGS.plot_invert_xaxis:
        ax.invert_xaxis()
    if SETTINGS.plot_invert_yaxis:
        ax.invert_yaxis()
