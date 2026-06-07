#!/usr/bin/env bash
set -eo pipefail

WORKSPACE="${HOME}/Desktop/planner"

source /opt/ros/noetic/setup.bash
source "${WORKSPACE}/devel/setup.bash"

echo "Starting planner demo with one roslaunch session..."
echo "RViz Fixed Frame is set to: map"

cd "${WORKSPACE}"
exec roslaunch map_tools start_navigation.launch
