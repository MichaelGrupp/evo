#!/usr/bin/env python

from __future__ import print_function

import os
import shutil
import subprocess as sp

tmp_dir = "tmp"
cfg_dir = "cfg/traj"
here = os.path.dirname(os.path.abspath(__file__))

# always run in script location
os.chdir(here)

data = [
  "evo_traj euroc data/V102_groundtruth.csv --ref data/V102_groundtruth.csv",
  "evo_traj kitti data/KITTI_00_gt.txt data/KITTI_00_ORB.txt --ref data/KITTI_00_gt.txt",
  "evo_traj tum data/fr2_desk_groundtruth.txt data/fr2_desk_ORB.txt --ref data/fr2_desk_groundtruth.txt"
]
try:
  import rosbag
  data.append("evo_traj bag data/ROS_example.bag groundtruth S-PTAM --ref groundtruth")
except:
  pass

try:
  for d in data:
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
  if os.path.exists(tmp_dir):
    shutil.rmtree(tmp_dir)
