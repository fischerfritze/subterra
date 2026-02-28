<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('simulation_jobs', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->string('status', 20)->default('pending')->index();
            $table->json('parameters');
            $table->json('parameters_si')->nullable();
            $table->string('work_dir')->nullable();
            $table->text('error_message')->nullable();
            $table->timestamp('mesh_started_at')->nullable();
            $table->timestamp('mesh_completed_at')->nullable();
            $table->timestamp('sim_started_at')->nullable();
            $table->timestamp('sim_completed_at')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('simulation_jobs');
    }
};
