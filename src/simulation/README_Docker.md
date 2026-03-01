# SubTerra – Docker Quick Reference

## Architecture

| Service | Purpose |
|---------|---------|
| **backend** | Laravel API + Vue SPA + queue workers (PHP, no Python) |
| **redis** | Queue broker & cache |
| **fenics** | FEniCSx simulation image (DOLFINx v0.9.0, MPICH). Build-only – spawned per job via `docker run`. |

Jobs share data through the named volume `subterra_jobs_data`.

## Build & Start

```bash
docker compose build              # build all images
docker compose up -d backend redis  # start web + queue
```

Rebuild after code changes:

```bash
docker compose build --no-cache && docker compose up -d backend redis
```

## Manual Runs (outside Laravel)

### Mesh generation

```bash
docker run --rm \
  -v subterra_jobs_data:/subterra/jobs \
  -e JOB_ID=<uuid> \
  subterra-fenics \
  python3 -m src.mesh_runner --params /subterra/jobs/<uuid>/parameter.json
```

### Simulation (MPI-parallel)

```bash
docker run --rm \
  -v subterra_jobs_data:/subterra/jobs \
  -e JOB_ID=<uuid> \
  subterra-fenics \
  mpirun -np 4 python3 -m src.sim_runner --params /subterra/jobs/<uuid>/parameter.json
```

### Plot generation

```bash
docker run --rm \
  -v subterra_jobs_data:/subterra/jobs \
  -e JOB_ID=<uuid> \
  subterra-fenics \
  python3 -m src.plot_runner --job-dir /subterra/jobs/<uuid>
```

### Interactive shell

```bash
docker run --rm -it subterra-fenics /bin/bash
```

## Container Internals

- **Working directory:** `/subterra`
- **Entrypoint:** `docker/entrypoint.sh` – creates symlinks `/subterra/params` → job dir, `/subterra/results` → job results dir based on `JOB_ID`.
- **MPI:** MPICH (bundled with DOLFINx). Core count configurable via `SUBTERRA_MPI_CORES` env var (default: 4). Uses MUMPS for parallel LU factorisation.
- **Solver:** PETSc KSP (PREONLY + LU/MUMPS). Falls back to serial LU when running on a single rank.
