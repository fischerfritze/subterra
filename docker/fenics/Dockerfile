# SubTerra FEniCS simulation container
# Used by the Laravel backend to run mesh generation and simulations.
# NOT a long-running service — spawned per job via `docker run`.
FROM ghcr.io/scientificcomputing/fenics-gmsh:2024-05-30

WORKDIR /subterra

# Copy Python simulation code
COPY src/ /subterra/src/
COPY requirements.txt /subterra/requirements.txt

# Install only the extra Python dependencies not already in the base image.
# Use --no-deps to avoid pulling transitive deps that conflict with system packages.
# Packages already provided by fenics-gmsh (gmsh, h5py, mpi4py, numpy, scipy,
# matplotlib, meshio, sympy, etc.) are skipped.
RUN pip install --no-cache-dir \
    alive-progress \
    python-box \
    scooby \
    pooch \
    || true \
    && pip install --no-cache-dir --no-deps -r requirements.txt 2>/dev/null || true

# Copy and prepare entrypoint
COPY docker/entrypoint.sh /subterra/entrypoint.sh
RUN chmod +x /subterra/entrypoint.sh

ENTRYPOINT ["/subterra/entrypoint.sh"]
CMD ["python3", "--help"]
