#!/bin/bash

# source: https://pythonhosted.org/CodeChat/.travis.yml.html

if [ "$TRAVIS_OS_NAME" == "osx" ]; then
    brew update
    brew install openssl readline
    brew outdated pyenv || brew upgrade pyenv

    brew install pyenv-virtualenv
    eval "$(pyenv init -)"
    eval "$(pyenv virtualenv-init -)"
    pyenv install $PYTHON

    export PYENV_VERSION=$PYTHON
    export PATH="/Users/travis/.pyenv/shims:${PATH}"
    pyenv virtualenv venv
    pyenv activate venv
fi
