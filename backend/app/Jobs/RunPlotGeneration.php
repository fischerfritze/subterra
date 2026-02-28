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

class RunPlotGeneration implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public int $timeout = 600; // 10 minutes
    public int $tries = 1;

    public function __construct(
        public SimulationJob $simulationJob
    ) {}

    public function handle(): void
    {
        $job = $this->simulationJob;

        try {
            Log::info("Plot generation started for job {$job->id}");

            $result = $this->runProcess($job);

            // Append stdout/stderr to job.log
            $this->appendLog($job, "[PLOT] stdout:\n" . $result->output());
            if ($result->errorOutput()) {
                $this->appendLog($job, "[PLOT] stderr:\n" . $result->errorOutput());
            }

            if ($result->successful()) {
                Log::info("Plot generation completed for job {$job->id}");
            } else {
                Log::warning(
                    "Plot generation had issues for job {$job->id}: "
                    . $result->errorOutput()
                );
            }
        } catch (\Throwable $e) {
            // Plot generation failure should not fail the overall job
            Log::error("Plot generation failed for job {$job->id}: {$e->getMessage()}");
        }
    }

    private function runProcess(SimulationJob $job): \Illuminate\Process\ProcessResult
    {
        $mode = config('subterra.runner_mode', 'docker');
        if ($mode === 'local') {
            return $this->runLocal($job);
        }
        $containerName = "subterra-plot-{$job->id}";
        Process::run("docker rm -f {$containerName} 2>/dev/null");

        return Process::timeout($this->timeout)->run($this->buildDockerCommand($job));
    }

    private function runLocal(SimulationJob $job): \Illuminate\Process\ProcessResult
    {
        $projectRoot = config('subterra.project_root');
        $paramFile   = $job->parameterFilePath();

        return Process::timeout($this->timeout)
            ->path($projectRoot)
            ->run(implode(' ', [
                'env', 'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                'python3', '-m', 'src.plot_runner',
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
            '--name', "subterra-plot-{$jobId}",
            '-v', "{$volume}:/subterra/jobs",
            '-e', "JOB_ID={$jobId}",
            $image,
            'python3', '-m', 'src.plot_runner',
            '--params', "/subterra/jobs/{$jobId}/parameter.json",
        ]);
    }

    private function appendLog(SimulationJob $job, string $text): void
    {
        $logFile = $job->work_dir . '/job.log';
        File::ensureDirectoryExists(dirname($logFile));
        File::append($logFile, $text . "\n");
    }
}
