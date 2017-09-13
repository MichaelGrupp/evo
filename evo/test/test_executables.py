#!/usr/bin/env python
"""
just some quick and dirty application test
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

import sys
import subprocess as sp


def green(string):
    return "\033[32m" + string + "\033[0m"


def blue(string):
    return "\033[34m" + string + "\033[0m"


infos, cmds = [], []
test_plot = False
test_bag = True

infos.append("APE with TUM files")
cmds.append(".././main_ape.py tum ../test/data/freiburg1_xyz-groundtruth.txt ../test/data/freiburg1_xyz-rgbdslam.txt")
infos.append("APE with KITTI files")
cmds.append(".././main_ape.py kitti ../test/data/KITTI_00_gt.txt ../test/data/KITTI_00_ORB.txt")
if test_bag:
    infos.append("APE with ROS bag")
    cmds.append(".././main_ape.py bag ../test/data/ROS_example.bag groundtruth ORB-SLAM")
infos.append("RPE with TUM files")
cmds.append(".././main_rpe.py tum ../test/data/freiburg1_xyz-groundtruth.txt ../test/data/freiburg1_xyz-rgbdslam.txt")
infos.append("RPE with KITTI files")
cmds.append(".././main_rpe.py kitti ../test/data/KITTI_00_gt.txt ../test/data/KITTI_00_ORB.txt")
if test_bag:
    infos.append("RPE with ROS bag")
    cmds.append(".././main_rpe.py bag ../test/data/ROS_example.bag groundtruth ORB-SLAM")

try:
    for info, cmd in zip(infos, cmds):
        cmd += " --help"
        info += ", help"
        print("\n" + green(info))
        print(blue(cmd))
        sp.check_call(cmd, shell=True)

    for info, cmd in zip(infos, cmds):
        print("\n" + green(info))
        print(blue(cmd))
        sp.check_call(cmd, shell=True)

    info = "APE with alignment"
    cmd = ".././main_ape.py tum ../test/data/freiburg1_xyz-groundtruth.txt ../test/data/freiburg1_xyz-rgbdslam.txt -a"
    cmd += " --plot" if test_plot else ""
    print("\n" + green(info))
    print(blue(cmd))
    sp.check_call(cmd, shell=True)

    info = "APE with alignment and scale correction"
    cmd = ".././main_ape.py tum ../test/data/freiburg1_xyz-groundtruth.txt ../test/data/freiburg1_xyz-rgbdslam.txt " \
          "--correct_scale --align"
    cmd += " --plot" if test_plot else ""
    print("\n" + green(info))
    print(blue(cmd))
    sp.check_call(cmd, shell=True)

    info = "APE with scale correction only"
    cmd = ".././main_ape.py tum ../test/data/freiburg1_xyz-groundtruth.txt ../test/data/freiburg1_xyz-rgbdslam.txt " \
          "--correct_scale"
    cmd += " --plot" if test_plot else ""
    print("\n" + green(info))
    print(blue(cmd))
    sp.check_call(cmd, shell=True)

    for info, cmd in zip(infos, cmds):
        cmd += " --verbose"
        info += ", verbose"
        print("\n" + green(info))
        print(blue(cmd))
        sp.check_call(cmd, shell=True)

    for info, cmd in zip(infos, cmds):
        cmd += " --debug"
        info += ", debug mode"
        print("\n" + green(info))
        print(blue(cmd))
        sp.check_call(cmd, shell=True)

    if test_plot:
        for info, cmd in zip(infos, cmds):
            cmd += " -v --plot"
            info += ", verbose and plot"
            print("\n" + green(info))
            print(blue(cmd))
            sp.check_call(cmd, shell=True)

    for info, cmd in zip(infos, cmds):
        cmd += " -v --silent"
        info += ", verbose and silent"
        print("\n" + green(info))
        print(blue(cmd))
        sp.check_call(cmd, shell=True)

    for p_rel in ["trans_part", "rot_part", "angle_deg", "angle_rad", "full"]:
        for info, cmd in zip(infos, cmds):
            cmd += " -r " + p_rel
            info += ", pose relation: " + p_rel
            print("\n" + green(info))
            print(blue(cmd))
            sp.check_call(cmd, shell=True)

except sp.CalledProcessError as e:
    print(e.output)
    sys.exit(1)

print(green("\nSUCCESS"))
