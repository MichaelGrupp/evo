# always run in script directory
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
cd "$parent_path"

pip install . --upgrade --no-binary evo
# or use when developing: python setup.py develop
