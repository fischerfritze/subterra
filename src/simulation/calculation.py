import json
import traceback
from os import makedirs, path

import fenics
import numpy as np
from alive_progress import alive_bar
from box import Box
from psutil import cpu_percent, virtual_memory

from src.simulation import mesh as msh
from src.simulation import powerprofile as pp
from src.simulation.utils.h5py_writer import H5Writer
import src.simulation.utils.paths as _paths
from src.simulation.utils.tools import P_el_values, weighted_parameter
from src.simulation.utils.convert_to_si import run_conversion
import os as _os


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


def run_calculation():
    """Legacy entry point: runs SI conversion, mesh generation, and simulation."""

    # SI-conversion of parameter file
    try:
        run_conversion(_paths.PARAMETER_FILE, _paths.PARAMETER_FILE_SI)
        print(f"SI-Konvertierung erfolgreich: {_paths.PARAMETER_FILE_SI}")
        
    except Exception as e:
        print(f"Fehler bei der SI-Konvertierung: {e}")
        traceback.print_exc()
        exit(1)
        

    # load JSON data
    with open(_paths.PARAMETER_FILE_SI, "r") as f:
        params_si = Box(json.load(f))
    with open(_paths.PARAMETER_FILE, "r") as f:
        params = Box(json.load(f))

    # Generate mesh (legacy: all-in-one)
    msh.generate_mesh(
        mode=tuple(params_si.meshMode),
        x_0=params_si.mesh.xCenter.value,
        y_0=params_si.mesh.yCenter.value,
        distance=params_si.mesh.boreholeDistance.value
    )

    return run_simulation(params, params_si)


def run_simulation(params: Box = None, params_si: Box = None):
    """Run the FEniCS simulation using a previously generated mesh.
    
    Loads mesh and borehole locations from params/temp/.
    If params/params_si are not provided, loads them from the default paths.
    """
    if params is None:
        with open(_paths.PARAMETER_FILE, "r") as f:
            params = Box(json.load(f))
    if params_si is None:
        # Ensure SI file exists
        if not path.exists(_paths.PARAMETER_FILE_SI):
            run_conversion(_paths.PARAMETER_FILE, _paths.PARAMETER_FILE_SI)
        with open(_paths.PARAMETER_FILE_SI, "r") as f:
            params_si = Box(json.load(f))

    return _run_simulation(params, params_si)


def _run_simulation(params: Box, params_si: Box):

    TEMP_MESH_PATH = path.join(_paths.TEMP_DIR, "temp_mesh.xml")
    TEMP_MESH_FACET_REGION_PATH = path.join(
        _paths.TEMP_DIR, "temp_mesh_facet_region.xml")
    folder_name = f"{params_si.meshMode[0]}_{params_si.meshMode[1]}_κ = {params_si.ground.thermalConductivity.value}_{params_si.time.simulationYears.value}years"
    base_folder = path.join(_paths.RESULTS_DIR, folder_name)
    makedirs(base_folder, exist_ok=True)

    print(f"Starting simulation with parameters from {_paths.PARAMETER_FILE_SI}")
    _write_progress('simulation', 0, 1, 'Simulation wird vorbereitet...')

    # Load borehole locations from previously generated mesh
    locations_raw = msh.load_locations()
    locations = [fenics.Point(loc[0], loc[1]) for loc in locations_raw]

    # TODO: Remove unused variables
    # create powerprofile: A - B * cos(2 * pi / 365 * days)
    powerprofile, eta, Q_out, Q_in = pp.multiple_powerprofile(
        A=params_si.power.coefficientA.value,
        B=params_si.power.coefficientB.value,
        years=params.time.simulationYears.value
    )

    # Load mesh from temp directory
    if not path.exists(TEMP_MESH_PATH):
        raise FileNotFoundError(
            f"Mesh file not found: {TEMP_MESH_PATH}. "
            "Run mesh generation first (python -m src.mesh_runner)."
        )

    mesh = fenics.Mesh(TEMP_MESH_PATH)
    fd = fenics.MeshFunction('size_t', mesh, TEMP_MESH_FACET_REGION_PATH)

    n_EWS = len(locations)

    #############################
    ### Create FEniCS objects ###
    #############################

    # create function space
    V_space = fenics.FunctionSpace(
        mesh,
        "Lagrange",
        1
    )

    # create vector space
    Vec_space = fenics.VectorFunctionSpace(
        mesh,
        "Lagrange",
        1
    )

    # create boundary conditions: T = T_0 on boundary
    boundary_condition = fenics.DirichletBC(
        V_space,
        params_si.ground.temperature.value,
        fd,
        1
    )

    # create initial conditions: T = T_0 at t = 0
    initial_condition = fenics.Expression(
        "T_0",
        degree=1,
        T_0=params_si.ground.temperature.value
    )

    T_1 = fenics.interpolate(initial_condition, V_space)

    # trial and test functions:
    T_trial = fenics.TrialFunction(V_space)
    v_test = fenics.TestFunction(V_space)

    # temperature function:
    T = fenics.Function(V_space)

    # normal vector:
    n_vector = fenics.FacetNormal(mesh)

    #########################
    ### convection on/off ###
    #########################

    try:
        max_distance = mesh.hmax()
        max_velocity = max(params_si.groundwater.velocityX.value,
                           params_si.groundwater.velocityY.value)

        if params_si.ground.porosity.value != 0.0:
            # weighted Parameters
            thermalConductivity, heatCapacityDensity = weighted_parameter(
                model=params_si.ground.modelType.value,
                ground_parameter=[
                    params_si.ground.thermalConductivity.value,
                    params_si.ground.heatCapacityDensity.value
                ],
                fluid_parameter=[
                    params_si.groundwater.thermalConductivity.value,
                    params_si.groundwater.density.value * params_si.groundwater.specificHeat.value
                ],
                porosity=params_si.ground.porosity.value
            )
        else:
            thermalConductivity = params_si.ground.thermalConductivity.value
            heatCapacityDensity = params_si.ground.heatCapacityDensity.value

        # a = λ / (ρc)
        diffusionCoefficient = thermalConductivity / heatCapacityDensity

        # diffusion term: ∇T·∇v*dx
        diffusion_term = fenics.dot(fenics.nabla_grad(
            T_trial), fenics.nabla_grad(v_test)) * fenics.dx

        # mass term: T*v*dx
        mass_term = T_trial * v_test * fenics.dx

        if params_si.enableConvection is True:
            # convection coefficient: b = n_porosity * (ρc)_groundwater / (ρc)_ground
            convectionCoefficient = fenics.Constant(
                params_si.ground.porosity.value * params_si.groundwater.density.value *
                params_si.groundwater.specificHeat.value /
                params_si.ground.heatCapacityDensity.value
            )

            # velcoity vector: v = [v_x, v_y]
            v_vec = fenics.as_vector([
                fenics.Constant(params_si.groundwater.velocityX.value),
                fenics.Constant(params_si.groundwater.velocityY.value)
            ])

            # convection term: ∇·(v*T) * v_test * dx
            convection_term = fenics.div(v_vec * T_trial) * v_test * fenics.dx

            # Peclet-number: Pe = v * L / a
            peclet_number = max_velocity * max_distance / diffusionCoefficient

            if peclet_number > 2.0:
                raise RuntimeWarning(
                    f"peclet_number_max = {peclet_number:.2f} \n Warning: calculation numerical unstable")
            print(f"peclet_number_max = {peclet_number:.2f}")

            # assamble matrices
            convection_matrix = fenics.assemble(convection_term)
            diffusion_matrix = fenics.assemble(diffusion_term)
            mass_matrix = fenics.assemble(mass_term)

            # A_matrix with convection
            A_matrix = mass_matrix + params_si.time.timeStepHours.value * diffusionCoefficient * \
                diffusion_matrix + params_si.time.timeStepHours.value * \
                convectionCoefficient * convection_matrix

        else:  # convection == "off"
            # Neumann-number: Ne = a * dt / L²
            neumann_number = diffusionCoefficient * \
                params_si.time.timeStepHours.value / (max_distance**2)
            print(f"Ne_max = {neumann_number:.2f}")

            # A_matrix without convection
            diffusion_matrix = fenics.assemble(diffusion_term)
            mass_matrix = fenics.assemble(mass_term)

            A_matrix = mass_matrix + params_si.time.timeStepHours.value * \
                diffusionCoefficient * diffusion_matrix

    except ValueError as e:
        print(f"Value error: \n {e}")
        traceback.print_exc()
        exit(1)

    except RuntimeWarning as e:
        print(f"There is an numerical issu for this ground parameter: \n {e}")
        traceback.print_exc()
        exit(1)

    except Exception as e:
        print(f"An unexpected exeption occured: \n {e}")
        traceback.print_exc()
        exit(1)

    boundary_condition.apply(A_matrix)
    solver = fenics.PETScLUSolver()

    # Iteration over time steps in hours
    time_steps = int(params_si.time.simulationYears.value /
                     params_si.time.timeStepHours.value)

    keys = [f'COP_b{i}' for i in range(n_EWS)]

    # HDF5-Writer
    writer = H5Writer(path=f"{base_folder}/sim_{params.time.simulationYears.value}years.h5",
                      n_EWS=n_EWS, compression="lzf", flush_every=365)

    with alive_bar(time_steps, title='SubTerra is running', bar='smooth') as bar:
        time_step = 1
        total_flux = 0.0
        E_probe_sum = 0.0
        last_progress_pct = -5  # Track last written percentage

        while time_step <= time_steps:
            # show CPU and RAM
            cpu = cpu_percent(interval=0.0)
            ram = virtual_memory().percent
            bar.text(f'(CPU: {cpu:.1f}%, RAM: {ram:.1f}%)')

            # Write progress every 5% (avoid I/O overhead)
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

            Q = Q_dict * params_si.time.timeStepHours.value / heatCapacityDensity

            # RHS
            b = mass_matrix * T_1.vector()
            for loc in locations:
                f_Q = fenics.PointSource(V_space, loc, Q)
                f_Q.apply(b)
            boundary_condition.apply(b)

            # solve
            solver.solve(A_matrix, T.vector(), b)

            # flux
            flux_boundary = fenics.assemble(-thermalConductivity *
                                            fenics.dot(fenics.nabla_grad(T), n_vector) * fenics.ds)

            # for every EWS/BHE
            r_EWS = params_si.power.pipeRadius.value
            Temp_EWS_row = np.empty(n_EWS, dtype=np.float32)
            W_el_row = np.empty(n_EWS, dtype=np.float32)

            for i in range(n_EWS):
                x = locations[i].x()
                y = locations[i].y()
                # average
                T_EWS = float(np.average([
                    T(fenics.Point(x - r_EWS, y)),
                    T(fenics.Point(x + r_EWS, y)),
                    T(fenics.Point(x, y - r_EWS)),
                    T(fenics.Point(x, y + r_EWS)),
                ]))
                Temp_EWS_row[i] = T_EWS

                W_el_row[i] = P_el_values(
                    Q=Q_dict,
                    T=T_EWS,
                    T_H=params_si.temperatureHot.value,
                    delta_t=params_si.time.timeStepHours.value,
                    gamma=params_si.power.efficiency.value
                )
            # conversion of energy
            E_ground_i = fenics.assemble(heatCapacityDensity * T_1 * fenics.dx) - \
                fenics.assemble(heatCapacityDensity * T * fenics.dx)
            E_flux_i = - params_si.time.timeStepHours.value * flux_boundary
            E_probe_i = params_si.time.timeStepHours.value * Q_dict * n_EWS

            error_i = E_ground_i + E_flux_i + E_probe_i

            # save to HDF5
            writer.append_step(
                day=time_step,
                error=error_i / (3600.0 * 1000.0),
                E_probe=E_probe_i / (3600.0 * 1000.0),
                E_flux=E_flux_i / (3600.0 * 1000.0),
                Delta_E=E_ground_i / (3600.0 * 1000.0),
                E_inout=(E_ground_i + E_probe_i) / (3600.0 * 1000.0),
                Q_probe=np.nan,          # falls du das später nutzen willst
                E_storage=np.nan,        # solange auskommentiert
                W_el_row=W_el_row,
                Temp_EWS_row=Temp_EWS_row
            )

            T_1.assign(T)
            total_flux += E_flux_i
            E_probe_sum += E_probe_i

            # create snapshots
            if time_step in [365 * 1, 365 * 10, 365 * 20, 365 * 30, 365 * 40]:
                t_between = time_step / 365.0

                # TODO: Consider adding a parameter to choose a variant
                # Variante A: Vertex-basierter Snapshot (empfohlen bei CG1)
                writer.add_vertex_snapshot_full(
                    name=f"T_vertex_{t_between:.1f}a",
                    mesh=mesh,
                    T=T
                )

                # ODER Variante B: DOF-basierter Snapshot (für höheren Grad)
                # writer.add_dof_snapshot(
                #     name=f"T_dof_{t_between:.1f}a",
                #     V_space=V_space,
                #     T=T,
                #     save_mesh=mesh  # optional; weglassen, wenn Größe minimal bleiben soll
                # )

            time_step += 1
            bar()

    writer.close()

    _write_progress('simulation', time_steps, time_steps, 'Simulation abgeschlossen.')

    # import matplotlib.pyplot as plt

    # plt.plot(powerprofile.keys(), powerprofile.values(), label='$Q_{ges}$')
    # plt.savefig("/home/Refactored/results/plot.png", dpi=300, bbox_inches="tight")
    # plt.close()

    print("Calculation finished.")
