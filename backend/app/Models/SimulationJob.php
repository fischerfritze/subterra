<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Concerns\HasUuids;

class SimulationJob extends Model
{
    use HasFactory, HasUuids;

    protected $table = 'simulation_jobs';

    const STATUS_PENDING    = 'pending';
    const STATUS_MESHING    = 'meshing';
    const STATUS_MESHED     = 'meshed';
    const STATUS_SIMULATING = 'simulating';
    const STATUS_COMPLETED  = 'completed';
    const STATUS_FAILED     = 'failed';

    protected $fillable = [
        'status',
        'parameters',
        'parameters_si',
        'work_dir',
        'error_message',
        'mesh_started_at',
        'mesh_completed_at',
        'sim_started_at',
        'sim_completed_at',
    ];

    protected $casts = [
        'parameters'        => 'array',
        'parameters_si'     => 'array',
        'mesh_started_at'   => 'datetime',
        'mesh_completed_at' => 'datetime',
        'sim_started_at'    => 'datetime',
        'sim_completed_at'  => 'datetime',
    ];

    /**
     * Get the absolute path to this job's working directory.
     */
    public function getWorkDirAttribute($value): string
    {
        return $value ?? storage_path("app/jobs/{$this->id}");
    }

    /**
     * Path to the parameter.json inside the work dir.
     */
    public function parameterFilePath(): string
    {
        return $this->work_dir . '/parameter.json';
    }

    /**
     * Path to the parameter_si.json inside the work dir.
     */
    public function parameterSiFilePath(): string
    {
        return $this->work_dir . '/parameter_si.json';
    }

    /**
     * Path to the temp directory (mesh output).
     */
    public function tempDir(): string
    {
        return $this->work_dir . '/temp';
    }

    /**
     * Path to the results directory.
     */
    public function resultsDir(): string
    {
        return $this->work_dir . '/results';
    }

    /**
     * Check if mesh files exist.
     */
    public function hasMesh(): bool
    {
        return file_exists($this->tempDir() . '/temp_mesh.xml')
            && file_exists($this->tempDir() . '/locations.json');
    }

    /**
     * Get result files list.
     */
    public function resultFiles(): array
    {
        $dir = $this->resultsDir();
        if (!is_dir($dir)) {
            return [];
        }

        $files = [];
        foreach (glob($dir . '/**/*.h5') ?: [] as $f) {
            $files[] = basename($f);
        }
        // Also check subdirs
        foreach (glob($dir . '/*/*.h5') ?: [] as $f) {
            $files[] = str_replace($dir . '/', '', $f);
        }

        return array_unique($files);
    }

    /**
     * Read the progress.json written by the Python simulation/mesh code.
     *
     * Returns an array with keys: phase, current_step, total_steps, percent, message
     * or null when no progress file exists.
     */
    public function progress(): ?array
    {
        $file = $this->work_dir . '/progress.json';
        if (!file_exists($file)) {
            return null;
        }

        $data = @json_decode(@file_get_contents($file), true);
        if (!is_array($data)) {
            return null;
        }

        return [
            'phase'        => $data['phase'] ?? null,
            'current_step' => $data['current_step'] ?? 0,
            'total_steps'  => $data['total_steps'] ?? 0,
            'percent'      => $data['percent'] ?? 0,
            'message'      => $data['message'] ?? '',
        ];
    }
}
