#!/usr/bin/env python

from __future__ import print_function
import copy
import os
import yaml
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from pylab import setp
from shutil import copyfile, move, rmtree, copytree, copy2

from evo.core import trajectory, sync, metrics

Y_MAX_APE_TRANS=[0.3, 0.25, 0.35, 0.5, 0.36, 0.170, 0.16, 0.4, 0.175, 0.24, 0.7]
Y_MAX_RPE_TRANS=[0.028, 0.025, 0.091, 0.21, 0.07, 0.03, 0.04, 0.15, 0.04, 0.06, 0.17]
Y_MAX_RPE_ROT=[0.4, 0.6, 0.35, 1.0, 0.3, 0.6, 1.5, 1.25, 0.6, 1.0, 2.6]

def find_step_of_base(x, base):
    return base * 10**np.floor(np.log10(np.abs(float(x))))

def _set_boxplot_colors(boxplot_object, color):
    setp(boxplot_object['boxes'][0], color=color)
    setp(boxplot_object['caps'][0], color=color)
    setp(boxplot_object['caps'][1], color=color)
    setp(boxplot_object['whiskers'][0], color=color)
    setp(boxplot_object['whiskers'][1], color=color)
    #setp(boxplot_object['fliers'], color=color)
    setp(boxplot_object['medians'][0], color=color)

def draw_boxplot(axis, stats, position, idx_experiment):
    """
        bxpstats : list of dicts
          A list of dictionaries containing stats for each boxplot.
          Required keys are:

          - ``med``: The median (scalar float).

          - ``q1``: The first quartile (25th percentile) (scalar
            float).

          - ``q3``: The third quartile (75th percentile) (scalar
            float).

          - ``whislo``: Lower bound of the lower whisker (scalar
            float).

          - ``whishi``: Upper bound of the upper whisker (scalar
            float).

          Optional keys are:

          - ``mean``: The mean (scalar float). Needed if
            ``showmeans=True``.

          - ``fliers``: Data beyond the whiskers (sequence of floats).
            Needed if ``showfliers=True``.

          - ``cilo`` & ``cihi``: Lower and upper confidence intervals
            about the median. Needed if ``shownotches=True``.

          - ``label``: Name of the dataset (string). If available,
            this will be used a tick label for the boxplot

        positions : array-like, default = [1, 2, ..., n]
          Sets the positions of the boxes. The ticks and limits
          are automatically set to match the positions.
    """
    colors = ['blue', 'black', 'green', 'red', 'mangenta', 'cyan', 'orange']
    bxpstats = []
    bxpstats_a = dict()
    bxpstats_a['med'] = stats['median']
    bxpstats_a['q1'] = stats['q1']
    bxpstats_a['q3'] = stats['q3']
    bxpstats_a['whislo'] = stats['min']
    bxpstats_a['whishi'] = stats['max']
    bxpstats.append(bxpstats_a)
    pb = axis.bxp(bxpstats,
                  positions=position,
                  widths=0.8, vert=True,
                  showcaps=True, showbox=True, showfliers=False, )
    _set_boxplot_colors(pb, colors[idx_experiment])

def draw_rpe_boxplots(output_dir, stats, n_segments):
    """ Draw boxplots from stats:
        which is a list that contains:
            - pipeline type (string) (like S, SP or SPR):
                - "relative_errors":
                    - segment distance (float) (like 10 or 20 etc):
                        - "max"
                        - "min"
                        - "mean"
                        - "median"
                        - "q1"
                        - "q3"
                        - "rmse"
        This function iterates over the pipeline types, and for each pipeline type, it plots
        the metrics achieved for each segment length. So the boxplot has in x-axis
        the number of segments considered, and in y-axis one boxplot per pipeline.
                        """

    colors = ['blue', 'black', 'green', 'red', 'mangenta', 'cyan', 'orange']
    if isinstance(stats, dict):
        n_experiment = len(stats)
        spacing = 1

        # Precompute position of boxplots in plot.
        pos = np.arange(0, n_segments * (n_experiment + spacing), (n_experiment + spacing))

        # Init axes
        # Use different plotting config.
        plt.style.use('default')
        import matplotlib as mpl
        from matplotlib import rc
        import seaborn as sns
        sns.reset_orig()
        mpl.rcParams.update(mpl.rcParamsDefault)
        rc('font',**{'family':'serif','serif':['Cardo'],'size':16})
        rc('text', usetex=True)

        fig = plt.figure(figsize=(6,6))
        ax_pos = fig.add_subplot(211, ylabel='RPE translation [m]')
        ax_yaw = fig.add_subplot(212, ylabel='RPE rotation [deg]', xlabel='Distance travelled [m]')
        dummy_plots_pos = []
        dummy_plots_yaw = []

        idx_experiment = 0
        x_labels = []
        final_max_e_pos=0.0
        final_max_e_yaw=0.0
        segment_lengths = []
        for pipeline_key, errors in sorted(stats.iteritems()):
            # The dummy plots are used to create the legends.
            dummy_plot_pos = ax_pos.plot([1,1], '-', color=colors[idx_experiment])
            dummy_plots_pos.append(dummy_plot_pos[0])
            dummy_plot_yaw = ax_yaw.plot([1,1], '-', color=colors[idx_experiment])
            dummy_plots_yaw.append(dummy_plot_yaw[0])
            x_labels.append(pipeline_key)
            if isinstance(errors, dict):
                assert("relative_errors" in errors)
                # Check that we have the expected number of segments
                assert(n_segments == len(errors['relative_errors']))
                idx_segment = 0
                for segment_length, stats in sorted(errors["relative_errors"].iteritems(), key = lambda item: int(item[0])):
                    segment_lengths.append(segment_length)
                    # Find max value overall, to set max in y-axis
                    max_e_pos = stats["rpe_trans"]["max"]
                    max_e_yaw = stats["rpe_rot"]["max"]
                    #max_e_pos = 10.2+0.02
                    #max_e_yaw = 30.0
                    if max_e_pos > final_max_e_pos:
                        final_max_e_pos = max_e_pos
                    if max_e_yaw > final_max_e_yaw:
                        final_max_e_yaw = max_e_yaw
                    # Draw boxplot
                    draw_boxplot(ax_pos, stats["rpe_trans"], [idx_experiment + pos[idx_segment]],
                                 idx_experiment)
                    draw_boxplot(ax_yaw, stats["rpe_rot"], [idx_experiment + pos[idx_segment]],
                                idx_experiment)
                    idx_segment = idx_segment + 1
            else:
                raise Exception("\033[91mValue in stats should be a dict: " + errors + "\033[99m")
            idx_experiment = idx_experiment + 1

        # Create legend.
        ax_pos.legend(dummy_plots_yaw, x_labels, bbox_to_anchor=(0., 1.02, 1., .102),
                      loc=3, ncol=3, mode='expand', borderaxespad=0.)

        def _ax_formatting(ax, dummy_plots, final_max_e):
            ax.yaxis.grid(ls='--', color='0.7')
            ax.yaxis.set_major_formatter(FuncFormatter(lambda y, pos: '%.2f'%y))
            # ax.xaxis.grid(which='major', visible=True, ls=' ')
            # ax.xaxis.grid(which='minor', visible=False)
            #ax.xaxis.set_major_formatter(plt.NullFormatter())
            ax.set_xticks(pos + 0.5*n_experiment - 0.5)
            ax.set_xticklabels(segment_lengths)
            ax.set_xlim(xmin=pos[0] - 1, xmax=pos[-1] + n_experiment + 0.2)
            ax.set_ylim(ymin=0, ymax=final_max_e)
            # Set yticks every multiple of 5 or 1. (so a tick 0.03 is now 0.00, 0.05,
            # and if 1 then a tick 0.034 is 0.03, 0.04)
            yticks = np.arange(0, final_max_e, find_step_of_base(final_max_e/5, 5))
            if len(yticks) < 4: # 4 is the minimum of yticks that we want.
                ax.set_yticks(np.arange(0, final_max_e, find_step_of_base(final_max_e/5, 1)))
            else:
                ax.set_yticks(yticks)
            for p in dummy_plots:
                p.set_visible(False)

        # give some extra space for the plot...
        final_max_e_pos += 0.05*final_max_e_pos
        final_max_e_yaw += 0.05*final_max_e_yaw
        _ax_formatting(ax_pos, dummy_plots_pos, final_max_e_pos)
        _ax_formatting(ax_yaw, dummy_plots_yaw, final_max_e_yaw)

        fig.savefig(os.path.join(output_dir, 'traj_relative_errors_boxplots.eps'),
                    bbox_inches="tight", format="eps", dpi=1200)
    else:
        raise Exception("\033[91mStats should be a dict: " + stats + "\033[99m")

    # Restore plotting config.
    from evo.tools.settings import SETTINGS
    plt.style.use('seaborn')
    # configure matplotlib and seaborn according to package settings
    sns.set(style=SETTINGS.plot_seaborn_style,
            palette=SETTINGS.plot_seaborn_palette,
            font=SETTINGS.plot_fontfamily,
            font_scale=SETTINGS.plot_fontscale
           )

    rc_params = {
        "lines.linewidth": SETTINGS.plot_linewidth,
        "text.usetex": SETTINGS.plot_usetex,
        "font.family": SETTINGS.plot_fontfamily,
        "font.serif": ['Cardo'],
        "pgf.texsystem": SETTINGS.plot_texsystem
    }
    mpl.rcParams.update(rc_params)

def draw_ape_boxplots(stats, output_dir):
    """ Draw boxplots from stats:
        which is a list that contains:
            - dataset name (string) (like V1_01_easy, MH_01_easy etc):
                - pipeline type (string) (like S, SP or SPR):
                    - "absolute_errors":
                        - "max"
                        - "min"
                        - "mean"
                        - "median"
                        - "q1"
                        - "q3"
                        - "rmse"
        This function iterates over the pipeline types, and for each pipeline type, it plots
        the metrics achieved, as a boxplot. So the boxplot has in x-axis the dataset name,
        and in y-axis one boxplot per pipeline."""
    colors = ['blue', 'black', 'green', 'red', 'mangenta', 'cyan', 'orange']
    if isinstance(stats, dict):
        n_param_values = len(stats)
        n_pipeline_types = len(stats.values()[0])
        spacing = 1

        # Precompute position of boxplots in plot.
        pos = np.arange(0, n_param_values * (n_pipeline_types + spacing),
                        (n_pipeline_types + spacing))

        # Use different plotting config.
        plt.style.use('default')
        import matplotlib as mpl
        from matplotlib import rc
        import seaborn as sns
        sns.reset_orig()
        mpl.rcParams.update(mpl.rcParamsDefault)
        rc('font',**{'family':'serif','serif':['Cardo'],'size':16})
        rc('text', usetex=True)

        # Init axis
        fig = plt.figure(figsize=(14, 6))
        ax_pos = fig.add_subplot(111, ylabel='APE translation error [m]', xlabel="Dataset")
        legend_labels = []
        legend_handles = []
        # Draw legend.
        color_id = 0
        for pipeline_type, pipeline_stats in sorted(stats.values()[0].iteritems()):
            # The dummy plots are used to create the legends.
            dummy_plot_pos = ax_pos.plot([1,1], '-', color=colors[color_id])
            legend_labels.append(pipeline_type)
            legend_handles.append(dummy_plot_pos[0])
            color_id = color_id + 1

        idx_param_value = 0
        final_max_e_pos=0.50
        xtick_labels=[]
        pipelines_failed = dict()
        for dataset_name, pipeline_types in sorted(stats.iteritems()):
            xtick_labels.append(dataset_name.replace('_', '\_'))
            if isinstance(pipeline_types, dict):
                idx_pipeline_type = 0
                for pipeline_type, pipeline_stats in sorted(pipeline_types.iteritems()):
                    if isinstance(pipeline_stats, dict):
                        # Find max value overall, to set max in y-axis
                        max_e_pos = pipeline_stats["absolute_errors"]["max"]
                        # if max_e_pos > final_max_e_pos:
                           # final_max_e_pos = max_e_pos
                        # Draw boxplot
                        draw_boxplot(ax_pos, pipeline_stats["absolute_errors"],
                                     [idx_pipeline_type + pos[idx_param_value]], idx_pipeline_type)
                    else:
                        # If pipeline_stats is not a dict, then it means the pipeline failed...
                        # Just plot a cross...
                        pipelines_failed[idx_pipeline_type] = [pipeline_type, idx_param_value]
                    idx_pipeline_type = idx_pipeline_type + 1
            else:
                raise Exception("\033[91mValue in stats should be a dict: " + errors + "\033[99m")
            idx_param_value = idx_param_value + 1

        # Draw crosses instead of boxplots for pipelines that failed.
        for idx_pipeline, pipeline_type_idx_param_pair in pipelines_failed.iteritems():
            x_middle = idx_pipeline + pos[pipeline_type_idx_param_pair[1]]
            x_1 = [x_middle - 0.5*spacing, x_middle + 0.5*spacing]
            y_1 = [0, final_max_e_pos]
            x_2 = [x_middle - 0.5*spacing, x_middle + 0.5*spacing]
            y_2 = [final_max_e_pos, 0]
            red_cross_plot = ax_pos.plot([1,1], 'xr')
            pipeline_type = pipeline_type_idx_param_pair[0]
            legend_labels.append("{} failure".format(pipeline_type))
            legend_handles.append(red_cross_plot[0])
            ax_pos.plot(x_1, y_1, '-r')
            ax_pos.plot(x_2, y_2, '-r')

        # Create legend.
        ax_pos.legend(legend_handles, legend_labels, bbox_to_anchor=(0., 1.02, 1., .102),
                      loc=3, ncol=3, mode='expand', borderaxespad=0.)

        def _ax_formatting(ax, dummy_plots, final_max_e):
            ax.yaxis.grid(ls='--', color='0.7')
            ax.yaxis.set_major_formatter(FuncFormatter(lambda y, pos: '%.2f'%y))
            # ax.xaxis.grid(which='major', visible=True, ls=' ')
            # ax.xaxis.grid(which='minor', visible=False)
            #ax.xaxis.set_major_formatter(plt.NullFormatter())
            ax.set_xticks(pos + 0.5*n_pipeline_types - 0.5)
            ax.set_xticklabels(xtick_labels, rotation=-40, ha='left')
            ax.set_xlim(xmin=pos[0] - 1, xmax=pos[-1] + n_pipeline_types + 0.2)
            ax.set_ylim(ymin=0, ymax= final_max_e)
            yticks = np.arange(0, final_max_e, find_step_of_base(final_max_e/5, 5))
            if len(yticks) < 4:
                ax.set_yticks(np.arange(0, final_max_e, find_step_of_base(final_max_e/5, 1)))
            else:
                ax.set_yticks(yticks)
            for p in dummy_plots:
                p.set_visible(False)

        # give some extra space for the plot...
        final_max_e_pos += 0.02
        _ax_formatting(ax_pos, legend_handles, final_max_e_pos)

        fig.savefig(os.path.join(output_dir, 'datasets_ape_boxplots.eps'),
                    bbox_inches="tight", format="eps", dpi=1200)
    else:
        raise Exception("\033[91mStats should be a dict: " + stats + "\033[99m")

    # Restore plotting config.
    from evo.tools.settings import SETTINGS
    plt.style.use('seaborn')
    # configure matplotlib and seaborn according to package settings
    sns.set(style=SETTINGS.plot_seaborn_style,
            palette=SETTINGS.plot_seaborn_palette,
            font=SETTINGS.plot_fontfamily,
            font_scale=SETTINGS.plot_fontscale
           )

    rc_params = {
        "lines.linewidth": SETTINGS.plot_linewidth,
        "text.usetex": SETTINGS.plot_usetex,
        "font.family": SETTINGS.plot_fontfamily,
        "font.serif": ['Cardo'],
        "pgf.texsystem": SETTINGS.plot_texsystem
    }
    mpl.rcParams.update(rc_params)

def aggregate_ape_results(list_of_datasets, list_of_pipelines):
    RESULTS_DIR = '/home/tonirv/code/evo-1/results'
    # Load results.
    print("Loading dataset results")

    # Aggregate all stats for each pipeline and dataset
    stats = dict()
    for dataset_name in list_of_datasets:
        dataset_dir = os.path.join(RESULTS_DIR, dataset_name)
        stats[dataset_name] = dict()
        for pipeline_name in list_of_pipelines:
            pipeline_dir = os.path.join(dataset_dir, pipeline_name)
            # Get results.
            results_file = os.path.join(pipeline_dir, 'results.yaml')
            stats[dataset_name][pipeline_name]  = yaml.load(open(results_file,'r'))
            print("Check stats from " + results_file)
            checkStats(stats[dataset_name][pipeline_name])

    print("Drawing APE boxplots.")
    draw_ape_boxplots(stats, RESULTS_DIR)
    # Write APE table
    write_latex_table(stats, RESULTS_DIR)
    # Write APE table without S pipeline

def get_distance_from_start(gt_translation):
    distances = np.diff(gt_translation[:,0:3],axis=0)
    distances = np.sqrt(np.sum(np.multiply(distances,distances),1))
    distances = np.cumsum(distances)
    distances = np.concatenate(([0], distances))
    return distances

def locate_min(a):
    smallest = min(a)
    return smallest, [index for index, element in enumerate(a)
                      if smallest == element]

def write_latex_table(stats, results_dir):
    """ Write latex table with median, mean and rmse from stats:
            which is a list that contains:
                - dataset name (string) (like V1_01_easy, MH_01_easy etc):
                    - pipeline type (string) (like S, SP or SPR):
                        - "absolute_errors":
                            - "max"
                            - "min"
                            - "mean"
                            - "median"
                            - "q1"
                            - "q3"
                            - "rmse"
            This function iterates over the pipeline types, and for each pipeline type, it plots
            the metrics achieved, as a boxplot. So the boxplot has in x-axis the dataset name,
            and in y-axis one boxplot per pipeline."""
    # Tex stuff.
    # start_line = """\\begin{table}[H]
    # \\centering
    # \\resizebox{\\textwidth}{!}{
    # \\begin{tabular}{l p{1.4cm} p{1.4cm} p{1.4cm} p{1.4cm} p{1.4cm} p{1.4cm} p{1.4cm} p{1.4cm} p{1.4cm}}
    # \\hline
    # Sequence             & \\multicolumn{2}{c}{\\textbf{S}} & \\multicolumn{2}{c}{\\textbf{S + P}}  & \\multicolumn{2}{c}{\\textbf{S + P + R} (Proposed)}          \\\\ \\hline
                         # & Median APE Translation (m)  & Mean APE Translation (m) & RMSE APE Translation (m) &
                         # Median APE Translation (m)  & Mean APE Translation (m) & RMSE APE Translation (m) & Median
                         # APE Translation (m) & Mean APE Translation (m)  & RMSE APE translation (m) \\\\
    # """
    start_line = """\\begin{table}[H]
  \\centering
  \\caption{Accuracy of the state estimation when using Structureless and Projection factors (S + P), and our proposed approach using Structureless, Projection and Regularity factors (S + P + R)}
  \\label{tab:accuracy_comparison}
  \\begin{tabularx}{\\textwidth}{l *6{Y}}
    \\toprule
    & \\multicolumn{6}{c}{APE Translation} \\\\
    \\cmidrule{2-7}
    & \\multicolumn{3}{c}{\\textbf{S + P}}  & \\multicolumn{3}{c}{\\textbf{S + P + R} (Proposed)} \\\\
    \\cmidrule(r){2-4} \\cmidrule(l){5-7}
    Sequence & Median [cm] & Mean [cm] & RMSE [cm] & Median [cm] & Mean [cm] & RMSE [cm] \\\\
    \\midrule
    """

    end_line = """
    \\bottomrule
  \\end{tabularx}%
\\end{table}
"""
    bold_in = '& \\textbf{{'
    bold_out = '}} '
    end = '\\\\\n'

    all_lines = start_line

    winners = dict()
    for dataset_name, pipeline_types in sorted(stats.iteritems()):
        median_error_pos = []
        # mean_error_pos = []
        rmse_error_pos = []
        for pipeline_type, pipeline_stats in sorted(pipeline_types.iteritems()):
            # if pipeline_type is not "S": # Ignore S pipeline
            median_error_pos.append(pipeline_stats["absolute_errors"]["median"])
            # mean_error_pos.append(pipeline_stats["absolute_errors"]["mean"])
            rmse_error_pos.append(pipeline_stats["absolute_errors"]["rmse"])

        # Find winning pipeline
        _, median_idx_min = locate_min(median_error_pos)
        # _, mean_idx_min = locate_min(mean_error_pos)
        _, rmse_idx_min = locate_min(rmse_error_pos)

        # Store winning pipeline
        winners[dataset_name] = [median_idx_min,
                                 # mean_idx_min,
                                 rmse_idx_min]

    for dataset_name, pipeline_types in sorted(stats.iteritems()):
        start = '{:>25} '.format(dataset_name.replace('_', '\\_'))
        one_line = start
        pipeline_idx = 0
        for pipeline_type, pipeline_stats in sorted(pipeline_types.iteritems()):
            # if pipeline_type is not "S": # Ignore S pipeline
            median_error_pos = pipeline_stats["absolute_errors"]["median"] * 100 # as we report in cm
            # mean_error_pos = pipeline_stats["absolute_errors"]["mean"] * 100 # as we report in cm
            rmse_error_pos = pipeline_stats["absolute_errors"]["rmse"] * 100 # as we report in cm

            # Bold for min median error
            if len(winners[dataset_name][0]) == 1 and pipeline_idx == winners[dataset_name][0][0]:
                one_line += bold_in + '{:.1f}'.format(median_error_pos) + bold_out
            else:
                one_line += '& {:.1f} '.format(median_error_pos)

            # Bold for min mean error
            # if len(winners[dataset_name][1]) == 1 and winners[dataset_name][1][0] == pipeline_idx:
                # one_line += bold_in + '{:.1f}'.format(mean_error_pos) + bold_out
            # else:
                # one_line += '& {:.1f} '.format(mean_error_pos)

            # Bold for min rmse error
            # Do not bold, if multiple max
            if len(winners[dataset_name][1]) == 1 and winners[dataset_name][1][0] == pipeline_idx:
                one_line += bold_in + '{:.1f}'.format(rmse_error_pos) + bold_out
            else:
                one_line += '& {:.1f} '.format(rmse_error_pos)

            pipeline_idx += 1

        one_line += end
        all_lines += one_line
    all_lines += end_line

    # Save table
    results_file = os.path.join(results_dir, 'APE_table.tex')
    print("Saving table of APE results to: " + results_file)
    with open(results_file,'w') as outfile:
        outfile.write(all_lines)

def run_analysis(traj_ref_path, traj_est_path, segments, save_results, display_plot, save_plots,
                 save_folder, confirm_overwrite = False, idx_analysis = -1, discard_n_start_poses=0,
                discard_n_end_poses=0):
    """ Run analysis on given trajectories, saves plots on given path:
    :param traj_ref_path: path to the reference (ground truth) trajectory.
    :param traj_est_path: path to the estimated trajectory.
    :param save_results: saves APE, and RPE per segment results.
    :param save_plots: whether to save the plots.
    :param save_folder: where to save the plots.
    :param confirm_overwrite: whether to confirm overwriting plots or not.
    :param idx_analysis: optional param, to allow setting the same scale on different plots.
    """
    # Load trajectories.
    from evo.tools import file_interface
    traj_ref = file_interface.read_euroc_csv_trajectory(traj_ref_path)
    traj_est = file_interface.read_swe_csv_trajectory(traj_est_path)

    print("Registering trajectories")
    traj_ref, traj_est = sync.associate_trajectories(traj_ref, traj_est)

    print("Aligning trajectories")
    traj_est = trajectory.align_trajectory(traj_est, traj_ref, correct_scale = False,
                                           discard_n_start_poses = int(discard_n_start_poses),
                                           discard_n_end_poses = int(discard_n_end_poses))

    num_of_poses = traj_est.num_poses
    traj_est.reduce_to_ids(range(int(discard_n_start_poses), int(num_of_poses - discard_n_end_poses), 1))
    traj_ref.reduce_to_ids(range(int(discard_n_start_poses), int(num_of_poses - discard_n_end_poses), 1))

    results = dict()

    results["absolute_errors"] = dict()
    print("Calculating APE translation part")
    data = (traj_ref, traj_est)
    ape_metric = metrics.APE(metrics.PoseRelation.translation_part)
    ape_metric.process_data(data)
    ape_statistics = ape_metric.get_all_statistics()
    results["absolute_errors"] = ape_statistics
    print("mean:", ape_statistics["mean"])

    print("Calculating RPE translation part for plotting")
    rpe_metric_trans = metrics.RPE(metrics.PoseRelation.translation_part,
                                   1.0, metrics.Unit.frames, 0.0, False)
    rpe_metric_trans.process_data(data)
    rpe_stats_trans = rpe_metric_trans.get_all_statistics()
    print("mean:", rpe_stats_trans["mean"])

    print("Calculating RPE rotation angle for plotting")
    rpe_metric_rot = metrics.RPE(metrics.PoseRelation.rotation_angle_deg,
                                 1.0, metrics.Unit.frames, 1.0, False)
    rpe_metric_rot.process_data(data)
    rpe_stats_rot = rpe_metric_rot.get_all_statistics()
    print("mean:", rpe_stats_rot["mean"])

    results["relative_errors"] = dict()
    # Read segments file
    for segment in segments:
        results["relative_errors"][segment] = dict()
        print("RPE analysis of segment: " + segment)
        print("Calculating RPE segment translation part")
        rpe_segment_metric_trans = metrics.RPE(metrics.PoseRelation.translation_part,
                                       float(segment), metrics.Unit.meters, 0.01, True)
        rpe_segment_metric_trans.process_data(data)
        rpe_segment_stats_trans = rpe_segment_metric_trans.get_all_statistics()
        results["relative_errors"][segment]["rpe_trans"] = rpe_segment_stats_trans
        # print(rpe_segment_stats_trans)
        # print("mean:", rpe_segment_stats_trans["mean"])

        print("Calculating RPE segment rotation angle")
        rpe_segment_metric_rot = metrics.RPE(metrics.PoseRelation.rotation_angle_deg,
                                     float(segment), metrics.Unit.meters, 0.01, True)
        rpe_segment_metric_rot.process_data(data)
        rpe_segment_stats_rot = rpe_segment_metric_rot.get_all_statistics()
        results["relative_errors"][segment]["rpe_rot"] = rpe_segment_stats_rot
        # print(rpe_segment_stats_rot)
        # print("mean:", rpe_segment_stats_rot["mean"])

    if save_results:
        # Save results file
        results_file = os.path.join(save_folder, 'results.yaml')
        print("Saving analysis results to: " + results_file)
        if confirm_overwrite:
            if not user.check_and_confirm_overwrite(results_file):
                return
        with open(results_file,'w') as outfile:
            outfile.write(yaml.dump(results, default_flow_style=False))

    # For each segment in segments file
    # Calculate rpe with delta = segment in meters with all-pairs set to True
    # Calculate max, min, rmse, mean, median etc
    # Plot boxplot, or those cumulative figures you see in evo (like demographic plots)

    if display_plot or save_plots:
        print("loading plot modules")
        from evo.tools import plot

        print("plotting")
        plot_collection = plot.PlotCollection("Example")
        # metric values
        fig_1 = plt.figure(figsize=(8, 8))
        ymax = -1
        if idx_analysis is not -1:
            ymax = Y_MAX_APE_TRANS[idx_analysis]
        plot.error_array(fig_1, ape_metric.error, statistics=ape_statistics,
                         name="APE translation", title=""#str(ape_metric)
                         , xlabel="Keyframe index [-]",
                         ylabel="APE translation [m]", y_min= 0.0, y_max=ymax)
        plot_collection.add_figure("APE_translation", fig_1)

        # trajectory colormapped with error
        fig_2 = plt.figure(figsize=(8, 8))
        plot_mode = plot.PlotMode.xy
        ax = plot.prepare_axis(fig_2, plot_mode)
        plot.traj(ax, plot_mode, traj_ref, '--', 'gray', 'reference')
        plot.traj_colormap(ax, traj_est, ape_metric.error, plot_mode,
                           min_map=0.0, max_map=ymax,
                           title="APE translation error mapped onto trajectory [m]")
        plot_collection.add_figure("APE_translation_trajectory_error", fig_2)

        # RPE
        ## Trans
        ### metric values
        fig_3 = plt.figure(figsize=(8, 8))
        if idx_analysis is not -1:
            ymax = Y_MAX_RPE_TRANS[idx_analysis]
        plot.error_array(fig_3, rpe_metric_trans.error, statistics=rpe_stats_trans,
                         name="RPE translation", title=""#str(rpe_metric_trans)
                         , xlabel="Keyframe index [-]", ylabel="RPE translation [m]", y_max=ymax)
        plot_collection.add_figure("RPE_translation", fig_3)

        ### trajectory colormapped with error
        fig_4 = plt.figure(figsize=(8, 8))
        plot_mode = plot.PlotMode.xy
        ax = plot.prepare_axis(fig_4, plot_mode)
        traj_ref_trans = copy.deepcopy(traj_ref)
        traj_ref_trans.reduce_to_ids(rpe_metric_trans.delta_ids)
        traj_est_trans = copy.deepcopy(traj_est)
        traj_est_trans.reduce_to_ids(rpe_metric_trans.delta_ids)
        plot.traj(ax, plot_mode, traj_ref_trans, '--', 'gray', 'Reference')
        plot.traj_colormap(ax, traj_est_trans, rpe_metric_trans.error, plot_mode,
                           min_map=0.0, max_map=ymax,
                           title="RPE translation error mapped onto trajectory [m]"
                          )
        plot_collection.add_figure("RPE_translation_trajectory_error", fig_4)

        ## Rot
        ### metric values
        fig_5 = plt.figure(figsize=(8, 8))
        if idx_analysis is not -1:
            ymax = Y_MAX_RPE_ROT[idx_analysis]
        plot.error_array(fig_5, rpe_metric_rot.error, statistics=rpe_stats_rot,
                         name="RPE rotation error", title=""#str(rpe_metric_rot)
                         , xlabel="Keyframe index [-]", ylabel="RPE rotation [deg]", y_max=ymax)
        plot_collection.add_figure("RPE_rotation", fig_5)

        ### trajectory colormapped with error
        fig_6 = plt.figure(figsize=(8, 8))
        plot_mode = plot.PlotMode.xy
        ax = plot.prepare_axis(fig_6, plot_mode)
        traj_ref_rot = copy.deepcopy(traj_ref)
        traj_ref_rot.reduce_to_ids(rpe_metric_rot.delta_ids)
        traj_est_rot = copy.deepcopy(traj_est)
        traj_est_rot.reduce_to_ids(rpe_metric_rot.delta_ids)
        plot.traj(ax, plot_mode, traj_ref_rot, '--', 'gray', 'Reference')
        plot.traj_colormap(ax, traj_est_rot, rpe_metric_rot.error, plot_mode,
                           min_map=0.0, max_map=ymax,
                           title="RPE rotation error mapped onto trajectory [deg]")
        plot_collection.add_figure("RPE_rotation_trajectory_error", fig_6)

        if display_plot:
            print("Displaying plots.")
            plot_collection.show()

        if save_plots:
            print("Saving plots to: " + save_folder)
            plot_collection.export(save_folder + "/plots", False)

    ## Plot results
    #if args.plot or args.save_plot or args.serialize_plot:
        #    common.plot(
        #        args, result,
        #        result.trajectories[ref_name],
        #        result.trajectories[est_name])

    ## Save results
    #if args.save_results:
        #    logger.debug(SEP)
        #    if not SETTINGS.save_traj_in_zip:
            #        del result.trajectories[ref_name]
            #        del result.trajectories[est_name]
            #    file_interface.save_res_file(
            #        args.save_results, result, confirm_overwrite=not args.no_warnings)

# Run pipeline as a subprocess.
def run_vio(build_dir, dataset_dir, dataset_name, results_dir, pipeline_output_dir, pipeline_type,
           extra_flagfile_path = ""):
    """ Runs pipeline depending on the pipeline_type"""
    import subprocess
    return subprocess.call("{}/stereoVIOEuroc \
                           --logtostderr=1 --colorlogtostderr=1 --log_prefix=0 \
                           --dataset_path={}/{} --output_path={}\
                           --vio_params_path={}/params/{}/{} \
                           --tracker_params_path={}/params/{}/{} \
                           --flagfile={}/params/{}/{} --flagfile={}/params/{}/{} \
                           --flagfile={}/params/{}/{} --flagfile={}/params/{}/{} \
                           --flagfile={}/params/{}/{} --flagfile={}/params/{}/{} \
                           --log_output=True".format(
                               build_dir, dataset_dir, dataset_name, pipeline_output_dir,
                               results_dir, pipeline_type, "vioParameters.yaml",
                               results_dir, pipeline_type, "trackerParameters.yaml",
                               results_dir, pipeline_type, "flags/stereoVIOEuroc.flags",
                               results_dir, pipeline_type, "flags/Mesher.flags",
                               results_dir, pipeline_type, "flags/VioBackEnd.flags",
                               results_dir, pipeline_type, "flags/RegularVioBackEnd.flags",
                               results_dir, pipeline_type, "flags/Visualizer3D.flags",
                               results_dir, pipeline_type, extra_flagfile_path), \
                           shell=True)

def moveOutputFromTo(pipeline_output_dir, output_destination_dir):
    try:
        if (os.path.exists(output_destination_dir)):
            rmtree(output_destination_dir)
    except:
        print("Directory:" + output_destination_dir + " does not exist, we can safely move output.")
    try:
        if (os.path.isdir(pipeline_output_dir)):
            move(pipeline_output_dir, output_destination_dir)
        else:
            print("There is no output directory...")
    except:
        print("Could not move output from: " + pipeline_output_dir + " to: "
              + output_destination_dir)
        raise
    try:
        os.makedirs(pipeline_output_dir)
    except:
        print("Could not mkdir: " + pipeline_output_dir)
        raise

def process_vio(build_dir, dataset_dir, dataset_name, results_dir, pipeline_output_dir,
                pipeline_type, SEGMENTS, save_results, plot, save_plots, output_file, run_pipeline, analyse_vio, discard_n_start_poses, discard_n_end_poses):
    """ build_dir: directory where the pipeline executable resides,
    dataset_dir: directory of the dataset,
    dataset_name: specific dataset to run,
    results_dir: directory where the results of the run will reside:
        used as results_dir/dataset_name/S, results_dir/dataset_name/SP, results_dir/dataset_name/SPR
        where each directory have traj_est.csv (the estimated trajectory), and plots if requested.
        results_dir/dataset_name/ must contain traj_gt.csv (the ground truth trajectory for analysis to work),
    pipeline_output_dir: where to store all output_* files produced by the pipeline,
    pipeline_type: type of pipeline to process (1: S, 2: SP, 3: SPR)
    SEGMENTS: segments for RPE boxplots,
    save_results: saves APE, and RPE per segment results of the run,
    plot: whether to plot the APE/RPE results or not,
    save_plots: saves plots of APE/RPE,
    output_file: the name of the trajectory estimate output of the vio which will then be copied as traj_est.csv,
    run_pipeline: whether to run the VIO to generate a new traj_est.csv,
    analyse_vio: whether to analyse traj_est.csv or not"""
    dataset_result_dir = results_dir + "/" + dataset_name + "/"
    dataset_pipeline_result_dir = dataset_result_dir + "/" + pipeline_type + "/"
    traj_ref_path = dataset_result_dir + "/traj_gt.csv"
    traj_est_s = dataset_result_dir + "/" + pipeline_type + "/" + "traj_es.csv"
    if run_pipeline:
        if run_vio(build_dir, dataset_dir, dataset_name, results_dir,
                   pipeline_output_dir, pipeline_type) == 0:
            print("Successful pipeline run.")
            print("\033[1mCopying output file: " + output_file + "\n to results file:\n" + \
                  traj_est_s + "\033[0m")
            copyfile(output_file, traj_est_s)
            try:
                output_destination_dir = dataset_pipeline_result_dir + "/output/"
                print("\033[1mCopying output dir: " + pipeline_output_dir
                      + "\n to destination:\n" + output_destination_dir + "\033[0m")
                moveOutputFromTo(pipeline_output_dir, output_destination_dir)
            except:
                print("\033[1mFailed copying output dir: " + pipeline_output_dir
                      + "\n to destination:\n" + output_destination_dir + "\033[0m")
        else:
            print("Pipeline failed on dataset: " + dataset_name)
            return False

    if analyse_vio:
        print("\033[1mAnalysing dataset: " + dataset_result_dir + " for pipeline "
              + pipeline_type + ".\033[0m")
        run_analysis(traj_ref_path, traj_est_s, SEGMENTS,
                     save_results, plot, save_plots, dataset_pipeline_result_dir, False,
                     return_id_of_dataset(dataset_name),
                     discard_n_start_poses,
                     discard_n_end_poses)
    return True

def return_id_of_dataset(dataset_name):
    if dataset_name == "MH_01_easy":
        return 0
    if dataset_name == "MH_02_easy":
        return 1
    if dataset_name == "MH_03_medium":
        return 2
    if dataset_name == "mh_04_difficult":
        return 3
    if dataset_name == "MH_05_difficult":
        return 4
    if dataset_name == "V1_01_easy":
        return 5
    if dataset_name == "V1_02_medium":
        return 6
    if dataset_name == "V1_03_difficult":
        return 7
    if dataset_name == "V2_01_easy":
        return 8
    if dataset_name == "V2_02_medium":
        return 9
    if dataset_name == "v2_03_difficult":
        return 10

def run_dataset(results_dir, dataset_dir, dataset_name, build_dir,
                run_pipeline, analyse_vio,
                plot, save_results, save_plots, save_boxplots, switch,
                discard_n_start_poses = 0, discard_n_end_poses = 0):
    """ Evaluates pipeline using Structureless(S), Structureless(S) + Projection(P), \
            and Structureless(S) + Projection(P) + Regular(R) factors \
            and then compiles a list of results """
    import time

    with open(os.path.join(results_dir, dataset_name, 'segments.txt'), 'r') as myfile:
        SEGMENTS = myfile.read().replace('\n', '').split(',')

    ################### RUN PIPELINE ################################
    pipeline_output_dir = results_dir + "/tmp_output/output"
    output_file = pipeline_output_dir + "/output_posesVIO.csv"
    has_a_pipeline_failed = False
    if switch == 1 or switch == 0 or switch == 4 or switch == 5:
        if process_vio(build_dir, dataset_dir, dataset_name, results_dir, pipeline_output_dir,
                   "S", SEGMENTS, save_results, plot, save_plots,
                       output_file, run_pipeline, analyse_vio,
                       discard_n_start_poses, discard_n_end_poses) == False:
            has_a_pipeline_failed = True

    if switch == 2 or switch == 0 or switch == 4 or switch == 6:
        time.sleep(2)
        if process_vio(build_dir, dataset_dir, dataset_name, results_dir, pipeline_output_dir,
                    "SP", SEGMENTS, save_results, plot, save_plots,
                       output_file, run_pipeline, analyse_vio,
                       discard_n_start_poses, discard_n_end_poses) == False:
            has_a_pipeline_failed = True

    if switch == 3 or switch == 0 or switch == 5 or switch == 6:
        time.sleep(2)
        if process_vio(build_dir, dataset_dir, dataset_name, results_dir, pipeline_output_dir,
                    "SPR", SEGMENTS, save_results, plot, save_plots,
                       output_file, run_pipeline, analyse_vio,
                       discard_n_start_poses, discard_n_end_poses) == False:
            has_a_pipeline_failed = True

    if switch == -1:
        print("Not running pipeline...")

    if switch != 0 and switch != 1 and switch != 2 and switch != 3 and switch != -1 and switch != 4 and switch != 5 and switch != 6 :
        raise Exception("\033[91mUnrecognized pipeline to run: {} \033[99m".format(switch) )

    # Save boxplots
    if save_boxplots:
        if has_a_pipeline_failed == False:
            print("Saving boxplots.")
            results_s = results_dir + "/" + dataset_name + "/S/results.yaml"
            if not os.path.exists(results_s):
                raise Exception("\033[91mCannot plot boxplots: missing results for S pipeline \
                                and dataset: " + dataset_name + "\033[99m")
            results_sp = results_dir + "/" + dataset_name + "/SP/results.yaml"
            if not os.path.exists(results_sp):
                raise Exception("\033[91mCannot plot boxplots: missing results for SP pipeline \
                                and dataset: " + dataset_name + "\033[99m")
            results_spr = results_dir + "/" + dataset_name + "/SPR/results.yaml"
            if not os.path.exists(results_spr):
                raise Exception("\033[91mCannot plot boxplots: missing results for SPR pipeline \
                                and dataset: " + dataset_name + "\033[99m")
            stats = dict()
            stats['S']  = yaml.load(open(results_s,'r'))
            print("Check stats S " + results_s)
            checkStats(stats['S'])
            print("Check stats SP " + results_sp)
            stats['SP'] = yaml.load(open(results_sp,'r'))
            checkStats(stats['SP'])
            print("Check stats SPR " + results_spr)
            stats['SPR'] = yaml.load(open(results_spr,'r'))
            checkStats(stats['SPR'])
            print("Drawing boxplots.")
            draw_rpe_boxplots(results_dir + "/" + dataset_name,
                          stats, len(SEGMENTS))
        else:
            print("A pipeline run has failed... skipping boxplot drawing.")
    if not has_a_pipeline_failed:
        print ("All pipeline runs were successful.")
    else:
        print("A pipeline has failed!")
    print("Finished evaluation for dataset: " + dataset_name)
    return has_a_pipeline_failed

def checkStats(stats):
    if not "relative_errors" in stats:
        print("Stats: ")
        print(stats)
        raise Exception("\033[91mWrong stats format: no relative_errors... \n"
                        "Are you sure you runned the pipeline and "
                        "saved the results? (--save_results).\033[99m")
    else:
        if len(stats["relative_errors"]) == 0:
            raise Exception("\033[91mNo relative errors available... \n"
                            "Are you sure you runned the pipeline and "
                            "saved the results? (--save_results).\033[99m")

        if not "rpe_rot" in stats["relative_errors"].values()[0]:
            print("Stats: ")
            print(stats)
            raise Exception("\033[91mWrong stats format: no rpe_rot... \n"
                            "Are you sure you runned the pipeline and "
                            "saved the results? (--save_results).\033[99m")
        if not "rpe_trans" in stats["relative_errors"].values()[0]:
            print("Stats: ")
            print(stats)
            raise Exception("\033[91mWrong stats format: no rpe_trans... \n"
                            "Are you sure you runned the pipeline and "
                            "saved the results? (--save_results).\033[99m")
    if not "absolute_errors" in stats:
        print("Stats: ")
        print(stats)
        raise Exception("\033[91mWrong stats format: no absolute_errors... \n"
                        "Are you sure you runned the pipeline and "
                        "saved the results? (--save_results).\033[99m")

def write_flags_parameters(param_name, param_new_value, params_path):
    directory = os.path.dirname(params_path)
    if not os.path.exists(directory):
        raise Exception("\033[91mCould not find directory: " + directory + "\033[99m")
    params_flagfile = open(params_path, "a+")
    params_flagfile.write("--" + param_name + "=" + param_new_value)
    params_flagfile.close()

def ensure_dir(dir_path):
    """ Check if the path directory exists: if it does, returns true,
    if not creates the directory dir_path and returns if it was successful"""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return True

def check_and_create_regression_test_structure(regression_tests_path, param_names, param_values,
                                               dataset_names, pipeline_types, extra_params_to_modify):
    """ Makes/Checks that the file structure is the correct one, and updates the parameters with the given values"""
    # Make or check regression_test directory
    assert(ensure_dir(regression_tests_path))
    # Make or check param_name directory
    # Use as param_name the concatenated elements of param_names
    param_names_dir = ""
    for i in param_names:
        param_names_dir += str(i) + "-"
    param_names_dir = param_names_dir[:-1]
    assert(ensure_dir("{}/{}".format(regression_tests_path, param_names_dir)))
    for param_value in param_values:
        # Create/Check param_value folder
        param_value_dir = ""
        if isinstance(param_value, list):
            for i in param_value:
                param_value_dir += str(i) + "-"
            param_value_dir = param_value_dir[:-1]
        else:
            param_value_dir = param_value
        ensure_dir("{}/{}/{}".format(regression_tests_path, param_names_dir, param_value_dir))
        # Create params folder by copying from current official one.
        param_dir = "{}/{}/{}/params".format(regression_tests_path, param_names_dir, param_value_dir);
        if (os.path.exists(param_dir)):
            rmtree(param_dir)
        copytree("/home/tonirv/code/evo/results/params", param_dir)

        # Modify param with param value
        for pipeline_type in pipeline_types:
            param_pipeline_dir = "{}/{}".format(param_dir, pipeline_type)
            ensure_dir(param_pipeline_dir)
            written_extra_param_names = []
            is_param_name_written = [False] * len(param_names)
            # VIO params
            vio_file = param_pipeline_dir + "/vioParameters.yaml"
            vio_params = []
            with open(vio_file, 'r') as infile:
                # Skip first yaml line: it contains %YAML:... which can't be read...
                _ = infile.readline()
                vio_params = yaml.load(infile)
                for idx, param_name in enumerate(param_names):
                    if param_name in vio_params:
                        # Modify param_name with param_value
                        if isinstance(param_value, list):
                            vio_params[param_name] = param_value[idx]
                        else:
                            vio_params[param_name] = param_value
                        is_param_name_written[idx] = True
                for extra_param_name, extra_param_value in extra_params_to_modify.iteritems():
                    if extra_param_name in vio_params:
                        vio_params[extra_param_name] = extra_param_value
                        written_extra_param_names.append(extra_param_name)
                # Store param_names with param_value
                with open(vio_file,'w') as outfile:
                    outfile.write("%YAML:1.0\n")
                with open(vio_file,'a') as outfile:
                    outfile.write(yaml.dump(vio_params))

            # Tracker params
            tracker_file = param_pipeline_dir + "/trackerParameters.yaml"
            tracker_params = []
            with open(tracker_file, 'r') as infile:
                # Skip first yaml line: it contains %YAML:... which can't be read...
                _ = infile.readline()
                tracker_params = yaml.load(infile)
                for idx, param_name in enumerate(param_names):
                    if param_name in tracker_params:
                        # Modify param_name with param_value
                        if isinstance(param_value, list):
                            tracker_params[param_name] = param_value[idx]
                        else:
                            tracker_params[param_name] = param_value
                        is_param_name_written[idx] = True
                for extra_param_name, extra_param_value in extra_params_to_modify.iteritems():
                    if extra_param_name in tracker_params:
                        tracker_params[extra_param_name] = extra_param_value
                        written_extra_param_names.append(extra_param_name)
                with open(tracker_file,'w') as outfile:
                    outfile.write("%YAML:1.0\n")
                with open(tracker_file,'a') as outfile:
                    outfile.write(yaml.dump(tracker_params, default_flow_style=False))

            # Gflags
            for idx, param_name in enumerate(param_names):
                if not is_param_name_written[idx]:
                    # Could not find param_name in vio_params nor tracker_params
                    # it must be a gflag:
                    if isinstance(param_value, list):
                        write_flags_parameters(param_name, param_value[idx],
                                               param_pipeline_dir + "/flags/override.flags")
                    else:
                        write_flags_parameters(param_name, param_value,
                                               param_pipeline_dir + "/flags/override.flags")
            for extra_param_name, extra_param_value in extra_params_to_modify.iteritems():
                if extra_param_name not in written_extra_param_names:
                    write_flags_parameters(extra_param_name,
                                           extra_param_value,
                                           param_pipeline_dir + "/flags/override.flags")

        # Create/Check tmp_output folder
        ensure_dir("{}/{}/{}/tmp_output/output".format(regression_tests_path, param_names_dir, param_value_dir))

        for dataset_name in dataset_names:
            ensure_dir("{}/{}/{}/{}".format(regression_tests_path, param_names_dir, param_value_dir, dataset_name))
            # Create ground truth trajectory by copying from current official one.
            copy2("/home/tonirv/code/evo/results/{}/traj_gt.csv".format(dataset_name),
                 "{}/{}/{}/{}/traj_gt.csv".format(regression_tests_path, param_names_dir,
                                                  param_value_dir, dataset_name))
            # Create segments by copying from current official one.
            copy2("/home/tonirv/code/evo/results/{}/segments.txt".format(dataset_name),
                 "{}/{}/{}/{}/segments.txt".format(regression_tests_path, param_names_dir,
                                                  param_value_dir, dataset_name))
            for pipeline_type in pipeline_types:
                ensure_dir("{}/{}/{}/{}/{}".format(regression_tests_path, param_names_dir, param_value_dir,
                                                   dataset_name, pipeline_type))

    # Make/Check results dir for current param_names
    ensure_dir("{}/{}/results".format(regression_tests_path, param_names_dir))
    for dataset_name in dataset_names:
        # Make/Check dataset dir for current param_names_dir, as the performance given the param depends on the dataset.
        ensure_dir("{}/{}/results/{}".format(regression_tests_path, param_names_dir, dataset_name))

def regression_test_simple(test_name, param_names, param_values, only_compile_regression_test_results,
                           run_pipelines, pipelines_to_run, extra_params_to_modify):
    """ Runs the vio pipeline with different values for the given param
    and draws graphs to decide best value for the param:
        param_names: names of the parameters to fine-tune: e.g ["monoNoiseSigma", "stereoNoiseSigma"]
        param_values: values that the parameter should take: e.g [[1.0, 1.3], [1.0, 1.2]]
        only_compile_regression_test_results: just draw boxplots for regression test,
            skip all per pipeline analysis and runs, assumes we have results.yaml for
            each param value, dataset and pipeline.
        run_pipelines: run pipelines, if set to false, it won't run pipelines and will assume we have a traj_est.csv already.
        pipelines_to_run: which pipeline to run, useful when a parameter only affects a single pipeline."""
    # Ensure input is correct.
    if isinstance(param_names, list):
        if len(param_names) > 1:
            assert(len(param_names) == len(param_values[0]))
            for i in range(2, len(param_names)):
                # Ensure all rows have the same number of parameter changes
                assert(len(param_values[i-2]) == len(param_values[i-1]))

    # Check and create file structure
    dataset_names = ["V1_01_easy"]
    pipelines_to_run_list = []
    if pipelines_to_run == 0:
        pipelines_to_run_list = ['S', 'SP', 'SPR']
    if pipelines_to_run == 1:
        pipelines_to_run_list = ['S']
    if pipelines_to_run == 2:
        pipelines_to_run_list = ['SP']
    if pipelines_to_run == 3:
        pipelines_to_run_list = ['SPR']
    if pipelines_to_run == 4:
        pipelines_to_run_list = ['S', 'SP']
    if pipelines_to_run == 5:
        pipelines_to_run_list = ['S', 'SPR']
    if pipelines_to_run == 6:
        pipelines_to_run_list = ['SP', 'SPR']
    REGRESSION_TESTS_DIR = "/home/tonirv/code/evo/regression_tests/" + test_name
    check_and_create_regression_test_structure(REGRESSION_TESTS_DIR, param_names, param_values,
                                               dataset_names, pipelines_to_run_list, extra_params_to_modify)


    param_names_dir = ""
    for i in param_names:
        param_names_dir += str(i) + "-"
    param_names_dir = param_names_dir[:-1]
    DATASET_DIR = '/home/tonirv/datasets/EuRoC'
    BUILD_DIR = '/home/tonirv/code/spark_vio/build'
    has_a_pipeline_failed = False
    if not only_compile_regression_test_results:
        for param_value in param_values:
            param_value_dir = ""
            if isinstance(param_value, list):
                for i in param_value:
                    param_value_dir += str(i) + "-"
                param_value_dir = param_value_dir[:-1]
            else:
                param_value_dir = param_value
            results_dir = "{}/{}/{}".format(REGRESSION_TESTS_DIR, param_names_dir, param_value_dir)
            pipeline_output_dir = results_dir + "/tmp_output/output"
            output_file = pipeline_output_dir + "/output_posesVIO.csv"
            for dataset_name in dataset_names:
                if run_dataset(results_dir, DATASET_DIR, dataset_name, BUILD_DIR,
                               run_pipelines, # Should we re-run pipelines?
                               True, # Should we run the analysis of per pipeline errors?
                               False, # Should we display plots?
                               True, # Should we save results?
                               True, # Should we save plots?
                               False, # Should we save boxplots?
                               pipelines_to_run): # Should we run 0: all pipelines, 1: S, 2:SP 3:SPR
                    has_a_pipeline_failed = True

                print("Finished analysis of pipelines for param_value: {} for parameter: {}".format(param_value_dir, param_names_dir))
                print("Finished pipeline runs/analysis for regression test of param_name: {}".format(param_names_dir))

    # Compile results for current param_name
    print("Drawing boxplot APE for regression test of param_name: {}".format(param_names_dir))
    for dataset_name in dataset_names:
        stats = dict()
        for param_value in param_values:
            param_value_dir = ""
            if isinstance(param_value, list):
                for i in param_value:
                    param_value_dir += str(i) + "-"
                param_value_dir = param_value_dir[:-1]
            else:
                param_value_dir = param_value
            stats[param_value_dir] = dict()
            for pipeline in pipelines_to_run_list:
                results_file = "{}/{}/{}/{}/{}/results.yaml".format(REGRESSION_TESTS_DIR, param_names_dir,
                                                                    param_value_dir, dataset_name, pipeline)
                if os.path.isfile(results_file):
                    stats[param_value_dir][pipeline] = yaml.load(open(results_file,'r'))
                else:
                    print("Could not find results file: {}".format(results_file) + ". Adding cross to boxplot...")
                    stats[param_value_dir][pipeline] = False

        print("Drawing regression simple APE boxplots for dataset: " + dataset_name)
        plot_dir = "{}/{}/results/{}".format(REGRESSION_TESTS_DIR, param_names_dir, dataset_name)
        max_y = -1
        if dataset_name == "V2_02_medium":
            max_y = 0.40
        if dataset_name == "V1_01_easy":
            max_y = 0.20
        draw_regression_simple_boxplot_APE(param_names, stats, plot_dir, max_y)
    print("Finished regression test for param_name: {}".format(param_names_dir))

def draw_regression_simple_boxplot_APE(param_names, stats, output_dir, max_y = -1):
    """ Draw boxpots where x-axis are the values of the parameters in param_names, and the y-axis has boxplots with APE
    performance of the pipelines in stats.
    Stats is organized as follows:
        - param_value_dir (path to directory containing results for the parameter with given value)
            - pipeline (pipeline type e.g. S, SP or SPR)
                - results (which is actually -max, -min etc !OR! False if there are no results if the pipeline failed."""
    colors = ['blue', 'black', 'green', 'red', 'mangenta', 'cyan', 'orange']
    if isinstance(stats, dict):
        n_param_values = len(stats)
        assert(n_param_values > 0)
        n_pipeline_types = len(stats.values()[0])
        spacing = 1

        # Precompute position of boxplots in plot.
        pos = np.arange(0, n_param_values * (n_pipeline_types + spacing),
                        (n_pipeline_types + spacing))

        # Use different plotting config.
        plt.style.use('default')
        import matplotlib as mpl
        from matplotlib import rc
        import seaborn as sns
        sns.reset_orig()
        mpl.rcParams.update(mpl.rcParamsDefault)
        rc('font',**{'family':'serif','serif':['Cardo'],'size':16})
        rc('text', usetex=True)

        # Init axis
        fig = plt.figure(figsize=(6,2))
        param_names_dir = ""
        for i in param_names:
            param_names_dir += str(i) + "-"
            param_names_dir = param_names_dir[:-1]
        ax_pos = fig.add_subplot(111, ylabel='APE translation error [m]', xlabel="Values of parameter: {}".format(param_names_dir))
        legend_labels = []
        legend_handles = []
        # Draw legend.
        color_id = 0
        for pipeline_type, pipeline_stats in sorted(stats.values()[0].iteritems()):
            # The dummy plots are used to create the legends.
            dummy_plot_pos = ax_pos.plot([1,1], '-', color=colors[color_id])
            legend_labels.append(pipeline_type)
            legend_handles.append(dummy_plot_pos[0])
            color_id = color_id + 1

        idx_param_value = 0
        auto_scale = False
        final_max_e_pos = 0
        if max_y < 0:
            auto_scale = True
        else:
            final_max_e_pos = max_y
        param_values_boxplots=[]
        pipelines_failed = dict()
        for param_value_boxplots, pipeline_types in sorted(stats.iteritems()):
            param_values_boxplots.append(param_value_boxplots)
            if isinstance(pipeline_types, dict):
                idx_pipeline_type = 0
                for pipeline_type, pipeline_stats in sorted(pipeline_types.iteritems()):
                    if isinstance(pipeline_stats, dict):
                        # Find max value overall, to set max in y-axis
                        max_e_pos = pipeline_stats["absolute_errors"]["max"]
                        if auto_scale:
                            if max_e_pos > final_max_e_pos:
                               final_max_e_pos = max_e_pos
                        # Draw boxplot
                        draw_boxplot(ax_pos, pipeline_stats["absolute_errors"],
                                     [idx_pipeline_type + pos[idx_param_value]], idx_pipeline_type)
                    else:
                        # If pipeline_stats is not a dict, then it means the pipeline failed...
                        # Just plot a cross...
                        pipelines_failed[idx_pipeline_type] = [pipeline_type, idx_param_value]
                    idx_pipeline_type = idx_pipeline_type + 1
            else:
                raise Exception("\033[91mValue in stats should be a dict: " + errors + "\033[99m")
            idx_param_value = idx_param_value + 1

        # Draw crosses instead of boxplots for pipelines that failed.
        for idx_pipeline, pipeline_type_idx_param_pair in pipelines_failed.iteritems():
            x_middle = idx_pipeline + pos[pipeline_type_idx_param_pair[1]]
            x_1 = [x_middle - 0.5*spacing, x_middle + 0.5*spacing]
            y_1 = [0, final_max_e_pos]
            x_2 = [x_middle - 0.5*spacing, x_middle + 0.5*spacing]
            y_2 = [final_max_e_pos, 0]
            red_cross_plot = ax_pos.plot([1,1], 'xr')
            pipeline_type = pipeline_type_idx_param_pair[0]
            legend_labels.append("{} failure".format(pipeline_type))
            legend_handles.append(red_cross_plot[0])
            ax_pos.plot(x_1, y_1, '-r')
            ax_pos.plot(x_2, y_2, '-r')

        # Create legend.
        ax_pos.legend(legend_handles, legend_labels, bbox_to_anchor=(0., 1.02, 1., .102),
                      loc=3, ncol=3, mode='expand', borderaxespad=0.)

        def _ax_formatting(ax, dummy_plots, final_max_e):
            ax.yaxis.grid(ls='--', color='0.7')
            ax.yaxis.set_major_formatter(FuncFormatter(lambda y, pos: '%.2f'%y))
            # ax.xaxis.grid(which='major', visible=True, ls=' ')
            # ax.xaxis.grid(which='minor', visible=False)
            #ax.xaxis.set_major_formatter(plt.NullFormatter())
            ax.set_xticks(pos + 0.5*n_pipeline_types - 0.5)
            ax.set_xticklabels(param_values_boxplots)
            ax.set_xlim(xmin=pos[0] - 1, xmax=pos[-1] + n_pipeline_types + 0.2)
            ax.set_ylim(ymin=0, ymax= final_max_e)
            yticks = np.arange(0, final_max_e, find_step_of_base(final_max_e/5, 5))
            if len(yticks) < 4:
                ax.set_yticks(np.arange(0, final_max_e, find_step_of_base(final_max_e/5, 1)))
            else:
                ax.set_yticks(yticks)
            for p in dummy_plots:
                p.set_visible(False)

        # give some extra space for the plot...
        final_max_e_pos += 0.02
        _ax_formatting(ax_pos, legend_handles, final_max_e_pos)

        fig.savefig(os.path.join(output_dir, param_names_dir + '_absolute_errors_boxplots.eps'),
                    bbox_inches="tight", format="eps", dpi=1200)
    else:
        raise Exception("\033[91mStats should be a dict: " + stats + "\033[99m")

    # Restore plotting config.
    from evo.tools.settings import SETTINGS
    plt.style.use('seaborn')
    # configure matplotlib and seaborn according to package settings
    sns.set(style=SETTINGS.plot_seaborn_style,
            palette=SETTINGS.plot_seaborn_palette,
            font=SETTINGS.plot_fontfamily,
            font_scale=SETTINGS.plot_fontscale
           )

    rc_params = {
        "lines.linewidth": SETTINGS.plot_linewidth,
        "text.usetex": SETTINGS.plot_usetex,
        "font.family": SETTINGS.plot_fontfamily,
        "font.serif": ['Cardo'],
        "pgf.texsystem": SETTINGS.plot_texsystem
    }
    mpl.rcParams.update(rc_params)

def run(args):
    import evo.common_ape_rpe as common
    from evo.tools import log
    from evo.tools.settings import SETTINGS

    log.configure_logging(args.verbose, args.silent, args.debug)
    if args.debug:
        from pprint import pformat
        parser_str = pformat({arg: getattr(args, arg) for arg in vars(args)})
        logger.debug("main_parser config:\n{}".format(parser_str))
        logger.debug(SEP)

    RESULTS_DIR = '/home/tonirv/code/evo-1/results'
    DATASET_DIR = '/home/tonirv/datasets/EuRoC'
    BUILD_DIR = '/home/tonirv/code/spark_vio/build'
    #PLOT_ONLY = 0 only do plotting of results, 1 run also pipeline.
    #PIPELINE_TYPE = 0:All 1:S 2:SP 3:SPR

    # Comment out any experiment that you do not want to run
    list_of_experiments_to_run = [\
                                  # 'MH_01_easy',
                                  # 'MH_02_easy',
                                  # 'MH_03_medium',
                                  # 'mh_04_difficult', # Diff number of left/right imgs...
                                  # 'MH_05_difficult',
                                  'V1_01_easy',
                                  # 'V1_02_medium',
                                  # 'V1_03_difficult',
                                  # 'V2_01_easy',
                                  # 'V2_02_medium',
                                  # 'v2_03_difficult' # Diff number of left/right imgs...
                                 ]

    # Load trajectories.
    print("Loading trajectories")
    for dataset_name in list_of_experiments_to_run:
        run_dataset(RESULTS_DIR, DATASET_DIR, dataset_name, BUILD_DIR,
                    args.run_pipeline, args.analyse_vio,
                    args.plot, args.save_results,
                    args.save_plots, args.save_boxplots, args.pipeline_type,
                    args.discard_n_start_poses, args.discard_n_end_poses)

def parser():
    import argparse
    basic_desc = "Full evaluation of pipeline (APE trans + RPE trans + RPE rot) metric app"

    shared_parser = argparse.ArgumentParser(add_help=True, description="{}".format(basic_desc))
    algo_opts = shared_parser.add_argument_group("algorithm options")
    output_opts = shared_parser.add_argument_group("output options")
    usability_opts = shared_parser.add_argument_group("usability options")

    algo_opts.add_argument("-p", "--pipeline_type", type=float,
                           help="Pipeline_type = 0:All 1:S 2:SP 3:SPR -1:None", default = 0)
    algo_opts.add_argument("-s", "--discard_n_start_poses", type=float,
                           help="Discard n start poses from ground-truth trajectory.", default = 0)
    algo_opts.add_argument("-e", "--discard_n_end_poses", type=float,
                           help="Discard n end poses from ground-truth trajectory", default = 0)
    algo_opts.add_argument("-r", "--run_pipeline", action="store_true",
                           help="Run vio?")
    algo_opts.add_argument("-a", "--analyse_vio", action="store_true",
                           help="Analyse vio, compute APE and RPE")

    output_opts.add_argument("--plot", action="store_true", help="show plot window",)
    output_opts.add_argument("--plot_mode", default="xyz", help="the axes for plot projection",
                             choices=["xy", "yx", "xz", "zx", "yz", "xyz"])
    output_opts.add_argument("--plot_colormap_max", type=float,
                             help="The upper bound used for the color map plot "
                             "(default: maximum error value)")
    output_opts.add_argument("--plot_colormap_min", type=float,
                             help="The lower bound used for the color map plot "
                             "(default: minimum error value)")
    output_opts.add_argument("--plot_colormap_max_percentile", type=float,
                             help="Percentile of the error distribution to be used "
                             "as the upper bound of the color map plot "
                             "(in %%, overrides --plot_colormap_min)")
    output_opts.add_argument("--save_plots", action="store_true",
                             help="Save plots?")
    output_opts.add_argument("--save_boxplots", action="store_true",
                             help="Save boxplots?")
    output_opts.add_argument("--save_results", action="store_true",
                             help="Save results?")

    usability_opts.add_argument("--no_warnings", action="store_true",
                                help="no warnings requiring user confirmation")
    usability_opts.add_argument("-v", "--verbose", action="store_true",
                                help="verbose output")
    usability_opts.add_argument("--silent", action="store_true",
                                help="don't print any output")
    usability_opts.add_argument("--debug", action="store_true",
                                help="verbose output with additional debug info")
    usability_opts.add_argument("-c", "--config",
                                help=".json file with parameters (priority over command line args)")

    main_parser = argparse.ArgumentParser(
        description="{}".format(basic_desc))
    sub_parsers = main_parser.add_subparsers(dest="subcommand")
    sub_parsers.required = True

    return shared_parser

if __name__ == '__main__':
    from evo import entry_points
    entry_points.evaluation()
