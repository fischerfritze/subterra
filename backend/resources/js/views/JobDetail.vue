<template>
  <div>
    <div v-if="loading" style="text-align: center; padding: 2rem;">
      <span class="spinner"></span> Lade...
    </div>

    <template v-else-if="job">
      <div class="page-header">
        <h1>Simulation {{ job.id.substring(0, 8) }}...</h1>
        <div style="display: flex; gap: 0.5rem;">
          <router-link to="/" class="btn">Zurück</router-link>
          <button v-if="canDelete" class="btn btn-danger" @click="onDelete">Löschen</button>
        </div>
      </div>

      <!-- Status card -->
      <div class="card">
        <h2>Status</h2>
        <div style="margin-bottom: 1rem;">
          <span :class="'badge badge-' + job.status" style="font-size: 1rem; padding: .4rem .8rem;">
            {{ job.status }}
          </span>
        </div>
        <div v-if="job.error_message" class="alert alert-error" style="margin-top: .5rem;">
          {{ job.error_message }}
        </div>
        <table class="detail-table">
          <tr><td>Erstellt</td><td>{{ formatDate(job.created_at) }}</td></tr>
          <tr v-if="job.mesh_started_at"><td>Mesh gestartet</td><td>{{ formatDate(job.mesh_started_at) }}</td></tr>
          <tr v-if="job.mesh_completed_at"><td>Mesh fertig</td><td>{{ formatDate(job.mesh_completed_at) }}</td></tr>
          <tr v-if="job.sim_started_at"><td>Simulation gestartet</td><td>{{ formatDate(job.sim_started_at) }}</td></tr>
          <tr v-if="job.sim_completed_at"><td>Simulation fertig</td><td>{{ formatDate(job.sim_completed_at) }}</td></tr>
        </table>
      </div>

      <!-- Actions -->
      <div class="card" v-if="showActions">
        <h2>Aktionen</h2>
        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
          <button v-if="canRunAll" class="btn btn-primary" @click="onRun" :disabled="busy">
            Komplett starten
          </button>
          <button v-if="canMesh" class="btn" @click="onMesh" :disabled="busy">
            Nur Mesh generieren
          </button>
          <button v-if="canSimulate" class="btn" @click="onSimulate" :disabled="busy">
            Simulation starten
          </button>
          <span v-if="busy" class="spinner" style="margin-left: .5rem;"></span>
        </div>
      </div>

      <!-- Results -->
      <div class="card" v-if="job.result_files && job.result_files.length">
        <h2>Ergebnisse</h2>
        <ul style="list-style: none; padding: 0;">
          <li v-for="file in job.result_files" :key="file" style="margin: .5rem 0;">
            <a :href="resultUrl(file)" target="_blank" class="btn btn-sm">
              ⬇ {{ file }}
            </a>
          </li>
        </ul>
      </div>

      <!-- Parameters -->
      <div class="card">
        <h2>Parameter</h2>
        <pre class="param-json">{{ JSON.stringify(job.parameters, null, 2) }}</pre>
      </div>
    </template>

    <div v-else class="card">
      <p>Job nicht gefunden.</p>
      <router-link to="/" class="btn" style="margin-top: 1rem;">Zurück zur Übersicht</router-link>
    </div>
  </div>
</template>

<script>
import api from '@/services/api.js';

export default {
  name: 'JobDetail',

  data() {
    return {
      job: null,
      loading: true,
      busy: false,
      pollTimer: null,
    };
  },

  computed: {
    canRunAll() {
      return ['pending', 'failed'].includes(this.job?.status);
    },
    canMesh() {
      return ['pending', 'failed'].includes(this.job?.status);
    },
    canSimulate() {
      return this.job?.status === 'meshed';
    },
    canDelete() {
      return ['pending', 'completed', 'failed'].includes(this.job?.status);
    },
    showActions() {
      return this.canRunAll || this.canMesh || this.canSimulate;
    },
    isRunning() {
      return ['meshing', 'simulating'].includes(this.job?.status);
    },
  },

  async mounted() {
    await this.fetchJob();
    this.startPolling();
  },

  beforeUnmount() {
    this.stopPolling();
  },

  watch: {
    isRunning(val) {
      if (val) this.startPolling();
      else this.stopPolling();
    },
  },

  methods: {
    async fetchJob() {
      try {
        const { data } = await api.getJob(this.$route.params.id);
        this.job = data;
      } catch (err) {
        console.error('Failed to fetch job:', err);
        this.job = null;
      } finally {
        this.loading = false;
      }
    },

    startPolling() {
      if (this.pollTimer) return;
      if (this.isRunning) {
        this.pollTimer = setInterval(this.fetchJob, 3000);
      }
    },

    stopPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer);
        this.pollTimer = null;
      }
    },

    async onRun() {
      this.busy = true;
      try {
        await api.startRun(this.job.id);
        await this.fetchJob();
      } catch (err) {
        alert(err.response?.data?.error || 'Fehler beim Starten.');
      } finally {
        this.busy = false;
      }
    },

    async onMesh() {
      this.busy = true;
      try {
        await api.startMesh(this.job.id);
        await this.fetchJob();
      } catch (err) {
        alert(err.response?.data?.error || 'Fehler beim Mesh-Start.');
      } finally {
        this.busy = false;
      }
    },

    async onSimulate() {
      this.busy = true;
      try {
        await api.startSimulation(this.job.id);
        await this.fetchJob();
      } catch (err) {
        alert(err.response?.data?.error || 'Fehler beim Simulations-Start.');
      } finally {
        this.busy = false;
      }
    },

    async onDelete() {
      if (!confirm('Simulation wirklich löschen?')) return;
      try {
        await api.deleteJob(this.job.id);
        this.$router.push('/');
      } catch (err) {
        alert('Löschen fehlgeschlagen.');
      }
    },

    resultUrl(filename) {
      return api.getResultUrl(this.job.id, filename);
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

<style scoped>
.detail-table {
  border-collapse: collapse;
  margin-top: 0.5rem;
}
.detail-table td {
  padding: 0.25rem 1rem 0.25rem 0;
  vertical-align: top;
}
.detail-table td:first-child {
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
}
.param-json {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem;
  overflow-x: auto;
  font-size: 0.85rem;
  max-height: 400px;
  overflow-y: auto;
}
</style>
