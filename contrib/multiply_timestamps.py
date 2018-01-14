#!/usr/bin/env python
# -*- coding: utf-8 -*-

from evo.tools import file_interface

DESC = """multiply the timestamps of a TUM trajectory file by a factor"""


def main(traj_file, factor):
    traj = file_interface.read_tum_trajectory_file(traj_file)
    traj.timestamps = traj.timestamps * factor
    file_interface.write_tum_trajectory_file(traj_file, traj)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description=DESC)
    parser.add_argument("traj_file", help="trajectory in TUM format")
    parser.add_argument("factor", help="factor", type=float)
    args = parser.parse_args()
    main(args.traj_file, args.factor)
