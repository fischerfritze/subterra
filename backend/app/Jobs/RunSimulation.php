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

class RunSimulation implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    /**
     * Max execution time in seconds (long-running simulations).
     */
    public int $timeout = 7200; // 2 hours

    public int $tries = 1;

    public function __construct(
        public SimulationJob $simulationJob
    ) {}

    public function handle(): void
    {
        $job = $this->simulationJob;

        try {
            // Verify mesh exists
            if (!$job->hasMesh()) {
                throw new \RuntimeException(
                    "Mesh files not found. Run mesh generation first."
                );
            }

            $job->update([
                'status'         => SimulationJob::STATUS_SIMULATING,
                'sim_started_at' => now(),
            ]);

            Log::info("Simulation started for job {$job->id}");

            $result = Process::timeout($this->timeout)->run(
                $this->buildDockerCommand($job)
            );

            if ($result->successful()) {
                $job->update([
                    'status'           => SimulationJob::STATUS_COMPLETED,
                    'sim_completed_at' => now(),
                ]);
                Log::info("Simulation completed for job {$job->id}");
            } else {
                throw new \RuntimeException(
                    "Simulation failed:\n" . $result->errorOutput() . "\n" . $result->output()
                );
            }
        } catch (\Throwable $e) {
            $job->update([
                'status'        => SimulationJob::STATUS_FAILED,
                'error_message' => substr($e->getMessage(), 0, 5000),
            ]);
            Log::error("Simulation failed for job {$job->id}: {$e->getMessage()}");
            throw $e;
        }
    }

    private function buildDockerCommand(SimulationJob $job): string
    {
        $workDir = $job->work_dir;
        $image = config('subterra.fenics_container', 'subterra-fenics');

        return implode(' ', [
            'docker', 'run', '--rm',
            '--name', "subterra-sim-{$job->id}",
            '-v', "{$workDir}:/subterra/work",
            $image,
            'python3', '-m', 'src.sim_runner',
            '--params', '/subterra/work/parameter.json',
        ]);
    }
}
