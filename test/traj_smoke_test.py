#!/usr/bin/env python

import os
import glob
import shutil
import subprocess as sp
from pathlib import Path

TMP_DIR = Path("tmp")
COMMON_CONFIG_DIR = Path("cfg/traj/common")
HERE = Path(__file__).absolute().parent

# always run in script location
os.chdir(HERE)

commands_with_config_dir = {
    "evo_traj euroc data/V102_groundtruth.csv --ref data/V102_groundtruth.csv": "cfg/traj/euroc",
    "evo_traj kitti data/KITTI_00_gt.txt data/KITTI_00_ORB.txt data/KITTI_00_SPTAM.txt "
    "--ref data/KITTI_00_gt.txt": "cfg/traj/kitti",
    "evo_traj tum data/fr2_desk_groundtruth.txt data/fr2_desk_ORB.txt data/fr2_desk_ORB_kf_mono.txt "
    "--ref data/fr2_desk_groundtruth.txt": "cfg/traj/tum",
    "evo_traj bag data/ROS_example.bag groundtruth S-PTAM ORB-SLAM --ref groundtruth": "cfg/traj/bag"
}

if os.getenv("ROS_DISTRO") is not None:
    # TF interface is able to load TF from ROS 1 bags in ROS 2 and vice versa.
    commands_with_config_dir.update({
        "evo_traj bag data/tf_example.bag /tf:odom.base_link --ref /tf:odom.base_footprint": "cfg/traj/bag",
        "evo_traj bag2 data/tf_example /tf:odom.base_link --ref /tf:odom.base_footprint": "cfg/traj/bag",
    })

try:
    for command in commands_with_config_dir.keys():
        for config_dir in (COMMON_CONFIG_DIR,
                           Path(commands_with_config_dir[command])):
            for config_file in config_dir.iterdir():
                TMP_DIR.mkdir(exist_ok=True)
                full_command = f"{command} -c {config_file}"
                print("[smoke test] {}".format(full_command))
                output = sp.check_output(full_command.split(" "), cwd=HERE)
                shutil.rmtree(TMP_DIR)
except sp.CalledProcessError as e:
    print(e.output.decode("utf-8"))
    raise
finally:
    traj_files = glob.glob("./*.bag") + glob.glob("./*.kitti") + glob.glob(
        "./*.tum")
    for traj_file in traj_files:
        os.remove(traj_file)
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
