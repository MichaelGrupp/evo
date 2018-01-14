#!/usr/bin/env python
# -*- coding: utf-8 -*-

from evo.tools import file_interface

DESC = """rename the 'est_name' field in a result file"""


def main(res_file, new_name):
    result = file_interface.load_res_file(res_file)
    result.info["est_name"] = new_name
    file_interface.save_res_file(res_file, result)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description=DESC)
    parser.add_argument("res_file", help="evo result file")
    parser.add_argument("new_name", help="new 'est_name'")
    args = parser.parse_args()
    main(args.res_file, args.new_name)
