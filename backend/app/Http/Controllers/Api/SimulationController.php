<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Requests\StoreParameterRequest;
use App\Jobs\RunMeshGeneration;
use App\Jobs\RunSimulation;
use App\Models\SimulationJob;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Storage;

class SimulationController extends Controller
{
    /**
     * POST /api/jobs
     * Create a new simulation job with validated parameters.
     */
    public function store(StoreParameterRequest $request): JsonResponse
    {
        $parameters = $request->toParameterJson();

        $job = SimulationJob::create([
            'status'     => SimulationJob::STATUS_PENDING,
            'parameters' => $parameters,
        ]);

        // Create work directory and write parameter.json
        $workDir = $job->work_dir;
        File::ensureDirectoryExists($workDir . '/temp', 0755, true);
        File::ensureDirectoryExists($workDir . '/results', 0755, true);
        File::put(
            $job->parameterFilePath(),
            json_encode($parameters, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)
        );

        $job->update(['work_dir' => $workDir]);

        return response()->json([
            'id'      => $job->id,
            'status'  => $job->status,
            'message' => 'Job created. Use POST /api/jobs/{id}/mesh to start mesh generation.',
        ], 201);
    }

    /**
     * GET /api/jobs
     * List all simulation jobs.
     */
    public function index(Request $request): JsonResponse
    {
        $jobs = SimulationJob::orderByDesc('created_at')
            ->limit($request->integer('limit', 20))
            ->get();

        $result = $jobs->map(function (SimulationJob $job) {
            $data = [
                'id'                => $job->id,
                'status'            => $job->status,
                'created_at'        => $job->created_at,
                'mesh_started_at'   => $job->mesh_started_at,
                'mesh_completed_at' => $job->mesh_completed_at,
                'sim_started_at'    => $job->sim_started_at,
                'sim_completed_at'  => $job->sim_completed_at,
            ];

            // Include progress for running jobs
            if (in_array($job->status, ['meshing', 'simulating'])) {
                $data['progress'] = $job->progress();
            }

            return $data;
        });

        return response()->json($result);
    }

    /**
     * GET /api/jobs/{id}
     * Get detailed status of a simulation job.
     */
    public function show(SimulationJob $job): JsonResponse
    {
        return response()->json([
            'id'                 => $job->id,
            'status'             => $job->status,
            'parameters'         => $job->parameters,
            'has_mesh'           => $job->hasMesh(),
            'result_files'       => $job->resultFiles(),
            'progress'           => $job->progress(),
            'error_message'      => $job->error_message,
            'mesh_started_at'    => $job->mesh_started_at,
            'mesh_completed_at'  => $job->mesh_completed_at,
            'sim_started_at'     => $job->sim_started_at,
            'sim_completed_at'   => $job->sim_completed_at,
            'created_at'         => $job->created_at,
        ]);
    }

    /**
     * POST /api/jobs/{id}/mesh
     * Dispatch mesh generation for a job.
     */
    public function mesh(SimulationJob $job): JsonResponse
    {
        if (!in_array($job->status, [SimulationJob::STATUS_PENDING, SimulationJob::STATUS_FAILED])) {
            return response()->json([
                'error' => "Cannot start mesh generation. Current status: {$job->status}",
            ], 422);
        }

        RunMeshGeneration::dispatch($job);

        return response()->json([
            'id'      => $job->id,
            'status'  => 'meshing',
            'message' => 'Mesh generation queued.',
        ]);
    }

    /**
     * POST /api/jobs/{id}/simulate
     * Dispatch simulation for a job (requires mesh to be generated first).
     */
    public function simulate(SimulationJob $job): JsonResponse
    {
        if ($job->status !== SimulationJob::STATUS_MESHED) {
            return response()->json([
                'error' => "Cannot start simulation. Current status: {$job->status}. "
                         . "Mesh must be generated first (status = 'meshed').",
            ], 422);
        }

        if (!$job->hasMesh()) {
            return response()->json([
                'error' => 'Mesh files not found in work directory.',
            ], 422);
        }

        RunSimulation::dispatch($job);

        return response()->json([
            'id'      => $job->id,
            'status'  => 'simulating',
            'message' => 'Simulation queued.',
        ]);
    }

    /**
     * POST /api/jobs/{id}/run
     * Convenience: dispatch mesh generation, then chain simulation automatically.
     */
    public function run(SimulationJob $job): JsonResponse
    {
        if (!in_array($job->status, [SimulationJob::STATUS_PENDING, SimulationJob::STATUS_FAILED])) {
            return response()->json([
                'error' => "Cannot start. Current status: {$job->status}",
            ], 422);
        }

        // Chain: mesh first, then simulation
        RunMeshGeneration::withChain([
            new RunSimulation($job),
        ])->dispatch($job);

        return response()->json([
            'id'      => $job->id,
            'status'  => 'meshing',
            'message' => 'Mesh generation + simulation queued (chained).',
        ]);
    }

    /**
     * GET /api/jobs/{id}/results/{filename}
     * Download a result file.
     */
    public function downloadResult(SimulationJob $job, string $filename): mixed
    {
        if ($job->status !== SimulationJob::STATUS_COMPLETED) {
            return response()->json([
                'error' => 'Simulation not completed yet.',
            ], 422);
        }

        // Search for the file in results directory (including subdirs)
        $resultsDir = $job->resultsDir();
        $found = null;
        foreach (glob($resultsDir . '/*/' . $filename) ?: [] as $f) {
            $found = $f;
            break;
        }
        if (!$found && file_exists($resultsDir . '/' . $filename)) {
            $found = $resultsDir . '/' . $filename;
        }

        if (!$found) {
            return response()->json(['error' => 'File not found.'], 404);
        }

        return response()->download($found);
    }

    /**
     * POST /api/params/validate
     * Validate parameters without creating a job.
     */
    public function validateParams(StoreParameterRequest $request): JsonResponse
    {
        return response()->json([
            'valid'      => true,
            'parameters' => $request->toParameterJson(),
        ]);
    }

    /**
     * DELETE /api/jobs/{id}
     * Delete a job and its work directory.
     */
    public function destroy(SimulationJob $job): JsonResponse
    {
        if (in_array($job->status, [SimulationJob::STATUS_MESHING, SimulationJob::STATUS_SIMULATING])) {
            return response()->json([
                'error' => 'Cannot delete a running job.',
            ], 422);
        }

        // Clean up work directory
        if (is_dir($job->work_dir)) {
            File::deleteDirectory($job->work_dir);
        }

        $job->delete();

        return response()->json(['message' => 'Job deleted.']);
    }
}
