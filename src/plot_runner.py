"""
plot_runner.py — Standalone plot generation program.

Finds HDF5 result files and generates contour plots as PNG images.
Can be run after a simulation completes.

Usage:
    python -m src.plot_runner --params path/to/parameter.json
    python -m src.plot_runner --h5 path/to/result.h5 --outdir path/to/plots
"""

import argparse
import glob
import json
import os
import traceback

from src.simulation.utils.paths import PARAMETER_FILE
from src.visualization.contour_plot import plot


def run_plot_generation(parameter_file: str = PARAMETER_FILE,
                        h5_path: str = None,
                        out_dir: str = None,
                        vmax_c: float = 40.0):
    """Generate contour plots from simulation results.

    If parameter_file is given, derives the results directory from it
    and finds all .h5 files automatically.

    If h5_path is given directly, uses that single file.

    Args:
        parameter_file: Path to parameter.json (to derive results dir).
        h5_path: Direct path to a single .h5 file (overrides param-based search).
        out_dir: Output directory for plots. Defaults to results/plots/ next to param file.
        vmax_c: Maximum contour temperature in °C.
    """
    param_dir = os.path.dirname(os.path.abspath(parameter_file))
    results_dir = os.path.join(param_dir, 'results')

    if out_dir is None:
        out_dir = os.path.join(results_dir, 'plots')
    os.makedirs(out_dir, exist_ok=True)

    # Collect .h5 files
    if h5_path:
        h5_files = [h5_path]
    else:
        h5_files = []
        # Search in results dir and one level of subdirectories
        for pattern in [
            os.path.join(results_dir, '*.h5'),
            os.path.join(results_dir, '*', '*.h5'),
        ]:
            h5_files.extend(glob.glob(pattern))

    if not h5_files:
        print(f"Keine .h5 Dateien gefunden in {results_dir}")
        return []

    h5_files = sorted(set(h5_files))
    print(f"Gefundene .h5 Dateien: {len(h5_files)}")

    all_saved = []
    for h5_file in h5_files:
        print(f"\nGeneriere Plots für: {h5_file}")
        try:
            saved = plot(
                h5_path=h5_file,
                out_dir=out_dir,
                save_svg=False,     # PNG for web display
                dpi=200,
                vmax_c=vmax_c,
            )
            all_saved.extend(saved)
        except Exception as e:
            print(f"Fehler bei {h5_file}: {e}")
            traceback.print_exc()

    print(f"\nInsgesamt {len(all_saved)} Plots generiert in {out_dir}")
    return all_saved


def main():
    parser = argparse.ArgumentParser(
        description="SubTerra Plot Runner — generates contour plots from simulation results"
    )
    parser.add_argument(
        "--params",
        type=str,
        default=PARAMETER_FILE,
        help=f"Path to parameter.json (default: {PARAMETER_FILE})"
    )
    parser.add_argument(
        "--h5",
        type=str,
        default=None,
        help="Direct path to a single .h5 file"
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default=None,
        help="Output directory for plot PNGs"
    )
    parser.add_argument(
        "--vmax_c",
        type=float,
        default=40.0,
        help="Maximum contour temperature in °C (default: 40)"
    )
    args = parser.parse_args()

    run_plot_generation(
        parameter_file=args.params,
        h5_path=args.h5,
        out_dir=args.outdir,
        vmax_c=args.vmax_c,
    )


if __name__ == "__main__":
    main()
