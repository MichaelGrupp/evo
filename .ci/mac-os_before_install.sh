#!/bin/bash

# source: https://pythonhosted.org/CodeChat/.travis.yml.html

if [ "$TRAVIS_OS_NAME" == "osx" ]; then
  brew update
  brew install openssl readline
  brew outdated pyenv || brew upgrade pyenv

  # As recommended by Homebrew's "keg-only" warning.
  export LDFLAGS="-L /usr/local/opt/readline/lib"
  export CPPFLAGS="-I /usr/local/opt/readline/include"
  export PKG_CONFIG_PATH="/usr/local/opt/readline/lib/pkgconfig"

  brew install pyenv-virtualenv
  eval "$(pyenv init -)"
  eval "$(pyenv virtualenv-init -)"  
  pyenv install $PYTHON

  export PYENV_VERSION=$PYTHON
  export PATH="/Users/travis/.pyenv/shims:${PATH}"
  pyenv virtualenv venv
  pyenv activate venv
fi
