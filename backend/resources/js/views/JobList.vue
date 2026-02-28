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
            <td>{{ formatDate(job.created_at) }}</td>
            <td>{{ job.mesh_completed_at ? formatDate(job.mesh_completed_at) : '—' }}</td>
            <td>{{ job.sim_completed_at ? formatDate(job.sim_completed_at) : '—' }}</td>
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

export default {
  name: 'JobList',

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
  },
};
</script>
