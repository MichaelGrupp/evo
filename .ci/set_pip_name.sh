#!/bin/bash

export pip="pip"

if [ "$TRAVIS_OS_NAME" == "osx" ]; then
  if [ "$PYTHON"=="2.7.10" ]; then
    export pip="pip2"
  else
    export pip="pip3"
  fi
fi
