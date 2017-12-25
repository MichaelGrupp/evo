from __future__ import print_function
from setuptools import setup, Command
from setuptools.command.install import install

import os
import sys
import shutil
import subprocess as sp
from pwd import getpwnam


# monkey patch because setuptools entry_points are slow as fuck
# https://github.com/ninjaaron/fast-entry_points
import fastentrypoints


HERE = os.path.abspath(os.path.dirname(__file__))


def python_below_34():
    return sys.version_info[0] < 3 or sys.version_info[1] < 4


def run_as_caller():
    caller = os.environ["SUDO_USER"] if "SUDO_USER" in os.environ else os.environ["USER"]
    uid = getpwnam(caller).pw_uid
    gid = getpwnam(caller).pw_gid
    os.setgid(gid)
    os.setuid(uid)


def _post_install(install_lib_dir):
    # argcomplete
    print("activating argcomplete")
    try:
        sp.check_call("activate-global-python-argcomplete", shell=True)
        print("done - argcomplete should work now")
    except sp.CalledProcessError as e:
        print("error:", e.output, file=sys.stderr)
    # IPython profile
    user = os.environ["SUDO_USER"] if "SUDO_USER" in os.environ else os.environ["USER"]
    home_dir = os.path.expanduser("~{}".format(user))
    ipython_dir = os.path.join(home_dir, ".ipython")
    os.environ["IPYTHONDIR"] = ipython_dir
    print("installing evo IPython profile for user", user)
    try:
        sp.check_call(["ipython", "--version"])
        sp.check_call(["ipython", "profile", "create", "evo",
                       "--ipython-dir", ipython_dir], preexec_fn=run_as_caller)
        profile_dir = sp.check_output(["ipython", "profile", "locate", "evo"],
                                      preexec_fn=run_as_caller)
        profile_dir = profile_dir.replace("\n", "")
        shutil.move(os.path.join(install_lib_dir, "evo", "ipython_config.py"),
                    os.path.join(profile_dir, "ipython_config.py"))
    except sp.CalledProcessError as e:
        print("IPython error", e.output, file=sys.stderr)


class CustomInstall(install):
    def run(self):
        install.run(self)
        self.execute(_post_install, (self.install_lib,),
                     msg="running post install task")


# cmd: python setup.py upload
class UploadCommand(Command):
    description = "Build and publish the package."
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            print("Removing previous dist/ ...")
            shutil.rmtree(os.path.join(HERE, "dist"))
        except OSError:
            pass
        print("Building source distribution...")
        sp.check_call([sys.executable, "setup.py", "sdist"])
        print("Uploading package to PyPi...")
        sp.check_call(["twine", "upload", "dist/*"])
        sys.exit()


setup(
    name="evo",
    version=open("evo/version").read(),
    description="Python package for the evaluation of odometry and SLAM",
    author="Michael Grupp",
    author_email="michael.grupp@tum.de",
    url="https://github.com/MichaelGrupp/evo",
    license="GPLv3",
    keywords=[
        "SLAM", "odometry", "trajectory", "evaluation", "metric",
        "vision", "laser", "visual", "robotics"
    ],
    packages=["evo", "evo.core", "evo.tools"],
    package_data={"evo": ["version", "LICENSE"]},
    entry_points={"console_scripts": [
        "evo_ape=evo.entry_points:ape",
        "evo_rpe=evo.entry_points:rpe",
        "evo_traj=evo.entry_points:traj",
        "evo_res=evo.entry_points:res",
        "evo_rpe-for-each=evo.entry_points:rpe_for_each",
        "evo_config=evo.main_config:main",
        "evo_fig=evo.main_fig:main",
        "evo_ipython=evo.main_ipython:main",
        "evo=evo.main_evo:main"
    ]},
    zip_safe=False,
    cmdclass={
        "install": CustomInstall,
        "upload": UploadCommand
    },
    install_requires=[
        "numpy",
        "matplotlib",
        "scipy",
        "pandas",
        "seaborn",
        "natsort",
        "argcomplete",
        "colorama",
        "pygments"
        #jupyter
    ] + (["enum34"] if python_below_34() else []),
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: CPython"
    ]
)
