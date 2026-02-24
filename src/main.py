import argparse
from src.simulation import calculation
from src.visualization import contour_plot


def main():
    parser = argparse.ArgumentParser(description="SubTerra CLI")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # ---- run command ----
    subparsers.add_parser("run", help="Run simulation")

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

    if args.command == "run":
        calculation.run_calculation()

    elif args.command == "plot":
        contour_plot.plot(
            h5_path=args.h5_path,
            vmax_c=args.vmax_c
        )


if __name__ == "__main__":
    main()
