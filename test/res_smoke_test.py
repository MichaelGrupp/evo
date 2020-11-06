#!/usr/bin/env python

import os
import shutil
import subprocess as sp

tmp_dir = "tmp"
cfg_dir = "cfg/res"
here = os.path.dirname(os.path.abspath(__file__))

# always run in script location
os.chdir(here)

data = [
    "data/res_files/orb_rpe-for-each.zip data/res_files/sptam_rpe-for-each.zip",
    "data/res_files/orb_rpe.zip data/res_files/sptam_rpe.zip",
    "data/res_files/orb_ape.zip data/res_files/sptam_ape.zip",
]

try:
    for d in data:
        for cfg in os.listdir(cfg_dir):
            os.mkdir(tmp_dir)
            cfg = os.path.join(cfg_dir, cfg)
            cmd = "evo_res {} -c {}".format(d, cfg)
            print("[smoke test] {}".format(cmd))
            output = sp.check_output(cmd.split(" "), cwd=here)
            shutil.rmtree(tmp_dir)
except sp.CalledProcessError as e:
    print(e.output.decode("utf-8"))
    raise
finally:
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
