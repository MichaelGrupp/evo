#!/usr/bin/env python

import os
import shutil
import subprocess as sp
from pathlib import Path

tmp_dir = Path("tmp")
cfg_dir = Path("cfg/ape_rpe")
here = Path(__file__).absolute().parent

# always run in script location
os.chdir(here)

metrics = ["evo_ape", "evo_rpe"]

data = [
    "euroc data/V102_groundtruth.csv data/V102.txt",
    "kitti data/KITTI_00_gt.txt data/KITTI_00_ORB.txt",
    "tum data/fr2_desk_groundtruth.txt data/fr2_desk_ORB.txt",
    "bag data/ROS_example.bag groundtruth S-PTAM",
]

try:
    for m in metrics:
        for d in data:
            for cfg in cfg_dir.iterdir():
                tmp_dir.mkdir(exist_ok=True)
                cmd = f"{m} {d} -c {cfg}"
                print(f"[smoke test] {cmd}")
                output = sp.check_output(cmd.split(" "), cwd=here)
                shutil.rmtree(tmp_dir)
except sp.CalledProcessError as e:
    print(e.output.decode("utf-8"))
    raise
finally:
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
