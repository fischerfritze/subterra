FROM ghcr.io/scientificcomputing/fenics-gmsh:2024-05-30

WORKDIR /subterra

COPY src/simulation src/simulation
RUN pip install -r src/simulation/requirements.txt

CMD ["python", "src/simulation/calculation.py"]
