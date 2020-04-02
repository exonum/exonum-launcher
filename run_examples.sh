#!/usr/bin/env bash

# Takes a path argument and returns it as an absolute path.
# No-op if the path is already absolute.
function abspath {
    local target="$1"

    if [[ "$target" == "." ]]; then
        echo "$(pwd)"
    elif [[ "$target" == ".." ]]; then
        echo "$(dirname "$(pwd)")"
    else
        echo "$(cd "$(dirname "$1")"; pwd)/$(basename "$1")"
    fi
}
function prepare_launcher {
    python3 -m venv .
    source bin/activate
    python3 -m pip install ${SOURCE_DIR}
    echo "Exonum launcher env prepared"
}

function run_exonum_config {
    python -m exonum-launcher \
        -i $1
}

TARGET_DIR=$(abspath $PWD)/target
SOURCE_DIR=$(abspath $(dirname $0))

mkdir -p ${TARGET_DIR}
cd ${TARGET_DIR}

prepare_launcher
case "$1" in
    'timestamping')
        echo "Starting timestamping..."
        run_exonum_config ${SOURCE_DIR}/samples/timestamping.yml
    ;;
    'cryptocurrency')
        echo "Starting cryptocurrency..."
        run_exonum_config ${SOURCE_DIR}/samples/cryptocurrency-advanced.yml
    ;;
esac
