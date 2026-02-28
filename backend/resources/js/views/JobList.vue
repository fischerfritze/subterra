<template>
  <div>
    <div class="page-header">
      <h1>Simulationen</h1>
      <router-link to="/new" class="btn btn-primary">+ Neue Simulation</router-link>
    </div>

    <div v-if="loading" style="text-align: center; padding: 2rem;">
      <span class="spinner"></span> Lade...
    </div>

    <div v-else-if="jobs.length === 0" class="card empty">
      <p>Noch keine Simulationen vorhanden.</p>
      <router-link to="/new" class="btn btn-primary" style="margin-top: 1rem;">
        Erste Simulation erstellen
      </router-link>
    </div>

    <div v-else class="card" style="padding: 0; overflow: hidden;">
      <table class="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Status</th>
            <th>Fortschritt</th>
            <th>Erstellt</th>
            <th>Mesh</th>
            <th>Simulation</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="job in jobs" :key="job.id">
            <td>
              <router-link :to="{ name: 'job-detail', params: { id: job.id } }"
                style="color: var(--primary); text-decoration: none;">
                {{ job.id.substring(0, 8) }}...
              </router-link>
            </td>
            <td>
              <span :class="'badge badge-' + job.status">{{ job.status }}</span>
            </td>
            <td>
              <ProgressBar :progress="job.progress" :status="job.status" />
            </td>
            <td>{{ formatDate(job.created_at) }}</td>
            <td>
              <template v-if="job.mesh_completed_at">
                {{ formatDate(job.mesh_completed_at) }}
                <span class="elapsed" v-if="meshElapsed(job)"> ({{ meshElapsed(job) }})</span>
              </template>
              <template v-else-if="job.mesh_started_at">
                <span class="elapsed running">läuft {{ elapsedSince(job.mesh_started_at) }}</span>
              </template>
              <template v-else>—</template>
            </td>
            <td>
              <template v-if="job.sim_completed_at">
                {{ formatDate(job.sim_completed_at) }}
                <span class="elapsed" v-if="simElapsed(job)"> ({{ simElapsed(job) }})</span>
              </template>
              <template v-else-if="job.sim_started_at">
                <span class="elapsed running">läuft {{ elapsedSince(job.sim_started_at) }}</span>
              </template>
              <template v-else>—</template>
            </td>
            <td>
              <router-link :to="{ name: 'job-detail', params: { id: job.id } }" class="btn btn-sm btn-primary">
                Details
              </router-link>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import api from '@/services/api.js';
import ProgressBar from '@/components/ProgressBar.vue';

export default {
  name: 'JobList',

  components: { ProgressBar },

  data() {
    return {
      jobs: [],
      loading: true,
      pollTimer: null,
    };
  },

  async mounted() {
    await this.fetchJobs();
    // Poll every 5s for status updates
    this.pollTimer = setInterval(this.fetchJobs, 5000);
  },

  beforeUnmount() {
    if (this.pollTimer) clearInterval(this.pollTimer);
  },

  methods: {
    async fetchJobs() {
      try {
        const { data } = await api.listJobs(50);
        this.jobs = data;
      } catch (err) {
        console.error('Failed to fetch jobs:', err);
      } finally {
        this.loading = false;
      }
    },

    formatDate(dateStr) {
      if (!dateStr) return '';
      const d = new Date(dateStr);
      return d.toLocaleDateString('de-DE', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      });
    },

    /**
     * Format a duration in seconds to a human-readable string.
     */
    formatDuration(seconds) {
      if (seconds < 0) return '';
      seconds = Math.round(seconds);
      if (seconds < 60) return seconds + 's';
      const min = Math.floor(seconds / 60);
      const sec = seconds % 60;
      if (min < 60) return sec > 0 ? min + 'min ' + sec + 's' : min + 'min';
      const h = Math.floor(min / 60);
      const m = min % 60;
      return m > 0 ? h + 'h ' + m + 'min' : h + 'h';
    },

    /**
     * Elapsed time for mesh: mesh_completed_at - mesh_started_at (or created_at fallback).
     */
    meshElapsed(job) {
      if (!job.mesh_completed_at) return '';
      const start = job.mesh_started_at || job.created_at;
      if (!start) return '';
      const sec = (new Date(job.mesh_completed_at) - new Date(start)) / 1000;
      return sec >= 0 ? this.formatDuration(sec) : '';
    },

    /**
     * Elapsed time for simulation: sim_completed_at - sim_started_at.
     */
    simElapsed(job) {
      if (!job.sim_completed_at || !job.sim_started_at) return '';
      const sec = (new Date(job.sim_completed_at) - new Date(job.sim_started_at)) / 1000;
      return sec >= 0 ? this.formatDuration(sec) : '';
    },

    /**
     * Elapsed time since a given timestamp until now.
     */
    elapsedSince(dateStr) {
      if (!dateStr) return '';
      const sec = (Date.now() - new Date(dateStr)) / 1000;
      return sec >= 0 ? this.formatDuration(sec) : '';
    },
  },
};
</script>

<style scoped>
.elapsed {
  font-size: 0.8em;
  color: var(--text-muted, #64748b);
  white-space: nowrap;
}
.elapsed.running {
  font-style: italic;
  color: var(--primary, #3b82f6);
}
</style>
