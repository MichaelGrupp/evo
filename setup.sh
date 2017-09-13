#!/bin/bash
# author: Michael Grupp

usage="\nUsage: [sudo -H] $0"
usage="$usage\n\t[--python2] [--python3] \t use an explicit Python version"
usage="$usage\n\t[--upgrade] [--uninstall] \t setup mode (default: install)"
usage="$usage\n\t[--with_jupyter] \t\t include Jupyter notebook dependencies"
usage="$usage\n\t[--show] \t\t\t search existing installation and exit"
usage="$usage\n\t[-h | --help] \t\t\t show help and exit"

if [[ $* == *--help ]] || [[ $* == *-h ]]; then
    echo -e "\nevo/setup.sh\n"
    echo "Sets up the evo Python package and its dependencies via pip."
    echo "WARNING: you might want to use a virtual environment, see README.md"
    echo -e $usage
    exit 0
fi

function log { echo -e "[$BASH_SOURCE] INFO $1"; }
function loge { echo -e "[$BASH_SOURCE] INFO $1"; }
function logne { echo -ne "[$BASH_SOURCE] INFO $1"; }
function error { echo -e "[$BASH_SOURCE] ERROR $1"; echo -e $usage; exit 1; }


if [[ $* == *--python2* ]]; then
    logne "using Python 2: "
    py=python2
elif [[ $* == *--python3* ]]; then
    logne "using Python 3: "
    py=python3
else
    logne "using default Python: "
    py=python
fi
$py --version
retcode=$?; if [ $retcode != 0 ]; then
    error "$py doesn't exist"
fi

if [[ $* == *--show* ]]; then
    logne "looking for a current installation for "; $py --version
    $py -m pip show --verbose evo
    retcode=$?; if [ $retcode != 0 ]; then error "found nothing"; exit 1; fi
    exit 0
fi
if [[ $* == *--uninstall* ]]; then
    log "uninstalling evo..."
    $py -m pip uninstall evo
    retcode=$?; if [ $retcode != 0 ]; then
        error "during uninstalling - maybe forgot 'sudo -H' or '--pythonX'?"
    fi
    exit 0
fi

log "starting setup of evo and its dependencies"
echo "enter 'y' to go on, any other key to exit"
read input
if [[ $input != y ]]; then
    exit 0
fi

pip --version
retcode=$?; if [ $retcode != 0 ]; then
    log "pip doesn't exist, installing..."
    log "downloading get-pip.py"
    curl -O https://bootstrap.pypa.io/get-pip.py
    log "installing pip"
    $py get-pip.py
    rm get-pip.py
fi

here="$(dirname "$0")"

if [[ $* == *--upgrade* ]]; then
    log "upgrading evo"
    $py -m pip install --upgrade --retries 1 $here
    retcode=$?; if [ $retcode != 0 ]; then
        error "during upgrade - maybe forgot 'sudo -H' or '--pythonX'?"
    fi
    if [[ $* == *--with_jupyter* ]]; then $py -m pip install --upgrade --retries 1 jupyter; fi
else
    log "installing evo"
    $py -m pip install $here
    retcode=$?; if [ $retcode != 0 ]; then
        error "error during installation - maybe forgot 'sudo -H' or '--pythonX'?"
    fi
    if [[ $* == *--with_jupyter* ]]; then $py -m pip install jupyter; fi
fi
if [[ $* == *--with_jupyter* ]]; then
    jupyter nbextension enable --py --sys-prefix widgetsnbextension
fi

logne ""; activate-global-python-argcomplete
log "argcomplete will be working in a new shell"

echo ""; loge "finished setup - package summary:\n"
$py -m pip show --verbose evo
