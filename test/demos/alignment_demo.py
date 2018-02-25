#!/usr/bin/env python
"""
test/demo for trajectory alignment functions
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

import logging
import sys

from evo.core import trajectory
from evo.tools import plot, file_interface

import evo.core.lie_algebra as lie

import numpy as np
import matplotlib.pyplot as plt

logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.DEBUG)

traj_ref = file_interface.read_kitti_poses_file("../data/KITTI_00_gt.txt")
traj_est = file_interface.read_kitti_poses_file("../data/KITTI_00_ORB.txt")

# add artificial Sim(3) transformation
traj_est.transform(lie.se3(np.eye(3), [0, 0, 0]))
traj_est.scale(0.5)

logging.info("\nUmeyama alignment without scaling")
traj_est_aligned = trajectory.align_trajectory(traj_est, traj_ref)
logging.info("\nUmeyama alignment with scaling")
traj_est_aligned_scaled = trajectory.align_trajectory(traj_est, traj_ref, correct_scale=True)
logging.info("\nUmeyama alignment with scaling only")
traj_est_aligned_only_scaled = trajectory.align_trajectory(traj_est, traj_ref, correct_only_scale=True)

fig = plt.figure(figsize=(8, 8))
# fig.suptitle("Umeyama $\mathrm{Sim}(3)$ alignment")
plot_mode = plot.PlotMode.xz
ax = plot.prepare_axis(fig, plot_mode, subplot_arg='221')  # 122 = 1*2 grid, second
plot.traj(ax, plot_mode, traj_ref, '--', 'gray')#, 'reference')
plot.traj(ax, plot_mode, traj_est, '-', 'blue')#, 'not aligned')
fig.axes.append(ax)
#plt.legend()
plt.title('not aligned')
ax = plot.prepare_axis(fig, plot_mode, subplot_arg='222')
plot.traj(ax, plot_mode, traj_ref, '--', 'gray')#, 'reference')
plot.traj(ax, plot_mode, traj_est_aligned, '-', 'blue')#, '$\mathrm{SE}(3)$ alignment')
fig.axes.append(ax)
#plt.legend()
plt.title('$\mathrm{SE}(3)$ alignment')
ax = plot.prepare_axis(fig, plot_mode, subplot_arg='223')
plot.traj(ax, plot_mode, traj_ref, '--', 'gray')#, 'reference')
plot.traj(ax, plot_mode, traj_est_aligned_scaled, '-', 'blue')#, '$\mathrm{Sim}(3)$ alignment')
fig.axes.append(ax)
#plt.legend()
plt.title('$\mathrm{Sim}(3)$ alignment')
ax = plot.prepare_axis(fig, plot_mode, subplot_arg='224')
plot.traj(ax, plot_mode, traj_ref, '--', 'gray')#, 'reference')
plot.traj(ax, plot_mode, traj_est_aligned_only_scaled, '-', 'blue')#, 'only scaled')
fig.axes.append(ax)
#plt.legend()
plt.title('only scaled')
fig.tight_layout()
plt.show()
