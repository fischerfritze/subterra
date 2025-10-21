from src import powerprofile as pp
from src import mesh as msh
from src import h5py_writer
from src.h5py_writer import H5Writer
from box import Box
from src.tools import weighted_parameter, P_el_values

from fenics import *
from src.paths import RESULTS_DIR, PARAMETER_FILE, PARAMETER_FILE_SI, TEMP_DIR, BASE_DIR, PARAMS_DIR
from alive_progress import alive_bar

import json
import subprocess
import traceback
import os
import numpy as np
import time
import psutil

def run_calculation():
    # SI-conversion of parameter file
    cmd = ["python3", "src/convert_to_si.py", PARAMETER_FILE, PARAMETER_FILE_SI]

    try:
        subprocess.run(cmd, check=True)
        print(f"SI-convection_matrixertierung erfolgreich: {PARAMETER_FILE_SI}")
    except subprocess.CalledProcessError as e:
        print(f"Fehler beim Ausführen von convert_to_si.py: {e}")
    except FileNotFoundError:
        print("Python oder Skriptdatei nicht gefunden. Bitte Pfade prüfen.")


    # load JSON with Box
    with open(PARAMETER_FILE_SI, "r") as f:
        param_si = Box(json.load(f))
    
    with open(PARAMETER_FILE, "r") as f:
        param = Box(json.load(f))

    print(f"Starting calculation with parameters from {PARAMETER_FILE_SI}")
    
    #Create powerprofile: A - B * cos(2 * pi / 365 * days)
    powerprofile, eta, Q_out, Q_in = pp.multiple_powerprofile(
                A = param_si.power.coefficientA.value,
                B = param_si.power.coefficientB.value,
                years = param.time.simulationYears.value
            )

    #Create meshgrid
    locations = msh.generate_mesh(
        mode = tuple(param_si.meshMode), 
        x_0 = param_si.mesh.xCenter.value, 
        y_0 = param_si.mesh.yCenter.value, 
        distance = param_si.mesh.boreholeDistance.value
        )
    
    mesh = Mesh(TEMP_DIR + "/temp_mesh.xml")
    fd = MeshFunction('size_t', mesh, TEMP_DIR + "/temp_mesh_facet_region.xml")

    n_EWS = len(locations)
    folder_name = f"{n_EWS}EWS_κ = {param_si.ground.thermalConductivity.value}_{param_si.time.simulationYears.value}years"
    
    base_folder = os.path.join(RESULTS_DIR, folder_name)
    os.makedirs(base_folder, exist_ok=True)

    ###########################
    ###Create FEniCS objects###
    ###########################
        
    #Create function space:
    V_space = FunctionSpace(
        mesh,
        "Lagrange",
        1
    )
    
    Vec_space = VectorFunctionSpace(
        mesh,
        "Lagrange",
        1
    )
    
    #Create boundary conditions: T = T_0 on boundary
    boundary_condition = DirichletBC(
        V_space,
        param_si.ground.temperature.value,
        fd,
        1
    )
    
    #Create initial conditions: T = T_0 at t = 0
    initial_condition = Expression(
        "T_0",
        degree = 1,
        T_0 = param_si.ground.temperature.value
    )
    
    T_1 = interpolate(initial_condition, V_space)
    
    #Trial and test functions:
    T_trial = TrialFunction(V_space)
    v_test = TestFunction(V_space)
    
    #Temperature function at new time step:
    T = Function(V_space)

    #Normal vector:
    n_vector = FacetNormal(mesh)

    #######################
    ###convection on/off###
    #######################

    try:
        max_distance = mesh.hmax()
        max_velocity = max(param_si.groundwater.velocityX.value, param_si.groundwater.velocityY.value)
        
        if param_si.ground.porosity.value != 0.0:
            # Weighted Parameters
            thermalConductivity, heatCapacityDensity = weighted_parameter(
                model = param_si.ground.modelType.value,
                ground_parameter = [
                    param_si.ground.thermalConductivity.value,
                    param_si.ground.heatCapacityDensity.value
                    ],
                fluid_parameter = [
                    param_si.groundwater.thermalConductivity.value, 
                    param_si.groundwater.density.value * param_si.groundwater.specificHeat.value
                    ],
                porosity = param_si.ground.porosity.value
            )
        else: 
            thermalConductivity = param_si.ground.thermalConductivity.value 
            heatCapacityDensity = param_si.ground.heatCapacityDensity.value

        # a = λ / (ρc)
        diffusionCoefficient = thermalConductivity / heatCapacityDensity

        # diffusion term: ∇T·∇v*dx
        diffusion_term = dot(nabla_grad(T_trial), nabla_grad(v_test)) * dx
        
        # mass term: T*v*dx
        mass_term = T_trial * v_test * dx

        if param_si.enableConvection is True:
            #convection coefficient: b = n_porosity * (ρc)_groundwater / (ρc)_ground
            convectionCoefficient = Constant(
                param_si.ground.porosity.value * param_si.groundwater.density.value * param_si.groundwater.specificHeat.value / param_si.ground.heatCapacityDensity.value
                )

            # velcoity vector: v = [v_x, v_y]
            v_vec = as_vector([
                Constant(param_si.groundwater.velocityX.value), 
                Constant(param_si.groundwater.velocityY.value)
                ])

            # convection term: ∇·(v*T) * v_test * dx
            convection_term = div(v_vec * T_trial) * v_test * dx

            # Peclet-number: Pe = v * L / a
            peclet_number =  max_velocity * max_distance / diffusionCoefficient

            if peclet_number > 2.0:
                raise RuntimeWarning(f"peclet_number_max = {peclet_number:.2f} \n Warning: calculation numerical unstable")
            print(f"peclet_number_max = {peclet_number:.2f}")

            # assamble matrices
            convection_matrix = assemble(convection_term)
            diffusion_matrix = assemble(diffusion_term)
            mass_matrix = assemble(mass_term)

            # A_matrix with convection
            A_matrix = mass_matrix + param_si.time.timeStepHours.value * diffusionCoefficient *  diffusion_matrix + param_si.time.timeStepHours.value * convectionCoefficient * convection_matrix

        else:  # convection == "off"
            # Neumann-nuber: Ne = a * dt / L²
            neumann_number = diffusionCoefficient * param_si.time.timeStepHours.value / (max_distance**2)
            print(f"Ne_max = {neumann_number:.2f}")

            # A_matrix without convection
            diffusion_matrix = assemble(diffusion_term)
            mass_matrix = assemble(mass_term)

            A_matrix = mass_matrix + param_si.time.timeStepHours.value * diffusionCoefficient * diffusion_matrix

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
    solver = PETScLUSolver()

    #Itteration over time steps in hours
    time_steps = int(param_si.time.simulationYears.value / param_si.time.timeStepHours.value)

    keys = [f'COP_b{i}' for i in range(n_EWS)]

    # HDF5-Writer anlegen (Dateipfad nach Wunsch)
    writer = H5Writer(path=f"{base_folder}/sim_{param.time.simulationYears.value}years.h5", n_EWS=n_EWS, compression="lzf", flush_every=365)


    with alive_bar(time_steps, title='SubTerra is running', bar='smooth') as bar:
        t = 1
        total_flux = 0.0
        E_probe_sum = 0.0

        while t <= time_steps:
            # CPU und RAM auslastung abfragen
            cpu = psutil.cpu_percent(interval=0.0)
            ram = psutil.virtual_memory().percent

            # Zusatztext im Fortschrittsbalken aktualisieren
            bar.text(f'(CPU: {cpu:.1f}%, RAM: {ram:.1f}%)')

            Q_dict = powerprofile.get(t)
            Q      = Q_dict * param_si.time.timeStepHours.value  / (heatCapacityDensity)

            # RHS
            b = mass_matrix * T_1.vector()
            for loc in locations:
                f_Q = PointSource(V_space, loc, Q)
                f_Q.apply(b)
            boundary_condition.apply(b)

            # Lösen
            solver.solve(A_matrix, T.vector(), b)

            # Randfluss (ggf. ausdünnen, falls teuer)
            flux_boundary = assemble(-thermalConductivity * dot(nabla_grad(T), n_vector) * ds)

            # --- pro EWS: Temperatur & elektrische Energie (als Zeilenvektoren) ---
            r_EWS = param_si.power.pipeRadius.value
            Temp_EWS_row = np.empty(n_EWS, dtype=np.float32)
            W_el_row     = np.empty(n_EWS, dtype=np.float32)

            for i in range(n_EWS):
                x = locations[i].x()
                y = locations[i].y()
                # 4-Punkt-Mittel
                T_EWS = np.average([
                    T(Point(x - r_EWS, y)),
                    T(Point(x + r_EWS, y)),
                    T(Point(x, y - r_EWS)),
                    T(Point(x, y + r_EWS)),
                ])
                Temp_EWS_row[i] = T_EWS

                W_el_row[i] = P_el_values(
                    Q =Q_dict,
                    T = T_EWS,
                    T_H = param_si.temperatureHot.value,
                    delta_t = param_si.time.timeStepHours.value,
                    gamma = param_si.power.efficiency.value
                )
            #Q: float, T : float, T_H: float, delta_t: float, gamma: float
            # --- Energiemengen / Fehler ---
            E_ground_i = assemble(heatCapacityDensity * T_1 * dx) - assemble(heatCapacityDensity * T * dx)
            E_flux_i   = - param_si.time.timeStepHours.value  * flux_boundary
            E_probe_i  =  param_si.time.timeStepHours.value  * Q_dict * n_EWS

            error_i = E_ground_i + E_flux_i + E_probe_i

            # --- Schrittwerte in HDF5 (keine Python-Listen mehr) ---
            writer.append_step(
                day=t,
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

            # Zustand updaten
            T_1.assign(T)
            total_flux += E_flux_i
            E_probe_sum += E_probe_i

            # # Snapshots (selten): Vertex-Feld einmalig speichern
            if t in [365 * 1, 365 * 10, 365 * 20, 365 * 30, 365 * 40]:
                t_between = t / 365.0
                
                # Variante A: Vertex-basierter Snapshot (empfohlen bei CG1)
                writer.add_vertex_snapshot_full(
                    name = f"T_vertex_{t_between:.1f}a",
                    mesh = mesh,
                    T = T
                )

                # ODER Variante B: DOF-basierter Snapshot (für höheren Grad)
                # writer.add_dof_snapshot(
                #     name=f"T_dof_{t_between:.1f}a",
                #     V_space=V_space,
                #     T=T,
                #     save_mesh=mesh  # optional; weglassen, wenn Größe minimal bleiben soll
                # )

            t += 1
            bar()

    # ganz am Ende:
    writer.close()





    # import matplotlib.pyplot as plt

    # plt.plot(powerprofile.keys(), powerprofile.values(), label='$Q_{ges}$')
    # plt.savefig("/home/Refactored/results/plot.png", dpi=300, bbox_inches="tight")
    # plt.close()

    print("Calculation finished.")