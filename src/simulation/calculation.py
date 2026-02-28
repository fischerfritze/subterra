"""
calculation.py — FEniCSx (DOLFINx) based BTES simulation.

Solves the transient heat-transport equation on a 2D domain using linear
Lagrange elements.  Borehole heat exchangers are modelled as regularised
Gaussian source terms (replacing the legacy ``fenics.PointSource``).

Mesh input: ``temp_mesh.msh`` (gmsh format, read via ``dolfinx.io.gmshio``).
"""

import json
import traceback
from os import makedirs, path

import numpy as np
from alive_progress import alive_bar
from box import Box
from psutil import cpu_percent, virtual_memory

# ── DOLFINx / UFL / PETSc imports ──
import dolfinx
import dolfinx.fem.petsc
import ufl
from dolfinx.io import gmshio
from mpi4py import MPI
from petsc4py import PETSc

from src.simulation import mesh as msh
from src.simulation import powerprofile as pp
from src.simulation.utils.h5py_writer import H5Writer
import src.simulation.utils.paths as _paths
from src.simulation.utils.tools import P_el_values, weighted_parameter
from src.simulation.utils.convert_to_si import run_conversion
import os as _os


# ---------------------------------------------------------------------------
# Progress helper (unchanged)
# ---------------------------------------------------------------------------

def _write_progress(phase, current, total, message=""):
    """Write progress.json into the params directory (= work dir)."""
    progress_file = _os.path.join(_paths.PARAMS_DIR, 'progress.json')
    pct = round(current / total * 100, 1) if total > 0 else 0
    data = {
        'phase': phase,
        'current_step': current,
        'total_steps': total,
        'percent': pct,
        'message': message,
    }
    try:
        tmp = progress_file + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(data, f)
        _os.replace(tmp, progress_file)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Legacy entry point (mesh + simulation in one call)
# ---------------------------------------------------------------------------

def run_calculation():
    """Legacy entry point: runs SI conversion, mesh generation, and simulation."""
    try:
        run_conversion(_paths.PARAMETER_FILE, _paths.PARAMETER_FILE_SI)
        print(f"SI-Konvertierung erfolgreich: {_paths.PARAMETER_FILE_SI}")
    except Exception as e:
        print(f"Fehler bei der SI-Konvertierung: {e}")
        traceback.print_exc()
        exit(1)

    with open(_paths.PARAMETER_FILE_SI, "r") as f:
        params_si = Box(json.load(f))
    with open(_paths.PARAMETER_FILE, "r") as f:
        params = Box(json.load(f))

    msh.generate_mesh(
        mode=tuple(params_si.meshMode),
        x_0=params_si.mesh.xCenter.value,
        y_0=params_si.mesh.yCenter.value,
        distance=params_si.mesh.boreholeDistance.value
    )

    return run_simulation(params, params_si)


# ---------------------------------------------------------------------------
# Public simulation entry
# ---------------------------------------------------------------------------

def run_simulation(params: Box = None, params_si: Box = None):
    """Run the DOLFINx simulation using a previously generated mesh.

    Loads mesh and borehole locations from params/temp/.
    If params / params_si are not provided, loads them from the default paths.
    """
    if params is None:
        with open(_paths.PARAMETER_FILE, "r") as f:
            params = Box(json.load(f))
    if params_si is None:
        if not path.exists(_paths.PARAMETER_FILE_SI):
            run_conversion(_paths.PARAMETER_FILE, _paths.PARAMETER_FILE_SI)
        with open(_paths.PARAMETER_FILE_SI, "r") as f:
            params_si = Box(json.load(f))

    return _run_simulation(params, params_si)


# ---------------------------------------------------------------------------
# Helper: build a Gaussian source function for all BHE locations
# ---------------------------------------------------------------------------

def _build_gaussian_source(V, locations_np, sigma):
    """Return a dolfinx.fem.Function representing the sum of normalised
    Gaussians centred at each borehole location.

    The amplitude is set to 1.0; the caller multiplies by *Q* each step.

    Parameters
    ----------
    V : dolfinx.fem.FunctionSpace
        Scalar CG1 space on the simulation mesh.
    locations_np : np.ndarray, shape (n_bhe, 2)
        BHE (x, y) positions.
    sigma : float
        Standard deviation of the Gaussian (≈ mesh fine size).
    """
    source = dolfinx.fem.Function(V)
    x = V.tabulate_dof_coordinates()[:, :2]  # (ndofs, 2)

    vals = np.zeros(x.shape[0], dtype=PETSc.ScalarType)
    two_sigma2 = 2.0 * sigma ** 2
    norm = 1.0 / (2.0 * np.pi * sigma ** 2)  # normalisation in 2D

    for loc in locations_np:
        r2 = (x[:, 0] - loc[0]) ** 2 + (x[:, 1] - loc[1]) ** 2
        vals += norm * np.exp(-r2 / two_sigma2)

    source.x.array[:] = vals
    return source


# ---------------------------------------------------------------------------
# Helper: evaluate T at a point
# ---------------------------------------------------------------------------

def _eval_at_point(mesh, T_func, point_2d):
    """Evaluate *T_func* at a single 2D point.  Returns float."""
    from dolfinx.geometry import bb_tree, compute_collisions_points, \
        compute_colliding_cells
    tree = bb_tree(mesh, mesh.topology.dim)
    pt3d = np.array([[point_2d[0], point_2d[1], 0.0]])
    cell_candidates = compute_collisions_points(tree, pt3d)
    cells = compute_colliding_cells(mesh, cell_candidates, pt3d)
    if len(cells.links(0)) == 0:
        return float('nan')
    return float(T_func.eval(pt3d, cells.links(0)[0])[0])


# Cached BoundingBoxTree for repeated evaluations within one time loop
_cached_tree = None


def _eval_at_points_batch(mesh, T_func, points_2d):
    """Evaluate *T_func* at multiple 2D points.  Returns 1D np array."""
    global _cached_tree
    from dolfinx.geometry import bb_tree, compute_collisions_points, \
        compute_colliding_cells

    if _cached_tree is None:
        _cached_tree = bb_tree(mesh, mesh.topology.dim)

    pts3d = np.column_stack([points_2d, np.zeros(len(points_2d))])
    results = np.empty(len(points_2d), dtype=np.float64)

    cell_candidates = compute_collisions_points(_cached_tree, pts3d)
    for i in range(len(points_2d)):
        try:
            cells_i = compute_colliding_cells(mesh, cell_candidates, pts3d[i:i+1])
            links = cells_i.links(0)
            if len(links) == 0:
                results[i] = float('nan')
            else:
                results[i] = T_func.eval(pts3d[i:i+1], links[0])[0]
        except RuntimeError:
            # GJK collision detection can fail for points near mesh boundaries
            results[i] = float('nan')

    return results


# ---------------------------------------------------------------------------
# Core simulation
# ---------------------------------------------------------------------------

def _run_simulation(params: Box, params_si: Box):
    """DOLFINx implementation of the transient heat-transport solver."""

    TEMP_MESH_PATH = path.join(_paths.TEMP_DIR, "temp_mesh.msh")
    folder_name = (
        f"{params_si.meshMode[0]}_{params_si.meshMode[1]}"
        f"_κ = {params_si.ground.thermalConductivity.value}"
        f"_{params_si.time.simulationYears.value}years"
    )
    base_folder = path.join(_paths.RESULTS_DIR, folder_name)
    makedirs(base_folder, exist_ok=True)

    print(f"Starting simulation with parameters from {_paths.PARAMETER_FILE_SI}")
    _write_progress('simulation', 0, 1, 'Simulation wird vorbereitet...')

    # ------------------------------------------------------------------
    # Load borehole locations
    # ------------------------------------------------------------------
    locations_raw = msh.load_locations()
    locations_np = np.array(locations_raw, dtype=np.float64)  # (n_bhe, 2)
    n_EWS = len(locations_raw)

    # ------------------------------------------------------------------
    # Power profile
    # ------------------------------------------------------------------
    powerprofile, eta, Q_out, Q_in = pp.multiple_powerprofile(
        A=params_si.power.coefficientA.value,
        B=params_si.power.coefficientB.value,
        years=params.time.simulationYears.value
    )

    # ------------------------------------------------------------------
    # Load mesh from .msh file
    # ------------------------------------------------------------------
    if not path.exists(TEMP_MESH_PATH):
        raise FileNotFoundError(
            f"Mesh file not found: {TEMP_MESH_PATH}. "
            "Run mesh generation first (python -m src.mesh_runner)."
        )

    mesh, cell_tags, facet_tags = gmshio.read_from_msh(
        TEMP_MESH_PATH, MPI.COMM_WORLD, gdim=2
    )

    #############################
    ### Create FEniCSx objects ##
    #############################

    # Scalar function space (CG1)
    V_space = dolfinx.fem.functionspace(mesh, ("Lagrange", 1))

    # ------------------------------------------------------------------
    # Boundary condition: T = T_0 on "Boundary" (Physical tag 1)
    # ------------------------------------------------------------------
    T_0 = PETSc.ScalarType(params_si.ground.temperature.value)

    boundary_facets = facet_tags.find(1)  # tag 1 = "Boundary"
    boundary_dofs = dolfinx.fem.locate_dofs_topological(
        V_space, mesh.topology.dim - 1, boundary_facets
    )
    bc = dolfinx.fem.dirichletbc(T_0, boundary_dofs, V_space)

    # ------------------------------------------------------------------
    # Initial condition: T = T_0 everywhere
    # ------------------------------------------------------------------
    T_n = dolfinx.fem.Function(V_space, name="T_n")
    T_n.x.array[:] = float(T_0)

    # Trial / test
    T_trial = ufl.TrialFunction(V_space)
    v_test = ufl.TestFunction(V_space)

    # Solution function
    T = dolfinx.fem.Function(V_space, name="T")

    # Normal vector (for boundary flux integrals)
    n_vector = ufl.FacetNormal(mesh)

    #########################
    ### Material parameters #
    #########################

    try:
        num_cells = mesh.topology.index_map(mesh.topology.dim).size_local
        max_distance = mesh.h(mesh.topology.dim, np.arange(
            num_cells, dtype=np.int32)).max()
        max_velocity = max(params_si.groundwater.velocityX.value,
                           params_si.groundwater.velocityY.value)

        if params_si.ground.porosity.value != 0.0:
            thermalConductivity, heatCapacityDensity = weighted_parameter(
                model=params_si.ground.modelType.value,
                ground_parameter=[
                    params_si.ground.thermalConductivity.value,
                    params_si.ground.heatCapacityDensity.value
                ],
                fluid_parameter=[
                    params_si.groundwater.thermalConductivity.value,
                    params_si.groundwater.density.value *
                    params_si.groundwater.specificHeat.value
                ],
                porosity=params_si.ground.porosity.value
            )
        else:
            thermalConductivity = params_si.ground.thermalConductivity.value
            heatCapacityDensity = params_si.ground.heatCapacityDensity.value

        # Diffusion coefficient: a = λ / (ρc)
        diffusionCoefficient = thermalConductivity / heatCapacityDensity
        dt = params_si.time.timeStepHours.value

        # ── Bilinear form ──
        # Mass + diffusion (always present)
        a_form = (
            T_trial * v_test * ufl.dx
            + dt * diffusionCoefficient
            * ufl.dot(ufl.grad(T_trial), ufl.grad(v_test)) * ufl.dx
        )

        if params_si.enableConvection is True:
            convCoeff = (
                params_si.ground.porosity.value
                * params_si.groundwater.density.value
                * params_si.groundwater.specificHeat.value
                / params_si.ground.heatCapacityDensity.value
            )
            v_vec = ufl.as_vector([
                dolfinx.fem.Constant(mesh, PETSc.ScalarType(
                    params_si.groundwater.velocityX.value)),
                dolfinx.fem.Constant(mesh, PETSc.ScalarType(
                    params_si.groundwater.velocityY.value)),
            ])
            a_form += dt * convCoeff * ufl.div(
                v_vec * T_trial) * v_test * ufl.dx

            peclet_number = max_velocity * max_distance / diffusionCoefficient
            if peclet_number > 2.0:
                raise RuntimeWarning(
                    f"peclet_number_max = {peclet_number:.2f}\n"
                    "Warning: calculation numerically unstable")
            print(f"peclet_number_max = {peclet_number:.2f}")

        else:
            neumann_number = diffusionCoefficient * dt / (max_distance ** 2)
            print(f"Ne_max = {neumann_number:.2f}")

    except ValueError as e:
        print(f"Value error:\n {e}")
        traceback.print_exc()
        exit(1)
    except RuntimeWarning as e:
        print(f"Numerical issue for ground parameters:\n {e}")
        traceback.print_exc()
        exit(1)
    except Exception as e:
        print(f"Unexpected exception:\n {e}")
        traceback.print_exc()
        exit(1)

    # ------------------------------------------------------------------
    # Gaussian source function for BHE point sources
    # ------------------------------------------------------------------
    sigma = float(params_si.mesh.meshFine.value) * 1.0  # ≈ mesh fine size
    source_shape = _build_gaussian_source(V_space, locations_np, sigma)

    # ------------------------------------------------------------------
    # Assemble LHS matrix (constant over time)
    # ------------------------------------------------------------------
    a_compiled = dolfinx.fem.form(a_form)
    A = dolfinx.fem.petsc.assemble_matrix(a_compiled, bcs=[bc])
    A.assemble()

    # ------------------------------------------------------------------
    # PETSc KSP solver (LU)
    # ------------------------------------------------------------------
    solver = PETSc.KSP().create(mesh.comm)
    solver.setOperators(A)
    solver.setType(PETSc.KSP.Type.PREONLY)
    pc = solver.getPC()
    pc.setType(PETSc.PC.Type.LU)

    # ------------------------------------------------------------------
    # Time loop
    # ------------------------------------------------------------------
    time_steps = int(params_si.time.simulationYears.value / dt)

    writer = H5Writer(
        path=f"{base_folder}/sim_{params.time.simulationYears.value}years.h5",
        n_EWS=n_EWS, compression="lzf", flush_every=365
    )

    # Reusable PETSc vector for RHS
    b_vec = dolfinx.fem.petsc.create_vector(dolfinx.fem.form(
        T_n * v_test * ufl.dx))

    with alive_bar(time_steps, title='SubTerra is running', bar='smooth') as bar:
        time_step = 1
        total_flux = 0.0
        E_probe_sum = 0.0
        last_progress_pct = -5

        while time_step <= time_steps:
            cpu = cpu_percent(interval=0.0)
            ram = virtual_memory().percent
            bar.text(f'(CPU: {cpu:.1f}%, RAM: {ram:.1f}%)')

            current_pct = int(time_step / time_steps * 100)
            if time_step == 1 or current_pct >= last_progress_pct + 5 or time_step == time_steps:
                _write_progress(
                    'simulation', time_step, time_steps,
                    f'Schritt {time_step}/{time_steps} — CPU: {cpu:.0f}%, RAM: {ram:.0f}%'
                )
                last_progress_pct = current_pct

            Q_dict = powerprofile.get(time_step)
            if not Q_dict:
                raise ValueError(
                    f"No powerprofile entry for time step {time_step}")

            Q = Q_dict * dt / heatCapacityDensity

            # ── Build RHS: M * T_n + dt * Q * source_shape ──
            # L = T_n * v_test * dx + Q * source_shape * v_test * dx
            L_form = dolfinx.fem.form(
                T_n * v_test * ufl.dx
                + dolfinx.fem.Constant(mesh, PETSc.ScalarType(Q))
                * source_shape * v_test * ufl.dx
            )

            with b_vec.localForm() as b_local:
                b_local.set(0.0)
            dolfinx.fem.petsc.assemble_vector(b_vec, L_form)
            dolfinx.fem.petsc.apply_lifting(b_vec, [a_compiled], bcs=[[bc]])
            b_vec.ghostUpdate(
                addv=PETSc.InsertMode.ADD_VALUES,
                mode=PETSc.ScatterMode.REVERSE)
            dolfinx.fem.petsc.set_bc(b_vec, [bc])

            # ── Solve ──
            solver.solve(b_vec, T.x.petsc_vec)
            T.x.scatter_forward()

            # ── Boundary flux ──
            flux_form = dolfinx.fem.form(
                -thermalConductivity
                * ufl.dot(ufl.grad(T), n_vector) * ufl.ds
            )
            flux_boundary = dolfinx.fem.assemble_scalar(flux_form)

            # ── Per-BHE temperature evaluation ──
            r_EWS = params_si.power.pipeRadius.value
            Temp_EWS_row = np.empty(n_EWS, dtype=np.float32)
            W_el_row = np.empty(n_EWS, dtype=np.float32)

            # Build array of 4 evaluation points per BHE
            eval_pts = []
            for i in range(n_EWS):
                x, y = locations_np[i]
                eval_pts.extend([
                    [x - r_EWS, y],
                    [x + r_EWS, y],
                    [x, y - r_EWS],
                    [x, y + r_EWS],
                ])
            eval_pts = np.array(eval_pts, dtype=np.float64)
            T_vals = _eval_at_points_batch(mesh, T, eval_pts)

            for i in range(n_EWS):
                T_EWS = float(np.nanmean(T_vals[4*i:4*i+4]))
                Temp_EWS_row[i] = T_EWS
                W_el_row[i] = P_el_values(
                    Q=Q_dict,
                    T=T_EWS,
                    T_H=params_si.temperatureHot.value,
                    delta_t=dt,
                    gamma=params_si.power.efficiency.value
                )

            # ── Energy balance ──
            E_T_n_form = dolfinx.fem.form(
                dolfinx.fem.Constant(mesh, PETSc.ScalarType(heatCapacityDensity))
                * T_n * ufl.dx
            )
            E_T_form = dolfinx.fem.form(
                dolfinx.fem.Constant(mesh, PETSc.ScalarType(heatCapacityDensity))
                * T * ufl.dx
            )
            E_ground_i = (
                dolfinx.fem.assemble_scalar(E_T_n_form)
                - dolfinx.fem.assemble_scalar(E_T_form)
            )
            E_flux_i = -dt * flux_boundary
            E_probe_i = dt * Q_dict * n_EWS
            error_i = E_ground_i + E_flux_i + E_probe_i

            # ── Save to HDF5 ──
            writer.append_step(
                day=time_step,
                error=error_i / (3600.0 * 1000.0),
                E_probe=E_probe_i / (3600.0 * 1000.0),
                E_flux=E_flux_i / (3600.0 * 1000.0),
                Delta_E=E_ground_i / (3600.0 * 1000.0),
                E_inout=(E_ground_i + E_probe_i) / (3600.0 * 1000.0),
                Q_probe=np.nan,
                E_storage=np.nan,
                W_el_row=W_el_row,
                Temp_EWS_row=Temp_EWS_row
            )

            # ── Update T_n for next time step ──
            T_n.x.array[:] = T.x.array[:]

            total_flux += E_flux_i
            E_probe_sum += E_probe_i

            # ── Snapshots ──
            if time_step in [365 * 1, 365 * 10, 365 * 20, 365 * 30, 365 * 40]:
                t_between = time_step / 365.0
                writer.add_vertex_snapshot_full(
                    name=f"T_vertex_{t_between:.1f}a",
                    mesh=mesh,
                    T=T
                )

            time_step += 1
            bar()

    writer.close()
    _write_progress('simulation', time_steps, time_steps, 'Simulation abgeschlossen.')
    print("Calculation finished.")
