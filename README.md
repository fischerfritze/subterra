# SubTerra
A Python-based toolkit for two dimensional simulations of borehole thermal energy storage (BTES) using FEniCS. For the calculation with groundwater flow, the heat transport equation is be solved:
$$
\frac{\partial T}{\partial t}- a_{\mathrm{eff}} \, \Delta T+ b \, (\vec{v}\cdot \nabla T)= \frac{f}{(\rho c)_{\mathrm{g}}},
$$

$$
a_{\mathrm{eff}} = \left( \frac{\kappa}{\rho c} \right)_{\mathrm{eff}}, \ \ \ \ \ \ \ \ \ b = n_{\mathrm{p}} \frac{(\rho c)_{\mathrm{w}}}{(\rho c)_{\mathrm{g}}}.
$$

**Key features:**
- FEniCS-based thermal simulations with custom geometries


## Prerequisites

This project requires FEniCS, gmsh, and other scientific computing libraries that are difficult to install natively. **Using the provided Docker container is strongly recommended.**

## Setup with Docker Container

### Build Docker Image

1. **Build the image:**
   ```bash
   docker build -t subterra:local .
   ```

2. **Run the container:**
   ```bash
   docker run -it -v $(pwd):/home/SubTerra subterra:local /bin/bash
   ```

3. **Inside the container, run your simulations** (see Usage section below)

## Project Structure

```
subterra-1/
├── Dockerfile              # Docker image definition (based on fenics-gmsh)
├── .devcontainer/          # VS Code dev container configuration
│   └── devcontainer.json
├── main.py                 # Main entry point for simulations
├── requirements.txt        # Python dependencies
├── params/                 # Parameter files
│   ├── parameter.json      # Input parameters (domain-specific units)
│   ├── parameter_si.json   # Auto-generated SI units
│   └── temp/               # Temporary mesh files
├── src/                    # Core Python package
│   ├── calculation.py      # Main simulation logic and FEniCS solver
│   ├── convert_to_si.py    # Parameter unit conversion
│   ├── h5py_writer.py      # HDF5 result export
│   ├── mesh.py             # Mesh handling utilities
│   ├── plot.py             # Visualization functions
│   ├── powerprofile.py     # Power profile calculations
│   ├── paths.py            # Path management
│   └── tools.py            # Helper functions
└── results/                # Output directory (created at runtime)
```

## Usage

### Input Parameters

Edit `params/parameter.json` to configure your simulation:
- Geometry parameters
- Material properties (thermal conductivity, heat capacity)
- Boundary conditions
- Time stepping parameters

### Output

After running simulations, you'll find:
- **HDF5 files**: `results/<case_name>/sim_<time>.h5` — Full simulation state with temperature fields
- **CSV files**: Power profiles and other derived quantities
- **Plots**: Temperature field visualizations (if plotting is enabled)

### Viewing Results

Inspect HDF5 files with Python:
```python
import h5py
with h5py.File('results/your_simulation/sim_20years.h5', 'r') as f:
    print(list(f.keys()))
```

Or use the built-in plotting utilities in `src/plot.py`.

## Key Dependencies

See `requirements.txt` for the complete list.

## License

**SubTerra: Copyright, license, and disclaimer of warranty**

See COPYING for copyright and a list of contributors.

SubTerra is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

SubTerra is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see https://www.gnu.org/licenses/.

---

**Last updated:** January 2026