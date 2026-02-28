<?php

namespace App\Jobs;

use App\Models\SimulationJob;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Process;

class RunMeshGeneration implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    /**
     * Max execution time in seconds (mesh generation can take minutes).
     */
    public int $timeout = 600;

    public int $tries = 1;

    public function __construct(
        public SimulationJob $simulationJob
    ) {}

    public function handle(): void
    {
        $job = $this->simulationJob;

        try {
            $job->update([
                'status'          => SimulationJob::STATUS_MESHING,
                'mesh_started_at' => now(),
            ]);

            Log::info("Mesh generation started for job {$job->id}");

            // Execute mesh runner inside the FEniCS container via docker exec
            // The work_dir is mounted into the container at /subterra/work
            $result = Process::timeout($this->timeout)->run(
                $this->buildDockerCommand($job)
            );

            if ($result->successful()) {
                $job->update([
                    'status'            => SimulationJob::STATUS_MESHED,
                    'mesh_completed_at' => now(),
                ]);
                Log::info("Mesh generation completed for job {$job->id}");
            } else {
                throw new \RuntimeException(
                    "Mesh generation failed:\n" . $result->errorOutput() . "\n" . $result->output()
                );
            }
        } catch (\Throwable $e) {
            $job->update([
                'status'        => SimulationJob::STATUS_FAILED,
                'error_message' => substr($e->getMessage(), 0, 5000),
            ]);
            Log::error("Mesh generation failed for job {$job->id}: {$e->getMessage()}");
            throw $e;
        }
    }

    private function buildDockerCommand(SimulationJob $job): string
    {
        $workDir = $job->work_dir;
        $image = config('subterra.fenics_container', 'subterra-fenics');

        // Mount the job's work directory into the FEniCS container
        // Inside the container, entrypoint.sh symlinks /subterra/params -> /subterra/work
        return implode(' ', [
            'docker', 'run', '--rm',
            '--name', "subterra-mesh-{$job->id}",
            '-v', "{$workDir}:/subterra/work",
            $image,
            'python3', '-m', 'src.mesh_runner',
            '--params', '/subterra/work/parameter.json',
        ]);
    }
}
