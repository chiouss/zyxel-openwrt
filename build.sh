#!/bin/sh
# Usage: ./build.sh <profile> [make args...]
set -e

[ -n "$1" ] || { echo "Usage: $0 <profile> [make args...]"; exit 1; }
profile=$1
shift

cd "$(dirname "$0")"
if [ -f openwrt/Makefile ]; then
	./setup.py --rebase
else
	./setup.py --setup
fi

cd openwrt
../scripts/gen_config.py "$profile"
make -j"$(nproc)" download
make -j"$(nproc)" "$@"
