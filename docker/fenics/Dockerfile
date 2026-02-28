# SubTerra FEniCSx simulation container
# Used by the Laravel backend to run mesh generation and simulations.
# NOT a long-running service — spawned per job via `docker run`.
FROM dolfinx/dolfinx:v0.9.0

WORKDIR /subterra

# Copy Python simulation code
COPY src/ /subterra/src/
COPY requirements.txt /subterra/requirements.txt

# Install gmsh (Python API) and extra dependencies not in the base image.
# DOLFINx image provides: dolfinx, basix, ufl, ffcx, petsc4py, mpi4py,
# numpy, scipy, h5py, matplotlib, sympy.
RUN pip install --no-cache-dir \
    gmsh \
    alive-progress \
    python-box \
    psutil \
    || true

# Copy and prepare entrypoint
COPY docker/entrypoint.sh /subterra/entrypoint.sh
RUN chmod +x /subterra/entrypoint.sh

ENTRYPOINT ["/subterra/entrypoint.sh"]
CMD ["python3", "--help"]
