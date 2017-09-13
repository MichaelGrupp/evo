from setuptools import setup
from setuptools.command.install import install

import os
import sys
import subprocess as sp

# monkey patch because setuptools entry_points are slow as fuck
# https://github.com/ninjaaron/fast-entry_points
import fastentrypoints


def python_below_34():
    return sys.version_info[0] < 3 or sys.version_info[1] < 4


def _post_install(install_lib_dir):
    from evo.main_config import reset_pkg_settings
    reset_pkg_settings(os.path.join(install_lib_dir, "evo", "settings.json"))
    sp.call(["activate-global-python-argcomplete"])
    # sp.call(["jupyter", "nbextension", "enable", "--py", "--sys-prefix", "widgetsnbextension"])


# https://stackoverflow.com/a/18159969/6288017
class CustomInstall(install):
    def run(self):
        install.run(self)
        self.execute(_post_install, (self.install_lib,), msg="running post install task")


setup(name="evo",
      version=open("evo/version").read(),
      description="Python package for the evaluation of odometry and SLAM",
      author="Michael Grupp",
      author_email="michael.grupp@tum.de",
      url="https://github.com/MichaelGrupp/evo",
      license="GNU GPL v3",
      keywords=["SLAM", "odometry", "vision", "laser", "visual", "robotics", "evaluation", "metric"],
      packages=["evo", "evo.algorithms", "evo.tools"],
      package_data={"evo": ["README.md", "settings.json", "version", "LICENSE"]},
      entry_points={"console_scripts": ["evo_ape=evo.entry_points:ape",
                                        "evo_rpe=evo.entry_points:rpe",
                                        "evo_traj=evo.entry_points:traj",
                                        "evo_res=evo.entry_points:res",
                                        "evo_rpe-for-each=evo.entry_points:rpe_for_each",
                                        "evo_config=evo.main_config:main",
                                        "evo_fig=evo.main_fig:main",
                                        "evo=evo.main_evo:main"]},
      zip_safe=False,
      install_requires=["numpy", "matplotlib", "scipy", "pandas", "seaborn",
                        "natsort", "argcomplete", "colorama", "pygments"]  # "jupyter"
                       + (["enum34"] if python_below_34() else []),
      cmdclass={"install": CustomInstall}
      )

