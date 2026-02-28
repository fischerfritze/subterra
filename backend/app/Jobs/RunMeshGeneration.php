<?php

namespace App\Jobs;

use App\Models\SimulationJob;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\File;
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

            // Append stdout/stderr to job.log
            $this->appendLog($job, "[MESH] stdout:\n" . $result->output());
            if ($result->errorOutput()) {
                $this->appendLog($job, "[MESH] stderr:\n" . $result->errorOutput());
            }

            if ($result->successful()) {
                $job->update([
                    'status'            => SimulationJob::STATUS_MESHED,
                    'mesh_completed_at' => now(),
                ]);
                Log::info("Mesh generation completed for job {$job->id}");

                // Generate mesh plot (non-blocking, errors are non-fatal)
                try {
                    $this->generateMeshPlot($job);
                } catch (\Throwable $e) {
                    Log::warning("Mesh plot generation failed for job {$job->id}: {$e->getMessage()}");
                    $this->appendLog($job, "[MESH-PLOT] error: " . $e->getMessage());
                }
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

        $containerName = "subterra-mesh-{$job->id}";
        Process::run("docker rm -f {$containerName} 2>/dev/null");

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

    private function appendLog(SimulationJob $job, string $text): void
    {
        $logFile = $job->work_dir . '/job.log';
        File::ensureDirectoryExists(dirname($logFile));
        File::append($logFile, $text . "\n");
    }

    private function generateMeshPlot(SimulationJob $job): void
    {
        $mode = config('subterra.runner_mode', 'docker');

        if ($mode === 'local') {
            $projectRoot = config('subterra.project_root');
            $paramFile   = $job->parameterFilePath();
            $result = Process::timeout(120)
                ->path($projectRoot)
                ->run(implode(' ', [
                    'python3', '-m', 'src.mesh_plot_runner',
                    '--params', escapeshellarg($paramFile),
                ]));
        } else {
            $image  = config('subterra.fenics_container', 'subterra-fenics');
            $volume = config('subterra.docker_jobs_volume', 'subterra_jobs_data');
            $jobId  = $job->id;
            $containerName = "subterra-meshplot-{$jobId}";

            Process::run("docker rm -f {$containerName} 2>/dev/null");

            $result = Process::timeout(120)->run(implode(' ', [
                'docker', 'run', '--rm',
                '--name', $containerName,
                '-v', "{$volume}:/subterra/jobs",
                '-e', "JOB_ID={$jobId}",
                $image,
                'python3', '-m', 'src.mesh_plot_runner',
                '--params', "/subterra/jobs/{$jobId}/parameter.json",
            ]));
        }

        $this->appendLog($job, "[MESH-PLOT] stdout:\n" . $result->output());
        if ($result->errorOutput()) {
            $this->appendLog($job, "[MESH-PLOT] stderr:\n" . $result->errorOutput());
        }

        if (!$result->successful()) {
            throw new \RuntimeException("Mesh plot process returned exit code " . $result->exitCode());
        }

        Log::info("Mesh plot generated for job {$job->id}");
    }
}
