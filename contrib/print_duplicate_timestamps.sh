#!/bin/bash

set -e

usage="
Print lines with duplicate timestamps in TUM or EuRoC trajectory files.\n\n
Usage: ./print_duplicates.sh TRAJECTORY
"

if [ "$#" -ne 1 ]; then
    echo -e $usage
    exit 1
fi


cut -d" " -f 1 $1 | uniq -D
