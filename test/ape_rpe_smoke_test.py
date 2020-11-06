#!/usr/bin/env python

import os
import shutil
import subprocess as sp

tmp_dir = "tmp"
cfg_dir = "cfg/ape_rpe"
here = os.path.dirname(os.path.abspath(__file__))

# always run in script location
os.chdir(here)

metrics = ["evo_ape", "evo_rpe"]

data = [
    "euroc data/V102_groundtruth.csv data/V102.txt",
    "kitti data/KITTI_00_gt.txt data/KITTI_00_ORB.txt",
    "tum data/fr2_desk_groundtruth.txt data/fr2_desk_ORB.txt"
]
try:
    import rosbag
    data.append("bag data/ROS_example.bag groundtruth S-PTAM")
except:
    pass

try:
    for m in metrics:
        for d in data:
            for cfg in os.listdir(cfg_dir):
                os.mkdir(tmp_dir)
                cfg = os.path.join(cfg_dir, cfg)
                cmd = "{} {} -c {}".format(m, d, cfg)
                print("[smoke test] {}".format(cmd))
                output = sp.check_output(cmd.split(" "), cwd=here)
                shutil.rmtree(tmp_dir)
except sp.CalledProcessError as e:
    print(e.output.decode("utf-8"))
    raise
finally:
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
