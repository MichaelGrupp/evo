#!/usr/bin/env python

import os
import glob
import shutil
import subprocess as sp
from pathlib import Path

tmp_dir = Path("tmp")
common_cfg_dir = Path("cfg/traj/common")
here = Path(__file__).absolute().parent

# always run in script location
os.chdir(here)

data = {
    "evo_traj euroc data/V102_groundtruth.csv --ref data/V102_groundtruth.csv": "cfg/traj/euroc",
    "evo_traj kitti data/KITTI_00_gt.txt data/KITTI_00_ORB.txt data/KITTI_00_SPTAM.txt "
    "--ref data/KITTI_00_gt.txt": "cfg/traj/kitti",
    "evo_traj tum data/fr2_desk_groundtruth.txt data/fr2_desk_ORB.txt data/fr2_desk_ORB_kf_mono.txt "
    "--ref data/fr2_desk_groundtruth.txt": "cfg/traj/tum",
    "evo_traj bag data/ROS_example.bag groundtruth S-PTAM ORB-SLAM --ref groundtruth": "cfg/traj/bag"
}

if os.getenv("ROS_DISTRO", "") == "noetic":
    data.update({
        "evo_traj bag data/tf_example.bag /tf:odom.base_link --ref /tf:odom.base_footprint": "cfg/traj/bag",
    })

try:
    for d in data.keys():
        for cfg_dir in (common_cfg_dir, Path(data[d])):
            for cfg in cfg_dir.iterdir():
                tmp_dir.mkdir(exist_ok=True)
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
    for traj_file in traj_files:
        os.remove(traj_file)
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
