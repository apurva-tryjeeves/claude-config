#!/usr/bin/env bash
# Kept for in-flight sessions: runs `python3 -m jaidev_watch watch <state-file>`; a legacy interval argument is dropped.
STATE=$1; shift; [[ ${1:-} =~ ^[0-9]+$ ]] && shift
PYTHONPATH="$(cd "$(dirname "$0")" && pwd)${PYTHONPATH:+:$PYTHONPATH}" exec python3 -m jaidev_watch watch "$STATE" "$@"
