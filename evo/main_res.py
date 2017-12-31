#!/usr/bin/env python
# -*- coding: UTF8 -*-
# PYTHON_ARGCOMPLETE_OK
"""
main executable for viewing result files from the trajectory metric apps
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

from __future__ import print_function

SEP = "-" * 80  # separator line


def parser():
    import argparse
    basic_desc = "tool for processing one or multiple result files from ape or rpe"
    lic = "(c) michael.grupp@tum.de"
    main_parser = argparse.ArgumentParser(description="%s %s" % (basic_desc, lic))
    output_opts = main_parser.add_argument_group("output options")
    usability_opts = main_parser.add_argument_group("usability options")
    main_parser.add_argument("result_files", help="one or multiple result files", nargs='+')
    main_parser.add_argument("--use_abs_time",
                             help="use absolute timestamps instead of the seconds from start "
                                  "(if trajectories were saved to result file)",
                             action="store_true")
    output_opts.add_argument("-p", "--plot", help="show plot window", action="store_true")
    output_opts.add_argument("--plot_markers", help="plot with circle markers", action="store_true")
    output_opts.add_argument("--save_plot", help="path to save plot", default=None)
    output_opts.add_argument("--serialize_plot", help="path to serialize plot (experimental)",
                             default=None)
    output_opts.add_argument("--save_table",
                             help="path to a file to save the results in a table", default=None)
    usability_opts.add_argument("--no_warnings", help="no warnings requiring user confirmation",
                                action="store_true")
    usability_opts.add_argument("-v", "--verbose", help="verbose output", action="store_true")
    usability_opts.add_argument("--silent", help="don't print any output", action="store_true")
    usability_opts.add_argument("--debug", help="verbose output with additional debug info",
                                action="store_true")
    usability_opts.add_argument("-c", "--config",
                                help=".json file with parameters (priority over command line args)")
    return main_parser


def run(args):
    import os
    import sys
    import logging

    import pandas as pd
    import numpy as np
    from natsort import natsorted

    from evo.tools import file_interface, user, settings
    from evo.tools.settings import SETTINGS

    settings.configure_logging(args.verbose, args.silent, args.debug)
    if args.debug:
        import pprint
        logging.debug("main_parser config:\n"
                      + pprint.pformat({arg: getattr(args, arg) for arg in vars(args)}) + "\n")

    # store data in Pandas data frames for easier analysis
    raw_df = pd.DataFrame()
    stat_df = pd.DataFrame()
    info_df = pd.DataFrame()
    use_seconds = False

    for result_file in args.result_files:
        logging.debug(SEP)
        result_obj = file_interface.load_res_file(result_file, True)
        short_est_name = os.path.splitext(os.path.basename(result_obj.info["est_name"]))[0]
        error_array = result_obj.np_arrays["error_array"]
        if "seconds_from_start" in result_obj.np_arrays:
            seconds_from_start = result_obj.np_arrays["seconds_from_start"]
        else:
            seconds_from_start = None

        if not args.no_warnings and (short_est_name in info_df.columns):
            logging.warning("double entry detected: " + short_est_name)
            if not user.confirm("ignore? enter 'y' to go on or any other key to quit"):
                sys.exit()

        if SETTINGS.plot_usetex:
            short_est_name = short_est_name.replace("_", "\\_")

        if args.use_abs_time:
            if "timestamps" in result_obj.np_arrays:
                index = result_obj.np_arrays["timestamps"]
                use_seconds = True
            else:
                raise RuntimeError("no timestamps found for --use_abs_time")
        elif seconds_from_start is not None:
            index = seconds_from_start.tolist()
            use_seconds = True
        else:
            index = np.arange(0, error_array.shape[0])

        result_obj.info["traj. backup?"] = \
            all(k in result_obj.trajectories for k in ("traj_ref", "traj_est"))
        result_obj.info["res_file"] = result_file
        new_raw_df = pd.DataFrame({short_est_name: error_array.tolist()}, index=index)
        duplicates = new_raw_df.index.get_level_values(0).get_duplicates()
        if len(duplicates) != 0:
            logging.warning("duplicate indices in error array of {} - "
                            "keeping only first occurrence of duplicates".format(result_file))
            new_raw_df.drop_duplicates(keep="first", inplace=True)

        new_info_df = pd.DataFrame({short_est_name: result_obj.info})
        new_stat_df = pd.DataFrame({short_est_name: result_obj.stats})
        # natural sort num strings "10" "100" "20" -> "10" "20" "100"
        new_stat_df = new_stat_df.reindex(index=natsorted(new_stat_df.index))
        # column-wise concatenation
        raw_df = pd.concat([raw_df, new_raw_df], axis=1)
        info_df = pd.concat([info_df, new_info_df], axis=1)
        stat_df = pd.concat([stat_df, new_stat_df], axis=1)
        # if verbose: log infos of the current data
        logging.debug("\n" + result_obj.pretty_str(title=True, stats=False, info=True))

    logging.debug(SEP)
    logging.info("\nstatistics overview:\n" + stat_df.T.to_string(line_width=80) + "\n")

    # check titles
    first_title = info_df.ix["title", 0]
    first_res_file = info_df.ix["res_file", 0]
    if args.save_table or args.plot or args.save_plot:
        for short_est_name, column in info_df.iteritems():
            if column.ix["title"] != first_title and not args.no_warnings:
                logging.info(SEP)
                msg = ("mismatching titles, you probably use data from different metrics"
                       + "\nconflict:\n{} {}\n{}\n".format("<"*7, first_res_file, first_title)
                       + "{}\n{}\n".format("="*7, column.ix["title"])
                       + "{} {}\n\n".format(">"*7, column.ix["res_file"])
                       + "only the first one will be used as the title!")
                logging.warning(msg)
                if not user.confirm("plot/save anyway? - enter 'y' or any other key to exit"):
                    sys.exit()

    if args.save_table:
        logging.debug(SEP)
        if args.no_warnings or user.check_and_confirm_overwrite(args.save_table):
            table_fmt = SETTINGS.table_export_format
            if SETTINGS.table_export_transpose:
                getattr(stat_df.T, "to_" + table_fmt)(args.save_table)
            else:
                getattr(stat_df, "to_" + table_fmt)(args.save_table)
            logging.debug(table_fmt + " table saved to: " + args.save_table)

    if args.plot or args.save_plot or args.serialize_plot:
        # check if data has NaN "holes" due to different indices
        inconsistent = raw_df.isnull().values.any()
        if inconsistent and not args.no_warnings:
            logging.debug(SEP)
            logging.warning("data lengths/indices are not consistent, plotting could make no sense")

        from evo.tools import plot
        import matplotlib.pyplot as plt
        import seaborn as sns
        import math
        from scipy import stats

        # use default plot settings
        figsize = (SETTINGS.plot_figsize[0], SETTINGS.plot_figsize[1])
        use_cmap = SETTINGS.plot_multi_cmap.lower() != "none"
        colormap = SETTINGS.plot_multi_cmap if use_cmap else None
        linestyles = ["-o" for x in args.result_files] if args.plot_markers else None

        # labels according to first dataset
        title = first_title
        if "xlabel" in info_df.ix[:, 0].index:
            index_label = info_df.ix["xlabel", 0]
        else:
            index_label = "$t$ (s)" if use_seconds else "index"
        metric_label = info_df.ix["label", 0]

        plot_collection = plot.PlotCollection(title)
        # raw value plot
        fig_raw = plt.figure(figsize=figsize)
        # handle NaNs from concat() above
        raw_df.interpolate(method="index").plot(ax=fig_raw.gca(), colormap=colormap,
                                                style=linestyles, title=first_title)
        plt.xlabel(index_label)
        plt.ylabel(metric_label)
        plt.legend(frameon=True)
        plot_collection.add_figure("raw", fig_raw)

        # statistics plot
        fig_stats = plt.figure(figsize=figsize)
        exclude = stat_df.index.isin(["sse"])  # don't plot sse
        stat_df[~exclude].plot(kind="barh", ax=fig_stats.gca(), colormap=colormap, stacked=False)
        plt.xlabel(metric_label)
        plt.legend(frameon=True)
        plot_collection.add_figure("stats", fig_stats)

        # grid of distribution plots
        raw_tidy = pd.melt(raw_df, value_vars=list(raw_df.columns.values), var_name="estimate",
                           value_name=metric_label)
        col_wrap = 2 if len(args.result_files) <= 2 else math.ceil(len(args.result_files) / 2.0)
        dist_grid = sns.FacetGrid(raw_tidy, col="estimate", col_wrap=col_wrap)
        dist_grid.map(sns.distplot, metric_label)  # fits=stats.gamma
        plot_collection.add_figure("histogram", dist_grid.fig)

        # box plot
        fig_box = plt.figure(figsize=figsize)
        ax = sns.boxplot(x=raw_tidy["estimate"], y=raw_tidy[metric_label], ax=fig_box.gca())
        # ax.set_xticklabels(labels=[item.get_text() for item in ax.get_xticklabels()], rotation=30)
        plot_collection.add_figure("box_plot", fig_box)

        # violin plot
        fig_violin = plt.figure(figsize=figsize)
        ax = sns.violinplot(x=raw_tidy["estimate"], y=raw_tidy[metric_label], ax=fig_violin.gca())
        # ax.set_xticklabels(labels=[item.get_text() for item in ax.get_xticklabels()], rotation=30)
        plot_collection.add_figure("violin_histogram", fig_violin)

        if args.plot:
            plot_collection.show()
        if args.save_plot:
            logging.debug(SEP)
            plot_collection.export(args.save_plot, confirm_overwrite=not args.no_warnings)
        if args.serialize_plot:
            logging.debug(SEP)
            plot_collection.serialize(args.serialize_plot, confirm_overwrite=not args.no_warnings)


if __name__ == '__main__':
    from evo import entry_points
    entry_points.res()
