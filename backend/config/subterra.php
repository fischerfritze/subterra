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
    | Paths Configuration
    |--------------------------------------------------------------------------
    |
    | Paths used by the Python simulation code inside the Docker container.
    |
    */
    'container_work_mount' => '/subterra/work',

];
