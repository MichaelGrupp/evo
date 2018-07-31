#!/bin/bash

set -e

workdir=$1

source /opt/ros/$ROS_DISTRO/setup.sh
cd $workdir
pytest -sv
