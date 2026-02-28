"""
sim_runner.py — Standalone simulation program.

Loads a previously generated mesh from params/temp/ and runs the
FEniCS simulation. Requires mesh_runner.py to have been executed first.

Usage:
    python -m src.sim_runner
    python -m src.sim_runner --params path/to/parameter.json
"""

import argparse
import json
import os
import traceback

from box import Box

from src.simulation import calculation
from src.simulation.utils.convert_to_si import run_conversion
from src.simulation.utils.paths import PARAMETER_FILE, PARAMETER_FILE_SI


def run_simulation(parameter_file: str = PARAMETER_FILE,
                   parameter_file_si: str = None):
    """Run SI conversion (if needed) and FEniCS simulation.
    
    Expects mesh files and locations.json to already exist in temp/.
    
    Args:
        parameter_file: Path to the input parameter.json.
        parameter_file_si: Path to write/read the SI-converted parameters.
                           Defaults to parameter_si.json next to parameter_file.
    """
    # Derive paths from parameter file location
    param_dir = os.path.dirname(os.path.abspath(parameter_file))
    if parameter_file_si is None:
        parameter_file_si = os.path.join(param_dir, 'parameter_si.json')
    
    temp_dir = os.path.join(param_dir, 'temp')
    results_dir = os.path.join(param_dir, 'results')
    os.makedirs(results_dir, exist_ok=True)

    # Patch module-level paths for this run
    import src.simulation.utils.paths as paths_mod
    import src.simulation.mesh as msh
    paths_mod.PARAMETER_FILE = parameter_file
    paths_mod.PARAMETER_FILE_SI = parameter_file_si
    paths_mod.TEMP_DIR = temp_dir
    paths_mod.RESULTS_DIR = results_dir
    msh.LOCATIONS_FILE = os.path.join(temp_dir, 'locations.json')

    # Step 1: SI-conversion
    try:
        run_conversion(parameter_file, parameter_file_si)
        print(f"SI-Konvertierung erfolgreich: {parameter_file_si}")
    except Exception as e:
        print(f"Fehler bei der SI-Konvertierung: {e}")
        traceback.print_exc()
        raise

    # Step 2: Load parameters
    with open(parameter_file_si, "r") as f:
        params_si = Box(json.load(f))
    with open(parameter_file, "r") as f:
        params = Box(json.load(f))

    # Step 3: Run simulation (mesh must already exist)
    calculation.run_simulation(params, params_si)

    print("Simulation complete.")


def main():
    parser = argparse.ArgumentParser(
        description="SubTerra Simulation Runner — runs FEniCS simulation with pre-generated mesh"
    )
    parser.add_argument(
        "--params",
        type=str,
        default=PARAMETER_FILE,
        help=f"Path to parameter.json (default: {PARAMETER_FILE})"
    )
    args = parser.parse_args()

    run_simulation(parameter_file=args.params)


if __name__ == "__main__":
    main()
