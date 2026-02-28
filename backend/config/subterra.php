<?php

return [

    /*
    |--------------------------------------------------------------------------
    | FEniCS Docker Container
    |--------------------------------------------------------------------------
    |
    | The Docker image name used to run mesh generation and simulations.
    | This image must contain FEniCS, gmsh and the SubTerra Python code.
    |
    */
    'fenics_container' => env('SUBTERRA_FENICS_IMAGE', 'subterra-fenics'),

    /*
    |--------------------------------------------------------------------------
    | Docker Jobs Volume
    |--------------------------------------------------------------------------
    |
    | Name of the Docker volume that stores job work directories.
    | Both the backend container and spawned fenics containers mount this volume.
    | Must match the named volume in docker-compose.yml.
    |
    */
    'docker_jobs_volume' => env('SUBTERRA_DOCKER_JOBS_VOLUME', 'subterra_jobs_data'),

    /*
    |--------------------------------------------------------------------------
    | Runner Mode
    |--------------------------------------------------------------------------
    |
    | 'docker' = run mesh/simulation inside a Docker container (production).
    | 'local'  = run Python directly on the host (development).
    |
    */
    'runner_mode' => env('SUBTERRA_RUNNER_MODE', 'docker'),

    /*
    |--------------------------------------------------------------------------
    | Project Root (local mode)
    |--------------------------------------------------------------------------
    |
    | Absolute path to the SubTerra project root so mesh_runner / sim_runner
    | can be invoked with  python3 -m src.mesh_runner  from this directory.
    |
    */
    'project_root' => env('SUBTERRA_PROJECT_ROOT', base_path('..')),

    /*
    |--------------------------------------------------------------------------
    | Paths Configuration
    |--------------------------------------------------------------------------
    |
    | Paths used by the Python simulation code inside the Docker container.
    |
    */
    'container_work_mount' => '/subterra/work',

    /*
    |--------------------------------------------------------------------------
    | MPI Cores
    |--------------------------------------------------------------------------
    |
    | Number of MPI processes for parallel FEniCSx simulation.
    | Set to 1 for serial execution.
    |
    */
    'mpi_cores' => (int) env('SUBTERRA_MPI_CORES', 4),

];
