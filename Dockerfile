FROM ghcr.io/scientificcomputing/fenics-gmsh:2024-05-30

WORKDIR /home/SubTerra

# Installiere alive-progress via pip
RUN pip install alive-progress
RUN pip install pyvista
RUN apt update
RUN apt install -y vim-tiny
RUN apt clean && \
    rm -rf /var/lib/apt/lists/*

# Kopiere dein Projekt hinein
COPY . /home/SubTerra

# Startkommando-Varianten (sodass der Container nicht terminiert)
# 1) Python-Loop läuft unendlich
#CMD ["python3", "EWS_wrapper.py"]
# 2) Es wird eine Shell geöffnet
CMD ["/bin/bash"]
# 3) Der python-Prozess wird im Hintergrund gestartet und zusätzlich eine Shell geöffnet
# CMD ["./wrapper_start"]