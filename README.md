# SubTerra (refactored)

A small, self-contained toolkit for steady / transient thermal simulations in subsurface geometries. This refactored version extracts core utilities for mesh handling, parameter conversion, calculation, plotting and HDF5 results writing. The project focuses on producing power profiles and temperature fields for simple engineered geological systems.

This README covers quick setup, running common tasks, input parameter conventions, and the repository layout.

## Quick facts

- Language: Python 3.10+ (tested in the provided dev container)
- Purpose: run thermal subsurface calculations and export results as HDF5 and CSV for plotting
- Key outputs: HDF5 simulations in `results/` and a multi-profile CSV at `results/powerprofile_multi.csv`

## Install

1. Create and activate a Python virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

2. Install dependencies from the top-level `requirements.txt` (provided in the original workspace root). If you only need the refactored package, install requirements listed in that file or use the system's package manager.

```bash
pip install -r ../requirements.txt
```

Note: if you run into system-level compiled dependency issues (e.g., MPI / FEniCS), consider running in the provided Docker/dev container or using prebuilt wheels suited to your platform.

## Run the main example

There is a small top-level runner that demonstrates end-to-end usage.

```bash
cd /home/SubTerra_refactored
python3 main.py
```

This will execute a sequence of calculations and write results to `results/`. Several example HDF5 files are included under `results/` (e.g. `7EWS_.../sim_1years.h5`), as well as a `powerprofile_multi.csv` produced by the power profile utilities.

## Core modules

The refactored code is in the `src/` package. Key modules:

- `src/mesh.py` — utilities for mesh loading and simple mesh helpers.
- `src/convert_to_si.py` — helper functions to convert parameters to SI units.
- `src/calculation.py` — the main physics and simulation orchestration.
- `src/h5py_writer.py` — writing simulation outputs to HDF5 for later analysis/plotting.
- `src/powerprofile.py` — compute and export power profiles (CSV used in `results/`).
- `src/plot.py` — simple plotting helpers to generate the `results/plots/*` images.
- `src/paths.py` — central paths and IO helpers used across the package.
- `src/tools.py` — utility functions shared across modules.

## Parameters and meshes

Example parameter JSON files are in `params/`:

- `params/parameter.json` — default parameter set (unitless or domain-specific).
- `params/parameter_si.json` — parameters already converted to SI.

Meshes and temporary mesh files are in `meshes/` and `params/temp/` respectively. The project includes simple example mesh files for quick testing.

## Results

After running the examples you will find:

- HDF5 simulation outputs under `results/<case>/sim_*.h5`.
- A combined CSV of power profiles at `results/powerprofile_multi.csv`.
- Plots in `results/plots/` showing temperature fields for selected cases.

You can inspect HDF5 files with standard viewers (e.g., `h5py` in Python) or use the plotting utilities in `src/plot.py`.

## Tests

There is a `tests/` folder prepared for unit and integration tests. Run tests with your preferred test runner (e.g., `pytest`).

```bash
pip install pytest
pytest -q
```

## Development notes

- The refactored package aims to be small and easy to reuse in other projects. Import the package by adding the repo root to `PYTHONPATH` or installing it in editable mode.

```bash
pip install -e .
```

- If you need platform-specific support (MPI, FEniCS) use the project's Docker setup in the original workspace root (`Dockerfile`, `docker_*` helpers).

## File tree (important files)

```
SubTerra_refactored/
├─ main.py                 # top-level runner that uses src/ to run examples
├─ params/                 # JSON parameter sets and temp mesh fragments
│  ├─ parameter.json
│  └─ parameter_si.json
├─ results/                # output HDF5, CSV and plots
├─ src/                    # refactored Python package (calculation, IO, plotting)
└─ README.md               # this file
```

## Contact / License

This repository is provided as-is for research and demonstration. Add license and contact details as appropriate for your project.

## Troubleshooting

- If Python raises ImportError for compiled dependencies, first try the dev container or Docker image included in the original workspace.
- For numerical differences vs. the original codebase, ensure the same parameter sets and mesh files are used (see `params/` and `meshes/`).

If you'd like, I can also:

- Add a minimal CLI for running specific parameter sets.
- Add an example Jupyter notebook that loads HDF5 output and renders plots.

---

README last updated: automated by the refactor helper
This is the how it goes!
