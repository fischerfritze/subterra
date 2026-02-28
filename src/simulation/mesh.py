"""
mesh.py — Mesh generation using the gmsh Python API.

Generates 2D triangular meshes for BTES simulations with borehole heat
exchangers (BHE).  Output is a native gmsh .msh file that can be read
directly by DOLFINx via ``dolfinx.io.gmshio``.

Physical groups written into the .msh:
    "Boundary" (dim 1, tag 1)  — outer rectangle edges
    "Ground"   (dim 2, tag 1)  — the 2D domain surface
"""

import math
import json
import os

import gmsh
import numpy as np

import src.simulation.utils.paths as _paths


# ---------------------------------------------------------------------------
# Path helpers (support runtime patching from mesh_runner / sim_runner)
# ---------------------------------------------------------------------------

def _temp_dir():
    """Return current TEMP_DIR (supports runtime patching)."""
    return _paths.TEMP_DIR


def _locations_file():
    """Return current locations file path."""
    return os.path.join(_temp_dir(), "locations.json")


# Keep module-level LOCATIONS_FILE for backward compat / direct patching
LOCATIONS_FILE = None  # set dynamically


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_mesh(mode, x_0, y_0, distance):
    """Generate mesh and save locations to JSON.

    Args:
        mode:     Tuple (layout_type, rings), e.g. ("hexa", 3).
        x_0:      x-coordinate of BHE field centre.
        y_0:      y-coordinate of BHE field centre.
        distance: BHE spacing in metres.

    Returns:
        list of [x, y] coordinate pairs (serialisable).
    """
    print("--------------------------------------------------------------------")
    if mode[0] == 'hexa':
        locations, EWS_dict = generate_hexa_ews(
            x_b0=x_0, y_b0=y_0, d=distance, rings=mode[1])
    elif mode[0] == 'square':
        locations, EWS_dict = generate_square_ews(
            x_b0=x_0, y_b0=y_0, d=distance, rings=mode[1])
    else:
        raise ValueError(f"Unknown mode: {mode}")

    meshing(EWS_dict)
    save_locations(locations)
    return locations


# ---------------------------------------------------------------------------
# Locations I/O
# ---------------------------------------------------------------------------

def save_locations(locations):
    """Save borehole locations to JSON file in temp directory."""
    loc_file = LOCATIONS_FILE or _locations_file()
    temp_dir = os.path.dirname(loc_file)
    os.makedirs(temp_dir, exist_ok=True)
    with open(loc_file, "w") as f:
        json.dump(locations, f, indent=2)
    print(f"Locations saved to {loc_file}")


def load_locations():
    """Load borehole locations from JSON file.

    Returns:
        list of [x, y] coordinate pairs.
    """
    loc_file = LOCATIONS_FILE or _locations_file()
    if not os.path.exists(loc_file):
        raise FileNotFoundError(
            f"Locations file not found: {loc_file}. "
            "Run mesh generation first."
        )
    with open(loc_file, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# BHE layout generators  (unchanged logic)
# ---------------------------------------------------------------------------

def generate_hexa_ews(x_b0, y_b0, d, rings):
    """Generate hexagonal BHE layout."""
    locations = []
    hexa_EWS = {}

    grid = {}
    index = 1
    for q in range(-rings, rings + 1):
        for r in range(-rings, rings + 1):
            s = -q - r
            if abs(s) <= rings:
                x = x_b0 + d * (q + r / 2)
                y = y_b0 + d * math.sqrt(3) / 2 * r
                grid[f"BH{index:02d}"] = (x, y)
                index += 1

    index = 1
    for _, (x, y) in grid.items():
        dist = math.sqrt((x - x_b0) ** 2 + (y - y_b0) ** 2)
        if dist <= rings * d:
            hexa_EWS[f"BH{index:02d}"] = (x, y)
            locations.append([x, y])
            index += 1

    return locations, hexa_EWS


def generate_square_ews(x_b0, y_b0, d, rings):
    """Generate square BHE layout."""
    locations = []
    square_EWS = {}

    index = 1
    for i in range(-rings, rings + 1):
        for j in range(-rings, rings + 1):
            x = x_b0 + i * d
            y = y_b0 + j * d
            dist = max(abs(i), abs(j))
            if dist <= rings:
                square_EWS[f"BH{index:02d}"] = (x, y)
                locations.append([x, y])
                index += 1

    return locations, square_EWS


# ---------------------------------------------------------------------------
# Gmsh-based meshing  (replaces .geo template + subprocess + dolfin-convert)
# ---------------------------------------------------------------------------

def meshing(EWS_dict):
    """Create a 2D triangle mesh with gmsh Python API and save as .msh.

    The mesh contains:
      - A rectangular domain [-x_len, x_len] x [-y_len, y_len]
      - Distance-based refinement around the BHE points
      - Physical groups "Boundary" (1D) and "Ground" (2D)

    Output: ``<TEMP_DIR>/temp_mesh.msh``  (gmsh format 4.1)
    """
    from box import Box

    with open(_paths.PARAMETER_FILE_SI, "r") as f:
        param = Box(json.load(f))

    ms      = param.mesh.meshFactor.value
    ms_fine = param.mesh.meshFine.value
    x_len   = param.mesh.xLength.value / 2
    y_len   = param.mesh.yLength.value / 2
    x_0     = param.mesh.xCenter.value
    y_0     = param.mesh.yCenter.value

    temp_dir = _temp_dir()
    os.makedirs(temp_dir, exist_ok=True)
    msh_file = os.path.join(temp_dir, "temp_mesh.msh")

    # ------------------------------------------------------------------
    # Initialise gmsh
    # ------------------------------------------------------------------
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)
    gmsh.model.add("subterra")
    factory = gmsh.model.occ  # OpenCASCADE kernel

    # ------------------------------------------------------------------
    # Geometry: rectangular domain
    # ------------------------------------------------------------------
    p1 = factory.addPoint(-x_len, -y_len, 0, ms)
    p2 = factory.addPoint( x_len, -y_len, 0, ms)
    p3 = factory.addPoint( x_len,  y_len, 0, ms)
    p4 = factory.addPoint(-x_len,  y_len, 0, ms)

    l1 = factory.addLine(p1, p2)
    l2 = factory.addLine(p2, p3)
    l3 = factory.addLine(p3, p4)
    l4 = factory.addLine(p4, p1)

    loop = factory.addCurveLoop([l1, l2, l3, l4])
    surf = factory.addPlaneSurface([loop])

    # Embed BHE points into the surface (needed for point-refinement)
    bhe_point_tags = []
    for _, (bx, by) in EWS_dict.items():
        pt = factory.addPoint(bx, by, 0, ms_fine)
        bhe_point_tags.append(pt)

    factory.synchronize()

    # Embed points so they become mesh vertices
    if bhe_point_tags:
        gmsh.model.mesh.embed(0, bhe_point_tags, 2, surf)

    # ------------------------------------------------------------------
    # Physical groups
    # ------------------------------------------------------------------
    gmsh.model.addPhysicalGroup(1, [l1, l2, l3, l4], tag=1, name="Boundary")
    gmsh.model.addPhysicalGroup(2, [surf], tag=1, name="Ground")

    # ------------------------------------------------------------------
    # Mesh size field: refine around BHE points
    # ------------------------------------------------------------------
    gmsh.model.mesh.field.add("Distance", 1)
    gmsh.model.mesh.field.setNumbers("Distance", 1, "PointsList", bhe_point_tags)

    gmsh.model.mesh.field.add("Threshold", 2)
    gmsh.model.mesh.field.setNumber("Threshold", 2, "InField", 1)
    gmsh.model.mesh.field.setNumber("Threshold", 2, "SizeMin", ms_fine)
    gmsh.model.mesh.field.setNumber("Threshold", 2, "SizeMax", ms)
    gmsh.model.mesh.field.setNumber("Threshold", 2, "DistMin", 0)
    gmsh.model.mesh.field.setNumber("Threshold", 2, "DistMax", 30)

    gmsh.model.mesh.field.setAsBackgroundMesh(2)

    # Override default sizing to let the background field take control
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)

    # ------------------------------------------------------------------
    # Generate 2D mesh and write
    # ------------------------------------------------------------------
    gmsh.model.mesh.generate(2)
    gmsh.write(msh_file)
    gmsh.finalize()

    print(f"Mesh successfully created: {msh_file}")
    print("--------------------------------------------------------------------")
