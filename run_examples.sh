#!/usr/bin/env sh

# Takes a path argument and returns it as an absolute path. 
# No-op if the path is already absolute.
function abspath {
    local target="$1"

    if [ "$target" == "." ]; then
        echo "$(pwd)"
    elif [ "$target" == ".." ]; then
        echo "$(dirname "$(pwd)")"
    else
        echo "$(cd "$(dirname "$1")"; pwd)/$(basename "$1")"
    fi
}
function prepare_launcher {
    python3 -m venv .
    source bin/activate
    python3 -m pip install $SOURCE_DIR
    echo "Exonum launcher env prepared"
}

function compile_proto {
    python3 -m exonum-launcher \
        compile \
        -e $EXONUM_DIR \
        -s $1 \
        -o proto
}

function compile_protos {
    compile_proto cryptocurrency:$EXONUM_DIR/examples/cryptocurrency-advanced/backend/src/proto/
    compile_proto timestamping:$EXONUM_DIR/examples/timestamping/backend/src/proto/
    compile_proto time:$EXONUM_DIR/services/time/src/proto/
}

function run_exonum_config {
    python -m exonum-launcher \
        run \
        -i $1 \
        -p proto
}

EXONUM_DIR=${VARIABLE:=../../exonum}
EXONUM_DIR=$(abspath $EXONUM_DIR)

TARGET_DIR=$(abspath $PWD)/target
SOURCE_DIR=$(abspath $(dirname $0))

mkdir -p $TARGET_DIR
cd $TARGET_DIR

prepare_launcher
case "$1" in
    'timestamping')
        compile_protos
        echo "Starting timestamping..."
        run_exonum_config $SOURCE_DIR/samples/timestamping.yml
    ;;
    'cryptocurrency')
        compile_protos
        echo "Starting cryptocurrency..."
        run_exonum_config $SOURCE_DIR/samples/cryptocurrency-advanced.yml
    ;;
esac