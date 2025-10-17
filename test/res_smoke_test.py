#!/usr/bin/env python

import os
import shutil
import subprocess as sp
from pathlib import Path

tmp_dir = Path("tmp")
cfg_dir = Path("cfg/res")
here = Path(__file__).absolute().parent

# always run in script location
os.chdir(here)

data = [
    "data/res_files/orb_rpe-for-each.zip data/res_files/sptam_rpe-for-each.zip",
    "data/res_files/orb_rpe.zip data/res_files/sptam_rpe.zip",
    "data/res_files/orb_ape.zip data/res_files/sptam_ape.zip",
]

try:
    for d in data:
        for cfg in cfg_dir.iterdir():
            tmp_dir.mkdir(exist_ok=True)
            cmd = f"evo_res {d} -c {cfg}"
            print(f"[smoke test] {cmd}")
            output = sp.check_output(cmd.split(" "), cwd=here)
            shutil.rmtree(tmp_dir)
except sp.CalledProcessError as e:
    print(e.output.decode("utf-8"))
    raise
finally:
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
