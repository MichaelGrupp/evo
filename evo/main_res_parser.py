import argparse


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
