# Installation in a virtual environment

Virtual environments allow you to install Python packages in an isolated environment.
This is usually a good idea because it reduces the risk that you mess up your system's Python packages by installing globally with `pip`.
Additionally, you can have multiple environments in parallel that don't interfere with each other.

## virtualenv & virtualenvwrapper

`virtualenvwrapper` is highly recommended, it makes using virtual environments much more comfortable.

Below are installation instructions for Ubuntu.
If you use any other OS, see the documentation for how to install it on your system:

* virtualenvwrapper: https://virtualenvwrapper.readthedocs.io/en/latest/
* virtualenv documentation: https://virtualenv.pypa.io/en/latest/

### virtualenvwrapper installation on Ubuntu

***The following steps have been verified on Ubuntu 20. They probably also work on other Debian-based Linux distros.***

Install `virtualenv` and `virtualenvwrapper`:
```shell
sudo apt install python3-virtualenvwrapper
```

Add setup code for `virtualenvwrapper` to your shell startup file:
```shell
echo "export WORKON_HOME=$HOME/.virtualenvs && source /usr/share/virtualenvwrapper/virtualenvwrapper.sh" >> ~/.bashrc

source ~/.bashrc
```

## Setting up a virtualenv for evo

Once `virtualenvwrapper` is installed, we can create the virtual environment.
The `--system-site-packages` flag is recommended if you are using ROS and want to use rosbags with evo:
it enables to import the `rosbag` Python module that is installed outside of the virtualenv on your system.
```shell
mkvirtualenv evaluation --system-site-packages
```

To activate the environment, type:
```shell
workon evaluation
```

Install evo and its dependencies inside the virtual environment:
```shell
pip install --ignore-installed evo --no-binary evo

# or alternatively from source:
cd <evo>  # go to evo base source folder that contains setup.py
pip install --ignore-installed --editable . --no-binary evo
```
Now, the package should be installed in the virtualenv and you can use it.


Check if evo is installed correctly by running:
```
evo
```

To leave the virtualenv, close the shell or type:
```shell
deactivate
```
(activate again with `workon evaluation`)

To delete the environment:
```shell
rmvirtualenv evaluation
```

## Tab completion (UNIX / Bash)
Unfortunately, tab command completion with the [argcomplete](https://github.com/kislyuk/argcomplete) might not work immediately in a virtual environment. You might need to install argcomplete outside of your virtualenv and run `activate-global-python-argcomplete` to make it work globally on your machine.
