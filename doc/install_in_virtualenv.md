Infos on virtual environments: https://www.dabapps.com/blog/introduction-to-pip-and-virtualenv-python/

### virtualenv setup

Install `pip`:

```shell
curl -O https://bootstrap.pypa.io/get-pip.py
sudo python get-pip.py
rm get-pip.py
```

Install `virtualenv` and `virtualenvwrapper`:
```shell
sudo pip install virtualenv
sudo pip install virtualenvwrapper
```

Add setup code for `virtualenvwrapper` to shell startup file:
```shell
echo "export WORKON_HOME=$HOME/.virtualenvs && source /usr/local/bin/virtualenvwrapper.sh" >> ~/.bashrc
source ~/.bashrc
```

### Using a virtualenv for evo

```shell
mkvirtualenv evaluation
```
Now, the package should be installed in the virtualenv and you can use it.

To activate the environment, type:
```shell
workon evaluation
```

Install evo and its dependencies inside the virtual environment:
```shell
pip install evo --upgrade

# or alternatively from source:
cd <evo>  # go to evo base source folder with setup.py
pip install . --upgrade
```

**Important**: if you want to use ROS bagfiles in the virtual environment, run this too:
```
pip install catkin_pkg rospkg pyyaml
``` 
For some reason these packages are not found in a virtual environment even if you have a proper ROS installation (see [ROS forums](https://answers.ros.org/question/85211/importerror-no-module-named-rospkg-on-hydro-solved/?answer=85331#post-id-85331))

Check if evo is installed correctly by running:
```
evo
```

To leave the virtualenv, close the shell or type:
```shell
deactivate
```

To delete the environment:
```shell
rmvirtualenv evaluation
```

## Tab completion (UNIX / Bash)
Unfortunately, tab command completion with the [argcomplete](https://github.com/kislyuk/argcomplete) might not work immediately in a virtual environment. You might need to install argcomplete outside of your virtualenv and run `activate-global-python-argcomplete` to make it work globally on your machine.
