# SubTerra FEniCS simulation container
# Used by the Laravel backend to run mesh generation and simulations.
FROM ghcr.io/scientificcomputing/fenics-gmsh:2024-05-30

WORKDIR /subterra

# Copy Python simulation code
COPY src/ /subterra/src/
COPY requirements.txt /subterra/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create a wrapper script that sets up the work directory symlinks
# so that the Python code can find params/temp and results in the mounted work dir
COPY docker/entrypoint.sh /subterra/entrypoint.sh
RUN chmod +x /subterra/entrypoint.sh

ENTRYPOINT ["/subterra/entrypoint.sh"]
CMD ["python3", "--help"]
