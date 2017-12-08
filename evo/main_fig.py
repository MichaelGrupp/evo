#!/usr/bin/env python
# -*- coding: UTF8 -*-
# PYTHON_ARGCOMPLETE_OK
"""
plot editor
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
import logging

SEP = "-" * 80  # separator line


def main():
    import argparse
    import argcomplete
    basic_desc = "experimental tool for opening a serialized PlotCollection (pickle format)"
    lic = "(c) michael.grupp@tum.de"
    main_parser = argparse.ArgumentParser(description="%s %s" % (basic_desc, lic))
    main_parser.add_argument("in_file", help="path to a serialized plot_collection")
    main_parser.add_argument("-t", "--title", help="custom title (default: file name)")
    main_parser.add_argument("--save_plot", help="path to save plot", default=None)
    main_parser.add_argument("--serialize_plot", help="path to re-serialize PlotCollection",
                             default=None)
    main_parser.add_argument("--to_html", help="convert to html (requires mpld3 library)",
                             action="store_true")
    main_parser.add_argument("--no_warnings", help="no warnings requiring user confirmation",
                             action="store_true")
    argcomplete.autocomplete(main_parser)
    args = main_parser.parse_args()

    from evo.tools import plot, settings, user
    settings.configure_logging(verbose=True)
    if not args.title:
        title = os.path.basename(args.in_file)
    else:
        title = args.title
    if not args.no_warnings:
        logging.warning("Please note that this tool is experimental and not guranteed to work.\n"
                        "Only works if the same plot settings are used as for serialization.\n"
                        "If not, try: evo_config show/set \n" + SEP)
    
    plot_collection = plot.PlotCollection(title, deserialize=args.in_file)
    logging.debug("deserialized PlotCollection: " + str(plot_collection))
    plot_collection.show()

    if args.serialize_plot:
        logging.debug(SEP)
        plot_collection.serialize(args.serialize_plot, confirm_overwrite=not args.no_warnings)
    if args.save_plot:
        logging.debug(SEP)
        plot_collection.export(args.save_plot, confirm_overwrite=not args.no_warnings)
    if args.to_html:
        import mpld3
        logging.debug(SEP + "\nhtml export\n")
        for name, fig in plot_collection.figures.items():
            html = mpld3.fig_to_html(fig)
            out = name + ".html"
            with open(out, 'w') as f:
                logging.debug(out)
                f.write(html)
    if not args.no_warnings:
        logging.debug(SEP)
        if user.confirm("save changes & overwrite original file "
                        + args.in_file + "? (y/n)"):
            plot_collection.serialize(args.in_file, confirm_overwrite=False)


if __name__ == '__main__':
    main()
