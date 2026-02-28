import argparse
from src.simulation import calculation
from src.visualization import contour_plot
from src.mesh_runner import run_mesh_generation
from src.sim_runner import run_simulation


def main():
    parser = argparse.ArgumentParser(description="SubTerra CLI")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # ---- mesh command (Phase 1: step 1) ----
    mesh_parser = subparsers.add_parser(
        "mesh", help="Generate mesh only (saves to params/temp/)")
    mesh_parser.add_argument(
        "--params",
        type=str,
        default=None,
        help="Path to parameter.json (default: params/parameter.json)"
    )

    # ---- simulate command (Phase 1: step 2) ----
    sim_parser = subparsers.add_parser(
        "simulate", help="Run simulation with pre-generated mesh")
    sim_parser.add_argument(
        "--params",
        type=str,
        default=None,
        help="Path to parameter.json (default: params/parameter.json)"
    )

    # ---- run command (legacy: mesh + simulation in one step) ----
    subparsers.add_parser("run", help="Run mesh generation + simulation (legacy)")

    # ---- plot command ----
    plot_parser = subparsers.add_parser("plot", help="Plot results")
    plot_parser.add_argument(
        "h5_path",
        type=str,
        help="Path to the .h5 result file"
    )
    plot_parser.add_argument(
        "--vmax_c",
        type=float,
        default=40.0,
        help="Maximum contour value (default: 40)"
    )

    args = parser.parse_args()

    if args.command == "mesh":
        kwargs = {}
        if args.params:
            kwargs["parameter_file"] = args.params
        run_mesh_generation(**kwargs)

    elif args.command == "simulate":
        kwargs = {}
        if args.params:
            kwargs["parameter_file"] = args.params
        run_simulation(**kwargs)

    elif args.command == "run":
        calculation.run_calculation()

    elif args.command == "plot":
        contour_plot.plot(
            h5_path=args.h5_path,
            vmax_c=args.vmax_c
        )


if __name__ == "__main__":
    main()
