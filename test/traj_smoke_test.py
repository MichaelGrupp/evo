#!/usr/bin/env python

from __future__ import print_function

import os
import glob
import shutil
import subprocess as sp

tmp_dir = "tmp"
common_cfg_dir = "cfg/traj/common"
here = os.path.dirname(os.path.abspath(__file__))

# always run in script location
os.chdir(here)

data = {
    "evo_traj euroc data/V102_groundtruth.csv": "cfg/traj/euroc",
    "evo_traj kitti data/KITTI_00_gt.txt data/KITTI_00_ORB.txt data/KITTI_00_SPTAM.txt "
    "--ref data/KITTI_00_gt.txt": "cfg/traj/kitti",
    "evo_traj tum data/fr2_desk_groundtruth.txt data/fr2_desk_ORB.txt data/fr2_desk_ORB_kf_mono.txt "
    "--ref data/fr2_desk_groundtruth.txt": "cfg/traj/tum"
}
try:
    import rosbag
    data["evo_traj bag data/ROS_example.bag groundtruth S-PTAM ORB-SLAM --ref groundtruth"] \
      = "cfg/traj/bag"
except:
    pass

try:
    for d in data.keys():
        for cfg_dir in (common_cfg_dir, data[d]):
            for cfg in os.listdir(cfg_dir):
                os.mkdir(tmp_dir)
                cfg = os.path.join(cfg_dir, cfg)
                cmd = "{} -c {}".format(d, cfg)
                print("[smoke test] {}".format(cmd))
                output = sp.check_output(cmd.split(" "), cwd=here)
                shutil.rmtree(tmp_dir)
except sp.CalledProcessError as e:
    print(e.output.decode("utf-8"))
    raise
finally:
    traj_files = glob.glob("./*.bag") + glob.glob("./*.kitti") + glob.glob(
        "./*.tum")
    print(repr(traj_files))
    for traj_file in traj_files:
        os.remove(traj_file)
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
