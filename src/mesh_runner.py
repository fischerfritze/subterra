"""
mesh_runner.py — Standalone mesh generation program.

Reads parameter.json, converts to SI, generates mesh + locations,
and saves everything to params/temp/.

Usage:
    python -m src.mesh_runner
    python -m src.mesh_runner --params path/to/parameter.json
"""

import argparse
import json
import os
import traceback

from box import Box

from src.simulation import mesh as msh
from src.simulation.utils.convert_to_si import run_conversion
from src.simulation.utils.paths import PARAMETER_FILE, PARAMETER_FILE_SI


def run_mesh_generation(parameter_file: str = PARAMETER_FILE,
                        parameter_file_si: str = None):
    """Run SI conversion and mesh generation.
    
    Args:
        parameter_file: Path to the input parameter.json.
        parameter_file_si: Path to write the SI-converted parameters.
                           Defaults to parameter_si.json next to parameter_file.
    
    Returns:
        list of [x, y] borehole locations.
    """
    # Derive SI file path from parameter file location if not specified
    if parameter_file_si is None:
        param_dir = os.path.dirname(os.path.abspath(parameter_file))
        parameter_file_si = os.path.join(param_dir, 'parameter_si.json')

    # Override module-level paths so mesh.py uses the correct locations
    param_dir = os.path.dirname(os.path.abspath(parameter_file))
    temp_dir = os.path.join(param_dir, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    # Patch paths in mesh module for this run
    import src.simulation.utils.paths as paths_mod
    paths_mod.PARAMETER_FILE_SI = parameter_file_si
    paths_mod.TEMP_DIR = temp_dir
    msh.LOCATIONS_FILE = os.path.join(temp_dir, 'locations.json')

    # Step 1: SI-conversion
    try:
        run_conversion(parameter_file, parameter_file_si)
        print(f"SI-Konvertierung erfolgreich: {parameter_file_si}")
    except Exception as e:
        print(f"Fehler bei der SI-Konvertierung: {e}")
        traceback.print_exc()
        raise

    # Step 2: Load SI parameters
    with open(parameter_file_si, "r") as f:
        params_si = Box(json.load(f))

    # Step 3: Generate mesh + save locations
    locations = msh.generate_mesh(
        mode=tuple(params_si.meshMode),
        x_0=params_si.mesh.xCenter.value,
        y_0=params_si.mesh.yCenter.value,
        distance=params_si.mesh.boreholeDistance.value
    )

    print(f"Mesh generation complete. {len(locations)} boreholes generated.")
    return locations


def main():
    parser = argparse.ArgumentParser(
        description="SubTerra Mesh Generator — generates mesh and saves to params/temp/"
    )
    parser.add_argument(
        "--params",
        type=str,
        default=PARAMETER_FILE,
        help=f"Path to parameter.json (default: {PARAMETER_FILE})"
    )
    args = parser.parse_args()

    run_mesh_generation(parameter_file=args.params)


if __name__ == "__main__":
    main()
