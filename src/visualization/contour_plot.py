from os import makedirs, path
from typing import Optional, Tuple

import matplotlib.pyplot as plt
from h5py import File
from matplotlib.tri import Triangulation
from numpy import arange

from src.simulation.utils.paths import (BASE_DIR, PARAMETER_FILE,
                                        PARAMETER_FILE_SI, PARAMS_DIR,
                                        RESULTS_DIR, TEMP_DIR)


def plot(
    h5_path: str = "results/7EWS_κ = 2.0_630720000.0years/sim_20years.h5",
    out_dir: str = "results/plots_svg",
    pattern: str = "T_vertex_",        
    save_svg: bool = True,              # True: .svg, False: .png
    dpi: int = 200,

    # >>> new Parameter for contour (in °C)
    vmin_c: float = 5.0,
    vmax_c: float = 25.0,
    step_c: float = 1.0,

    # >>> new parameter for axis
    x_range: Optional[Tuple[float, float]] = None,   # z.B. (0.0, 50.0)
    y_range: Optional[Tuple[float, float]] = None,   # z.B. (0.0, 30.0)

    # optic
    cmap: str = "cividis",
    line_color: str = "k",
    line_width: float = 0.4,
    line_alpha: float = 0.7,
    label_fontsize: int = 7,
):
    """
    Generate 2D contour plots from all snapshots in an HDF5 file.

    - Color scale in °C can be fixed via vmin_c/vmax_c/step_c (for both lines & filled contours).
    - x_range/y_range set the visible axis limits (None = automatic).
    - Saves files as .svg (default) or .png.

    Returns: list of generated file paths.
    """
    # validation
    if vmax_c <= vmin_c:
        raise ValueError("vmax_c muss > vmin_c sein.")
    if step_c <= 0:
        raise ValueError("step_c muss > 0 sein.")

    makedirs(out_dir, exist_ok=True)

    # find snapshots
    with File(h5_path, "r") as h5:
        if "snapshots" not in h5:
            raise FileNotFoundError(f"Keine 'snapshots'-Gruppe in {h5_path}")
        all_snaps = [k for k in h5["snapshots"].keys() if pattern in k]
    if not all_snaps:
        raise FileNotFoundError(
            f"Keine Snapshots mit pattern '{pattern}' gefunden.")
    all_snaps.sort()

    # fixed levels (°C) 
    levels_c = arange(vmin_c, vmax_c + step_c, step_c)
    print(
        f"Farbskala: {vmin_c:.1f}–{vmax_c:.1f} °C in {step_c:.1f}°C-Schritten (Levels={len(levels_c)})")

    saved = []
    for snap in all_snaps:
        with File(h5_path, "r") as h5:
            g = h5[f"snapshots/{snap}"]
            kind = g.attrs.get("kind", "vertex")
            title = g.attrs.get("time_label", snap)

            if kind == "vertex":
                coords = g["coords"][...]
                cells = g["cells"][...] if "cells" in g else None
                values = g["values"][...] - 273.15  # K → °C
                x, y = coords[:, 0], coords[:, 1]
            elif kind == "dof":
                coords = g["dof_coords"][...]
                x, y = coords[:, 0], coords[:, 1]
                cells = None
                values = g["dof_values"][...] - 273.15
            else:
                raise ValueError(f"Unbekannter Snapshot-Typ: {kind}")

        triang = Triangulation(
            x, y, cells) if cells is not None else Triangulation(x, y)

        plt.figure(figsize=(7, 5))
    # filled contours
        cf = plt.tricontourf(
            triang,
            values,
            levels=levels_c,
            vmin=vmin_c,
            vmax=vmax_c,
            cmap=cmap,
            extend="both"
        )
    # contour lines
        cl = plt.tricontour(
            triang,
            values,
            levels=levels_c,
            colors=line_color,
            linewidths=line_width,
            alpha=line_alpha
        )
        plt.clabel(cl, inline=True, fontsize=label_fontsize, fmt="%.0f°C")

    # axes
        if x_range is not None:
            plt.xlim(*x_range)
        if y_range is not None:
            plt.ylim(*y_range)

        plt.colorbar(cf, label="Temperature (°C)")
        plt.xlabel("x (m)")
        plt.ylabel("y (m)")
        plt.title(f"{title} — Temperaturfeld")
        plt.tight_layout()

        # save
        ext = "svg" if save_svg else "png"
        out_path = path.join(out_dir, f"{snap}.{ext}")
        plt.savefig(out_path, format=ext, dpi=dpi, bbox_inches="tight")
        plt.close()
        saved.append(out_path)
        print(f"--> Gespeichert: {out_path}")

    print(f"\nAlle Plots in '{out_dir}' gespeichert.")
    return saved
