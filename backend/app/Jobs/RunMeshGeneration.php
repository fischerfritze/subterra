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

            // Execute mesh runner
            $result = $this->runProcess($job);

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

    private function runProcess(SimulationJob $job): \Illuminate\Process\ProcessResult
    {
        $mode = config('subterra.runner_mode', 'docker');

        if ($mode === 'local') {
            return $this->runLocal($job);
        }

        return Process::timeout($this->timeout)->run(
            $this->buildDockerCommand($job)
        );
    }

    private function runLocal(SimulationJob $job): \Illuminate\Process\ProcessResult
    {
        $projectRoot = config('subterra.project_root');
        $paramFile   = $job->parameterFilePath();

        // Use env PATH=... prefix so the full parent environment is preserved
        // (FEniCS/DOLFIN needs MPI, LD_LIBRARY_PATH, etc.)
        return Process::timeout($this->timeout)
            ->path($projectRoot)
            ->run(implode(' ', [
                'env', 'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                'python3', '-m', 'src.mesh_runner',
                '--params', escapeshellarg($paramFile),
            ]));
    }

    private function buildDockerCommand(SimulationJob $job): string
    {
        $image  = config('subterra.fenics_container', 'subterra-fenics');
        $volume = config('subterra.docker_jobs_volume', 'subterra_jobs_data');
        $jobId  = $job->id;

        return implode(' ', [
            'docker', 'run', '--rm',
            '--name', "subterra-mesh-{$jobId}",
            '-v', "{$volume}:/subterra/jobs",
            '-e', "JOB_ID={$jobId}",
            $image,
            'python3', '-m', 'src.mesh_runner',
            '--params', "/subterra/jobs/{$jobId}/parameter.json",
        ]);
    }
}
