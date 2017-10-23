#!/usr/bin/env python

from __future__ import print_function

print("loading required evo modules")
from evo.algorithms import trajectory, sync, metrics
from evo.tools import file_interface

print("loading trajectories")
traj_ref = file_interface.read_tum_trajectory_file("../test/data/fr2_desk_groundtruth.txt")
traj_est = file_interface.read_tum_trajectory_file("../test/data/fr2_desk_ORB.txt")

print("registering trajectories")
traj_ref, traj_est = sync.associate_trajectories(traj_ref, traj_est)
traj_est = trajectory.align_trajectory(traj_est, traj_ref, correct_scale=False)

print("calculating APE")
data = (traj_ref, traj_est)
ape_metric = metrics.APE(metrics.PoseRelation.translation_part)
ape_metric.process_data(data)
ape_statistics = ape_metric.get_all_statistics()
print("mean:", ape_statistics["mean"])

print("loading plot modules")
from evo.tools import plot
import matplotlib.pyplot as plt

print("plotting")
plot_collection = plot.PlotCollection("Example")
# metric values
fig_1 = plt.figure(figsize=(8, 8))
plot.error_array(fig_1, ape_metric.error, statistics=ape_statistics,
                 name="APE", title=str(ape_metric))
plot_collection.add_figure("raw", fig_1)

# trajectory colormapped with error
fig_2 = plt.figure(figsize=(8, 8))
plot_mode = plot.PlotMode.xy
ax = plot.prepare_axis(fig_2, plot_mode)
plot.traj(ax, plot_mode, traj_ref, '--', 'gray', 'reference')
plot.traj_colormap(ax, traj_est, ape_metric.error, plot_mode,
                   min_map=ape_statistics["min"], max_map=ape_statistics["max"],
                   title="APE mapped onto trajectory")
plot_collection.add_figure("traj (error)", fig_2)

# trajectory colormapped with speed
fig_3 = plt.figure(figsize=(8, 8))
plot_mode = plot.PlotMode.xy
ax = plot.prepare_axis(fig_3, plot_mode)
speeds = [trajectory.calc_speed(traj_est.positions_xyz[i], traj_est.positions_xyz[i + 1],
                    traj_est.timestamps[i], traj_est.timestamps[i + 1])
                    for i in range(len(traj_est.positions_xyz) - 1)]
speeds.append(0)
plot.traj(ax, plot_mode, traj_ref, '--', 'gray', 'reference')
plot.traj_colormap(ax, traj_est, speeds, plot_mode,
                   min_map=min(speeds), max_map=max(speeds),
                   title="speed mapped onto trajectory")
fig_3.axes.append(ax)
plot_collection.add_figure("traj (speed)", fig_3)

plot_collection.show()
