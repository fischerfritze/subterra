#!/bin/bash
set -e

# The Laravel backend mounts the job's work directory at /subterra/work.
# Structure: /subterra/work/parameter.json
#            /subterra/work/parameter_si.json
#            /subterra/work/temp/        (mesh output)
#            /subterra/work/results/     (simulation output)
#
# Create symlinks so the Python code's paths.py can find everything:
#   params/ -> /subterra/work
#   results/ -> /subterra/work/results

WORK_DIR="/subterra/work"

if [ -d "$WORK_DIR" ]; then
    # Symlink params directory
    rm -rf /subterra/params
    ln -sf "$WORK_DIR" /subterra/params

    # Symlink results directory
    mkdir -p "$WORK_DIR/results"
    rm -rf /subterra/results
    ln -sf "$WORK_DIR/results" /subterra/results

    # Ensure temp directory exists
    mkdir -p "$WORK_DIR/temp"
fi

exec "$@"
