#!/bin/bash

window_pattern="$1"
window_name="$2"

# Note: this could be simpler if there was a way to know the pid
# of the current subl window.
pids=$(xdotool search --class --onlyvisible "subl")

for pid in $pids; do
    name=$(xdotool getwindowname $pid)
    echo "found $pid : $name"
    if [[ $name == *"$window_pattern" ]]; then
        echo "renaming $pid : $name to $window_name"
        xdotool set_window --name "$window_name" "$pid"
    fi
done
