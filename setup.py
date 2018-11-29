from __future__ import print_function
from setuptools import setup, Command
from setuptools.command.install import install

import os
import sys
import shutil
import subprocess as sp

# monkey patch because setuptools entry_points are slow as fuck
# https://github.com/ninjaaron/fast-entry_points
import fastentrypoints

HERE = os.path.abspath(os.path.dirname(__file__))


def python_below_34():
    return sys.version_info[0] < 3 or sys.version_info[1] < 4


def _run_as_caller():
    if os.name == "nt":
        return
    from pwd import getpwnam
    if "SUDO_USER" in os.environ:
        caller = os.environ["SUDO_USER"]
    else:
        caller = os.environ["USER"]
    uid = getpwnam(caller).pw_uid
    gid = getpwnam(caller).pw_gid
    os.setgid(gid)
    os.setuid(uid)


def _get_home_dir():
    user = os.getenv("SUDO_USER")
    if user is not None:
        home_dir = os.path.expanduser("~{}".format(user))
    else:
        home_dir = os.path.expanduser("~")
    return home_dir


def install_ipython_profile(install_lib_dir):
    from evo.tools.compat import which
    home_dir = _get_home_dir()
    ipython_dir = os.path.join(home_dir, ".ipython")
    os.environ["IPYTHONDIR"] = ipython_dir
    print("Installing evo IPython profile...")
    ipython = "ipython3" if sys.version_info >= (3, 0) else "ipython2"
    if which(ipython) is None:
        # Use the non-explicit ipython name if ipython2/3 is not in PATH.
        ipython = "ipython"
        if which(ipython) is None:
            print("IPython is not installed", file=sys.stderr)
            return
    try:
        sp.check_call([
            ipython, "profile", "create", "evo", "--ipython-dir", ipython_dir
        ], preexec_fn=_run_as_caller)
        profile_dir = sp.check_output([ipython, "profile", "locate", "evo"],
                                      preexec_fn=_run_as_caller)
        if sys.version_info >= (3, 0):
            profile_dir = profile_dir.decode("UTF-8").replace("\n", "")
        else:
            profile_dir = profile_dir.replace("\n", "")
        shutil.copy(
            os.path.join(install_lib_dir, "evo", "ipython_config.py"),
            os.path.join(profile_dir, "ipython_config.py"))
    except sp.CalledProcessError as e:
        print("IPython error:", e.output, file=sys.stderr)
    except Exception as e:
        print("Unexpected error:", e.message, file=sys.stderr)


def activate_argcomplete():
    if os.name == "nt":
        return
    print("Activating argcomplete...")
    try:
        sp.check_call("activate-global-python-argcomplete", shell=True)
        print("Done - argcomplete should work now.")
    except sp.CalledProcessError as e:
        print("Error:", e.output, file=sys.stderr)


def _post_install(install_lib_dir):
    activate_argcomplete()
    install_ipython_profile(install_lib_dir)


class CustomInstall(install):
    def run(self):
        install.run(self)
        self.execute(_post_install, (self.install_lib, ),
                     msg="Running post install task of evo...")


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


# yapf: disable
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
        "evo_evaluation=evo.entry_points:evaluation",
        "evo_ape=evo.entry_points:ape",
        "evo_rpe=evo.entry_points:rpe",
        "evo_traj=evo.entry_points:traj",
        "evo_res=evo.entry_points:res",
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
        "pygments",
        "pyyaml"
        #jupyter
    ] + (["enum34"] if python_below_34() else []),
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Topic :: Scientific/Engineering",
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
# yapf: enable
