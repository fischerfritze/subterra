"""
mesh_plot_runner.py — Generate a PNG visualization of a gmsh mesh.

Reads the temp_mesh.msh file produced by mesh generation and creates
a mesh_plot.png image next to it in the temp directory.

Usage:
    python -m src.mesh_plot_runner --params path/to/parameter.json
"""

import argparse
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def generate_mesh_plot(param_dir: str):
    """Read temp_mesh.msh via gmsh API and render it as a PNG.

    Args:
        param_dir: Directory containing params (with temp/ subdirectory
                   that holds temp_mesh.msh).
    """
    temp_dir = os.path.join(param_dir, 'temp')
    msh_file = os.path.join(temp_dir, 'temp_mesh.msh')
    out_file = os.path.join(temp_dir, 'mesh_plot.png')

    if not os.path.isfile(msh_file):
        print(f"Mesh-Datei nicht gefunden: {msh_file}")
        return None

    print(f"Lese Mesh: {msh_file}")

    # Use gmsh API to extract node coordinates and triangle connectivity
    import gmsh

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)  # suppress output
    gmsh.open(msh_file)

    # Get all 2D element types (triangles = type 2)
    node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
    # node_coords is [x1,y1,z1, x2,y2,z2, ...]
    coords = np.array(node_coords).reshape(-1, 3)
    # Build tag-to-index map
    tag_to_idx = {int(t): i for i, t in enumerate(node_tags)}

    # Get triangles (element type 2)
    elem_types, elem_tags, elem_node_tags = gmsh.model.mesh.getElements(dim=2)

    triangles = []
    for etype, enodes in zip(elem_types, elem_node_tags):
        if etype == 2:  # 3-node triangle
            nodes = np.array(enodes, dtype=int).reshape(-1, 3)
            for tri in nodes:
                triangles.append([tag_to_idx[t] for t in tri])

    gmsh.finalize()

    if not triangles:
        print("Keine Dreiecke im Mesh gefunden.")
        return None

    triangles = np.array(triangles)
    x = coords[:, 0]
    y = coords[:, 1]

    # Load locations.json for BHE positions (if available)
    loc_file = os.path.join(temp_dir, 'locations.json')
    bhe_locations = None
    if os.path.isfile(loc_file):
        with open(loc_file, 'r') as f:
            bhe_locations = json.load(f)

    # Plot
    fig, ax = plt.subplots(1, 1, figsize=(10, 8), dpi=150)
    ax.triplot(x, y, triangles, linewidth=0.3, color='#4a90d9', alpha=0.7)

    if bhe_locations:
        bhe_x = [loc[0] for loc in bhe_locations]
        bhe_y = [loc[1] for loc in bhe_locations]
        ax.scatter(bhe_x, bhe_y, c='#e74c3c', s=30, zorder=5, label='BHE',
                   edgecolors='darkred', linewidths=0.5)
        ax.legend(fontsize=9, loc='upper right')

    ax.set_xlabel('x [m]', fontsize=11)
    ax.set_ylabel('y [m]', fontsize=11)
    ax.set_title('Mesh Visualisierung', fontsize=13, fontweight='bold')
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.2)
    fig.tight_layout()

    fig.savefig(out_file, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)

    print(f"Mesh-Plot gespeichert: {out_file}")
    print(f"  Knoten: {len(x)}")
    print(f"  Dreiecke: {len(triangles)}")
    return out_file


def main():
    parser = argparse.ArgumentParser(description='Generate mesh visualization')
    parser.add_argument('--params', type=str, required=True,
                        help='Path to parameter.json')
    args = parser.parse_args()

    param_dir = os.path.dirname(os.path.abspath(args.params))
    generate_mesh_plot(param_dir)


if __name__ == '__main__':
    main()
