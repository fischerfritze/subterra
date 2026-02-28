#!/bin/bash
set -e

# ─── SubTerra FEniCS Container Entrypoint ─────────────────────────────
#
# In production the backend mounts the shared jobs volume at /subterra/jobs
# and passes JOB_ID as an environment variable. The job directory structure:
#   /subterra/jobs/<JOB_ID>/parameter.json
#   /subterra/jobs/<JOB_ID>/parameter_si.json
#   /subterra/jobs/<JOB_ID>/temp/        (mesh output)
#   /subterra/jobs/<JOB_ID>/results/     (simulation output)
#
# For backwards-compat / manual runs, /subterra/work is also supported:
#   docker run --rm -v /path/to/job:/subterra/work subterra-fenics ...
#
# Symlinks are created so paths.py can find everything:
#   /subterra/params  -> <job_dir>
#   /subterra/results -> <job_dir>/results

# Determine the work directory
if [ -n "$JOB_ID" ] && [ -d "/subterra/jobs/$JOB_ID" ]; then
    WORK_DIR="/subterra/jobs/$JOB_ID"
elif [ -d "/subterra/work" ]; then
    WORK_DIR="/subterra/work"
else
    # No job directory found — just run the command (e.g. --help)
    exec "$@"
fi

# Symlink params directory
rm -rf /subterra/params
ln -sf "$WORK_DIR" /subterra/params

# Symlink results directory
mkdir -p "$WORK_DIR/results"
rm -rf /subterra/results
ln -sf "$WORK_DIR/results" /subterra/results

# Ensure temp directory exists
mkdir -p "$WORK_DIR/temp"

exec "$@"
