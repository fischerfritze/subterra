<?php

use App\Http\Controllers\Api\SimulationController;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| API Routes
|--------------------------------------------------------------------------
|
| SubTerra API endpoints for simulation job management.
| All routes are prefixed with /api automatically.
|
*/

// Parameter validation (no job creation)
Route::post('/params/validate', [SimulationController::class, 'validateParams']);

// Job CRUD
Route::get('/jobs',          [SimulationController::class, 'index']);
Route::post('/jobs',         [SimulationController::class, 'store']);
Route::get('/jobs/{job}',    [SimulationController::class, 'show']);
Route::delete('/jobs/{job}', [SimulationController::class, 'destroy']);

// Job actions
Route::post('/jobs/{job}/mesh',     [SimulationController::class, 'mesh']);
Route::post('/jobs/{job}/simulate', [SimulationController::class, 'simulate']);
Route::post('/jobs/{job}/run',      [SimulationController::class, 'run']);

// Result download
Route::get('/jobs/{job}/results/{filename}', [SimulationController::class, 'downloadResult'])
    ->where('filename', '.*');
