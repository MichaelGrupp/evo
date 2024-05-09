#!/bin/bash

set -e

if [ "$(git branch --show-current)" != "master" ]; then
    echo "Not on master branch"
    exit 1
fi

git diff --quiet || { echo "Unstaged changes"; exit 1; }
git diff --quiet --cached || { echo "Uncommitted staged changes"; exit 1; }

if [ -n "$(git fetch --dry-run)" ]; then
    echo "Branch is not up to date"
    exit 1
fi

PREVIOUS_VERSION="$(git describe --tags --abbrev=0)"
echo "Current version: $PREVIOUS_VERSION"
read -p "Enter new version: " NEW_VERSION
read -p "Enter tag message: " TAG_MESSAGE

hatch version "$NEW_VERSION"

git commit -aem "Bump version to $NEW_VERSION"
git tag -a "$NEW_VERSION" -m "Release $NEW_VERSION: $TAG_MESSAGE"
git push
git push --tags

hatch build
hatch publish
