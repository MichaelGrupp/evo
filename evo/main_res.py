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

import argparse
import logging
import sys
import typing

import pandas as pd

from evo.core.result import merge_results, Result
from evo.tools import file_interface, log, user, pandas_bridge
from evo.tools.settings import SETTINGS

logger = logging.getLogger(__name__)

SEP = "-" * 80  # separator line

CONFLICT_TEMPLATE = """
Mismatching titles - risk of aggregating data from different metrics. Conflict:

<<<<<<< {0}
{1}
=======
{2}
>>>>>>> {3}

Only the first one will be used as the title!"""


def parser() -> argparse.ArgumentParser:
    basic_desc = "tool for processing one or multiple result files"
    lic = "(c) evo authors"
    main_parser = argparse.ArgumentParser(description="%s %s" %
                                          (basic_desc, lic))
    output_opts = main_parser.add_argument_group("output options")
    usability_opts = main_parser.add_argument_group("usability options")
    main_parser.add_argument("result_files",
                             help="one or multiple result files", nargs='+')
    main_parser.add_argument("--merge",
                             help="merge the results into a single one",
                             action="store_true")
    main_parser.add_argument("--use_rel_time",
                             help="use relative timestamps if available",
                             action="store_true")
    main_parser.add_argument("--use_filenames",
                             help="use the filenames to label the data",
                             action="store_true")
    main_parser.add_argument("--ignore_title",
                             help="don't try to find a common metric title",
                             action="store_true")
    output_opts.add_argument("-p", "--plot", help="show plot window",
                             action="store_true")
    output_opts.add_argument("--plot_markers", help="plot with circle markers",
                             action="store_true")
    output_opts.add_argument("--save_plot", help="path to save plot",
                             default=None)
    output_opts.add_argument("--serialize_plot",
                             help="path to serialize plot (experimental)",
                             default=None)
    output_opts.add_argument(
        "--save_table", help="path to a file to save the results in a table",
        default=None)
    output_opts.add_argument("--logfile", help="Local logfile path.",
                             default=None)
    usability_opts.add_argument("--no_warnings",
                                help="no warnings requiring user confirmation",
                                action="store_true")
    usability_opts.add_argument("-v", "--verbose", help="verbose output",
                                action="store_true")
    usability_opts.add_argument("--silent", help="don't print any output",
                                action="store_true")
    usability_opts.add_argument(
        "--debug", help="verbose output with additional debug info",
        action="store_true")
    usability_opts.add_argument(
        "-c", "--config",
        help=".json file with parameters (priority over command line args)")
    return main_parser


def run(args: argparse.Namespace) -> None:

    pd.options.display.width = 80
    pd.options.display.max_colwidth = 20

    log.configure_logging(args.verbose, args.silent, args.debug,
                          local_logfile=args.logfile)
    if args.debug:
        import pprint
        arg_dict = {arg: getattr(args, arg) for arg in vars(args)}
        logger.debug("main_parser config:\n{}\n".format(
            pprint.pformat(arg_dict)))

    df = pandas_bridge.load_results_as_dataframe(args.result_files,
                                                 args.use_filenames,
                                                 args.merge)

    keys = df.columns.values.tolist()
    if SETTINGS.plot_usetex:
        keys = [key.replace("_", "\\_") for key in keys]
        df.columns = keys
    duplicates = [x for x in keys if keys.count(x) > 1]
    if duplicates:
        logger.error("Values of 'est_name' must be unique - duplicates: {}\n"
                     "Try using the --use_filenames option to use filenames "
                     "for labeling instead.".format(", ".join(duplicates)))
        sys.exit(1)

    # derive a common index type if possible - preferably timestamps
    common_index = None
    time_indices = ["timestamps", "seconds_from_start", "sec_from_start"]
    if args.use_rel_time:
        del time_indices[0]
    for idx in time_indices:
        if idx not in df.loc["np_arrays"].index:
            continue
        if df.loc["np_arrays", idx].isnull().values.any():
            continue
        else:
            common_index = idx
            break

    # build error_df (raw values) according to common_index
    if common_index is None:
        # use a non-timestamp index
        error_df = pd.DataFrame(df.loc["np_arrays", "error_array"].tolist(),
                                index=keys).T
    else:
        error_df = pd.DataFrame()
        for key in keys:
            new_error_df = pd.DataFrame(
                {key: df.loc["np_arrays", "error_array"][key]},
                index=df.loc["np_arrays", common_index][key])
            duplicates = new_error_df.index.duplicated(keep="first")
            if any(duplicates):
                logger.warning(
                    "duplicate indices in error array of {} - "
                    "keeping only first occurrence of duplicates".format(key))
                new_error_df = new_error_df[~duplicates]  # type: ignore
            error_df = pd.concat([error_df, new_error_df], axis=1)

    # check titles
    first_title = df.loc["info", "title"][0] if not args.ignore_title else ""
    first_file = args.result_files[0]
    if not args.no_warnings and not args.ignore_title:
        checks = df.loc["info", "title"] != first_title
        for i, differs in enumerate(checks):
            if not differs:
                continue
            else:
                mismatching_title = df.loc["info", "title"][i]
                mismatching_file = args.result_files[i]
                logger.debug(SEP)
                logger.warning(
                    CONFLICT_TEMPLATE.format(first_file, first_title,
                                             mismatching_title,
                                             mismatching_file))
                if not user.confirm(
                        "You can use --ignore_title to just aggregate data.\n"
                        "Go on anyway? - enter 'y' or any other key to exit"):
                    sys.exit()

    logger.debug(SEP)
    logger.debug("Aggregated dataframe:\n{}".format(
        df.to_string(line_width=80)))

    # show a statistics overview
    logger.debug(SEP)
    if not args.ignore_title:
        logger.info("\n" + first_title + "\n\n")
    logger.info(df.loc["stats"].T.to_string(line_width=80) + "\n")

    if args.save_table:
        logger.debug(SEP)
        if SETTINGS.table_export_data.lower() == "error_array":
            data = error_df
        elif SETTINGS.table_export_data.lower() in ("info", "stats"):
            data = df.loc[SETTINGS.table_export_data.lower()]
        else:
            raise ValueError("unsupported export data specifier: {}".format(
                SETTINGS.table_export_data))
        pandas_bridge.save_df_as_table(data, args.save_table,
                                       confirm_overwrite=not args.no_warnings)

    if args.plot or args.save_plot or args.serialize_plot:
        # check if data has NaN "holes" due to different indices
        inconsistent = error_df.isnull().values.any()
        if inconsistent and common_index != "timestamps" and not args.no_warnings:
            logger.debug(SEP)
            logger.warning("Data lengths/indices are not consistent, "
                           "raw value plot might not be correctly aligned")

        from evo.tools import plot
        import matplotlib.pyplot as plt
        import seaborn as sns
        import math

        # use default plot settings
        figsize = (SETTINGS.plot_figsize[0], SETTINGS.plot_figsize[1])
        use_cmap = SETTINGS.plot_multi_cmap.lower() != "none"
        colormap = SETTINGS.plot_multi_cmap if use_cmap else None
        linestyles = ["-o" for x in args.result_files
                      ] if args.plot_markers else None

        # labels according to first dataset
        if "xlabel" in df.loc["info"].index and not df.loc[
                "info", "xlabel"].isnull().values.any():
            index_label = df.loc["info", "xlabel"][0]
        else:
            index_label = "$t$ (s)" if common_index else "index"
        metric_label = df.loc["info", "label"][0]

        plot_collection = plot.PlotCollection(first_title)
        # raw value plot
        fig_raw = plt.figure(figsize=figsize)
        # handle NaNs from concat() above
        error_df.interpolate(method="index", limit_area="inside").plot(
            ax=fig_raw.gca(), colormap=colormap, style=linestyles,
            title=first_title, alpha=SETTINGS.plot_trajectory_alpha)
        plt.xlabel(index_label)
        plt.ylabel(metric_label)
        plt.legend(frameon=True)
        plot_collection.add_figure("raw", fig_raw)

        # statistics plot
        if SETTINGS.plot_statistics:
            fig_stats = plt.figure(figsize=figsize)
            include = df.loc["stats"].index.isin(SETTINGS.plot_statistics)
            if any(include):
                df.loc["stats"][include].plot(kind="barh", ax=fig_stats.gca(),
                                              colormap=colormap, stacked=False)
                plt.xlabel(metric_label)
                plt.legend(frameon=True)
                plot_collection.add_figure("stats", fig_stats)

        # grid of distribution plots
        raw_tidy = pd.melt(error_df, value_vars=list(error_df.columns.values),
                           var_name="estimate", value_name=metric_label)
        col_wrap = 2 if len(args.result_files) <= 2 else math.ceil(
            len(args.result_files) / 2.0)
        dist_grid = sns.FacetGrid(raw_tidy, col="estimate", col_wrap=col_wrap)
        # TODO: see issue #98
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            dist_grid.map(sns.distplot, metric_label)  # fits=stats.gamma
        plot_collection.add_figure("histogram", dist_grid.fig)

        # box plot
        fig_box = plt.figure(figsize=figsize)
        ax = sns.boxplot(x=raw_tidy["estimate"], y=raw_tidy[metric_label],
                         ax=fig_box.gca())
        # ax.set_xticklabels(labels=[item.get_text() for item in ax.get_xticklabels()], rotation=30)
        plot_collection.add_figure("box_plot", fig_box)

        # violin plot
        fig_violin = plt.figure(figsize=figsize)
        ax = sns.violinplot(x=raw_tidy["estimate"], y=raw_tidy[metric_label],
                            ax=fig_violin.gca())
        # ax.set_xticklabels(labels=[item.get_text() for item in ax.get_xticklabels()], rotation=30)
        plot_collection.add_figure("violin_histogram", fig_violin)

        if args.plot:
            plot_collection.show()
        if args.save_plot:
            logger.debug(SEP)
            plot_collection.export(args.save_plot,
                                   confirm_overwrite=not args.no_warnings)
        if args.serialize_plot:
            logger.debug(SEP)
            plot_collection.serialize(args.serialize_plot,
                                      confirm_overwrite=not args.no_warnings)


if __name__ == '__main__':
    from evo import entry_points
    entry_points.res()
