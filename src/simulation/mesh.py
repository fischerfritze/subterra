import math
import subprocess
import numpy as np
import os
import json

from box import Box
from src.simulation.utils.paths import PARAMETER_FILE_SI, TEMP_DIR

LOCATIONS_FILE = os.path.join(TEMP_DIR, "locations.json")


def generate_mesh(mode, x_0, y_0, distance):
    """Generate mesh and save locations to JSON.
    
    Returns:
        list of [x, y] coordinate pairs (serializable).
    """
    print("--------------------------------------------------------------------")
    if mode[0] == 'hexa':
        locations, EWS_dict = generate_hexa_ews(
            x_b0=x_0, y_b0=y_0, d=distance, rings=mode[1])
        meshing(EWS_dict)
        save_locations(locations)
        return locations

    elif mode[0] == 'square':
        locations, EWS_dict = generate_square_ews(
            x_b0=x_0, y_b0=y_0, d=distance, rings=mode[1])
        meshing(EWS_dict)
        save_locations(locations)
        return locations

    else:
        raise ValueError(f"Unknown mode: {mode}")


def save_locations(locations):
    """Save borehole locations to JSON file in temp directory."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    with open(LOCATIONS_FILE, "w") as f:
        json.dump(locations, f, indent=2)
    print(f"Locations saved to {LOCATIONS_FILE}")


def load_locations():
    """Load borehole locations from JSON file.
    
    Returns:
        list of [x, y] coordinate pairs.
    """
    if not os.path.exists(LOCATIONS_FILE):
        raise FileNotFoundError(
            f"Locations file not found: {LOCATIONS_FILE}. "
            "Run mesh generation first."
        )
    with open(LOCATIONS_FILE, "r") as f:
        return json.load(f)


def generate_hexa_ews(x_b0, y_b0, d, rings):
    locations = []
    hexa_EWS = {}

    # Schritt 1: Erstelle hexagonales Gitter mit ausreichend Punkten
    grid = {}
    index = 1

    for q in range(-rings, rings + 1):
        for r in range(-rings, rings + 1):
            s = -q - r  # Bedingung für hexagonale Koordinaten
            if abs(s) <= rings:
                x = x_b0 + d * (q + r / 2)
                y = y_b0 + d * math.sqrt(3) / 2 * r
                grid[f"BH{index:02d}"] = (x, y)
                index += 1

    # Schritt 2: Filtere Punkte außerhalb d * rings
    index = 1
    for _, (x, y) in grid.items():
        distance = math.sqrt((x - x_b0) ** 2 + (y - y_b0) ** 2)
        if distance <= rings * d:
            hexa_EWS[f"BH{index:02d}"] = (x, y)
            locations.append([x, y])
            index += 1

    return locations, hexa_EWS


def generate_square_ews(x_b0, y_b0, d, rings):
    locations = []
    square_EWS = {}

    index = 1
    for i in range(-rings, rings + 1):
        for j in range(-rings, rings + 1):
            x = x_b0 + i * d
            y = y_b0 + j * d

            # Abstand zum Zentrum berechnen
            distance = max(abs(i), abs(j))
            if distance <= rings:
                square_EWS[f"BH{index:02d}"] = (x, y)
                locations.append([x, y])
                index += 1

    return locations, square_EWS


def geo_template_circles_alt(EWS_dict, ms, ms_fine, x_len, y_len, x_0, y_0, radius):
    num = len(EWS_dict)
    number_list = np.arange(5, 5+num, 1).tolist()
    number_list = "{" + ", ".join(map(str, number_list)) + "}"

    # Initialize point entries based on the dictionary
    circle_num = 12
    point_entries = ""
    counter_point = 5
    counter_line = 5
    for i, (_, coords) in enumerate(EWS_dict.items(), start=2):
        x, y = coords  # Directly unpack the tuple
        point_entries += f"Point({counter_point}) = {{{x}, {y}, 0, ms_fine}};\n    "
        start_point = counter_point
        start_line = counter_line
        for j in range(circle_num):
            angle = 2*np.pi/circle_num * j
            point_entries += f"Point({counter_point+1}) = {{{x + radius*np.cos(angle)}, {y + radius*np.sin(angle)}, 0, ms_fine}};\n    "
            counter_point += 1

        for k in range(circle_num-1):
            point_entries += f"Line({counter_line}) = {{{start_point + k + 1}, {start_point + k+2}}};\n    "
            counter_line += 1

        point_entries += f"Line({counter_line}) = {{{start_point + circle_num}, {start_point + 1}}};\n    "
        point_entries += f"Curve Loop({i}) = {{{start_line}:{counter_line}}};\n    "
        counter_point += 1
        counter_line += 1

    geo_template = f"""
    SetFactory("OpenCASCADE");

    // Mesh Size Factor
    ms = {ms};
    ms_fine = {ms_fine};

    // Define the coordinates of the points
    x_m = {x_0};                // x-coordinate of the center
    y_m = {y_0};                // y-coordinate of the center

    // Create the boundary lines
    Point(1) = {{-{x_len}, -{y_len}, 0, ms}};
    Point(2) = {{ {x_len}, -{y_len}, 0, ms}};
    Point(3) = {{ {x_len},  {y_len}, 0, ms}};
    Point(4) = {{-{x_len},  {y_len}, 0, ms}};

    Line(1) = {{1, 2}};
    Line(2) = {{2, 3}};
    Line(3) = {{3, 4}};
    Line(4) = {{4, 1}};

    Curve Loop(1) = {{1, 2, 3, 4}};

    // Define mesh points
    {point_entries} 
    
    // Physical Groups 
    Plane Surface(1) = {{1, 2:{num+1}}};
    Physical Curve("Boundary") = {{1, 2, 3, 4}};
    Physical Curve("Boreholes") = {{77:{counter_line-1}}};
    Physical Surface("Ground") = {{1}};

    Field[1] = Distance;
    Field[1].CurvesList = {{5:{counter_line-1}}}; // Alle Kreiskanten für das Distanzfeld

    Field[2] = Threshold;
    Field[2].InField = 1;
    Field[2].SizeMin = ms_fine;  // Feines Mesh nah an den Kreisen
    Field[2].SizeMax = ms;       // Grobes Mesh weiter weg
    Field[2].DistMin = 5;        // Bis 2 Einheiten Abstand fein
    Field[2].DistMax = 15;       // Danach wird es grober

    Background Field = 2;

    Mesh.CharacteristicLengthMin = 1;
    Mesh.CharacteristicLengthMax = ms;
    """

    return geo_template


def geo_template_points(EWS_dict, ms, ms_fine, x_len, y_len, x_0, y_0, radius):

    num = len(EWS_dict)
    number_list = np.arange(5, 5+num, 1).tolist()
    number_list = "{" + ", ".join(map(str, number_list)) + "}"

    # Initialize point entries based on the dictionary
    point_entries = ""
    for i, (key, coords) in enumerate(EWS_dict.items(), start=5):
        x, y = coords  # Directly unpack the tuple
        point_entries += f"    Point({i}) = {{{x}, {y}, 0, ms_fine}};\n"

    geo_template = f"""
    SetFactory("OpenCASCADE");

    // Mesh Size Factor
    ms = {ms};
    ms_fine = {ms_fine};

    // Define the coordinates of the points
    x_m = {x_0};                // x-coordinate of the center
    y_m = {y_0};                // y-coordinate of the center

    // Define mesh points
    {point_entries} 

    // Create a distance field from the specified points
    Field[1] = Distance;
    Field[1].NodesList = {number_list}; // Reference points for distance

    // Create a threshold field to control mesh size
    Field[2] = Threshold;
    Field[2].IField = 1;       // Reference the distance field
    Field[2].LcMin = ms_fine;  // Minimum mesh size near the points
    Field[2].LcMax = ms;       // Maximum mesh size away from the points
    Field[2].DistMin = 0;      // Start at distance 0 
    Field[2].DistMax = 30;     // Distance of the effect

    // Set the background field to the threshold
    Background Field = 2;

    // Create the boundary lines
    Point(1) = {{-{x_len}, -{y_len}, 0, ms}};
    Point(2) = {{ {x_len}, -{y_len}, 0, ms}};
    Point(3) = {{ {x_len},  {y_len}, 0, ms}};
    Point(4) = {{-{x_len},  {y_len}, 0, ms}};

    Line(1) = {{1, 2}};
    Line(2) = {{2, 3}};
    Line(3) = {{3, 4}};
    Line(4) = {{4, 1}};

    Curve Loop(1) = {{1, 2, 3, 4}};
    Plane Surface(1) = {{1}};

    // Physical Groups (optional)
    Physical Curve("Boundary") = {{1, 2, 3, 4}};
    Physical Surface("Ground") = {{1}};
    """

    return geo_template


def geo_template_circles(EWS_dict, ms, ms_fine, x_len, y_len, x_0, y_0, radius):
    num = len(EWS_dict)
    number_list = np.arange(5, 5+num, 1).tolist()
    number_list = "{" + ", ".join(map(str, number_list)) + "}"

    # TODO: Remove unused code
    # Initialize point entries based on the dictionary
    # circle_num = 12
    # point_entries = ""
    # counter_point = 5
    # counter_line = 5
    # for i, (key, coords) in enumerate(EWS_dict.items(), start=2):
    #     x, y = coords  # Directly unpack the tuple
    #     point_entries += f"Point({counter_point}) = {{{x}, {y}, 0, ms_fine}};\n    "
    #     start_point = counter_point
    #     start_line = counter_line
    #     for j in range(circle_num):
    #         angle = 2*np.pi/circle_num * j
    #         point_entries += f"Point({counter_point+1}) = {{{x + radius*np.cos(angle)}, {y+ radius*np.sin(angle)}, 0, ms_fine}};\n    "
    #         counter_point += 1

    #     for k in range(circle_num-1):
    #         point_entries +=f"Line({counter_line}) = {{{start_point + k + 1}, {start_point + k+2}}};\n    "
    #         counter_line += 1

    #     point_entries +=f"Line({counter_line}) = {{{start_point + circle_num}, {start_point + 1}}};\n    "
    #     point_entries +=f"Curve Loop({i}) = {{{start_line}:{counter_line}}};\n    "
    #     counter_point += 1
    #     counter_line += 1
    
    cylinder_entries = ""
    counter_cylinder = 2

    for i, (key, coords) in enumerate(EWS_dict.items(), start=2):
        x, y = coords  # Directly unpack the tuple
        cylinder_entries += f"Circle({counter_cylinder}) = {{{x}, {y}, 0, {radius}, 0 , 2*Pi}},\n     "
        counter_cylinder += 1

    geo_template = f"""
    SetFactory("OpenCASCADE");

    // Mesh Size Factor
    ms = {ms};
    ms_fine = {ms_fine};

    // Define the coordinates of the points
    x_m = {x_0};                // x-coordinate of the center
    y_m = {y_0};                // y-coordinate of the center

    // Create the boundary lines
    Point(1) = {{-{x_len}, -{y_len}, 0, ms}};
    Point(2) = {{ {x_len}, -{y_len}, 0, ms}};
    Point(3) = {{ {x_len},  {y_len}, 0, ms}};
    Point(4) = {{-{x_len},  {y_len}, 0, ms}};

    Line(1) = {{1, 2}};
    Line(2) = {{2, 3}};
    Line(3) = {{3, 4}};
    Line(4) = {{4, 1}};

    Curve Loop(1) = {{1, 2, 3, 4}};
    Plane Surface(1) = {{1}};

    // Define mesh points
    cylinders[] = {{
        {cylinder_entries} 
    }};
    BooleanDifference(9) = {{ Surface{{1}}; Delete; }}{{ Surface{{2:8}}; }};


    // Physical Groups 
    Physical Curve("Boundary") = {{1, 2, 3, 4}};
    Physical Surface("Ground") = {{9}};

    // Create Distance Field for Cylinders
    Field[1] = Distance;
    Field[1].SurfacesList = {{GetEntities(Surface)}}; // Gets all Cylinder surfaces

    // Create Threshold Field for mesh refinement
    Field[2] = Threshold;
    Field[2].InField = 1;
    Field[2].SizeMin = ms_fine;
    Field[2].SizeMax = ms;
    Field[2].DistMin = 3;  // Reduced to avoid unnecessary fine areas
    Field[2].DistMax = 10;

    // Set Background Field
    Background Field = 2;

    // Mesh settings
    Mesh.CharacteristicLengthMax = ms;
    """

    return geo_template


def meshing(EWS_dict):
    with open(PARAMETER_FILE_SI, "r") as f:
        param = Box(json.load(f))

    # Create the .geo file
    template = geo_template_points(
        EWS_dict,
        ms=param.mesh.meshFactor.value,
        ms_fine=param.mesh.meshFine.value,
        x_len=param.mesh.xLength.value / 2,
        y_len=param.mesh.yLength.value / 2,
        x_0=param.mesh.xCenter.value,
        y_0=param.mesh.yCenter.value,
        radius=param.power.pipeRadius.value
    )

    # Write .geo file
    geo_file_name = TEMP_DIR + "/temp_mesh.geo"
    with open(geo_file_name, "w") as geo_file:
        geo_file.write(template)

    # Run Gmsh
    msh_file_name = TEMP_DIR + "temp_mesh.msh"  # Gmsh's default output file
    subprocess.run(["gmsh", "-2", geo_file_name, "-o",
                   msh_file_name, "-format", "msh2"])

    # Convert mesh to XML
    xml_file_name = TEMP_DIR + "/temp_mesh.xml"
    subprocess.run(["dolfin-convert", msh_file_name, xml_file_name])

    # Clean up temporary files
    os.remove(geo_file_name)
    os.remove(msh_file_name)

    print(f"Mesh successfully created and converted to {xml_file_name}.")
    print("--------------------------------------------------------------------")
    # print("---------------------Plot is activated------------------------------")
    # print("--------------------------------------------------------------------")
    # # Plot the created mesh
    # import matplotlib.pyplot as plt
    # from dolfin import Mesh, plot # type: ignore
    # base_folder = os.path.join(RESULTS_DIR)

    # plot(Mesh(xml_file_name))
    # plt.title("Generated Mesh", fontsize = 22)
    # plt.xlabel("X-axis", fontsize = 22)
    # plt.ylabel("Y-axis", fontsize = 22)
    # plt.xticks(fontsize = 18)
    # plt.yticks(fontsize = 18)
    # plt.show()
