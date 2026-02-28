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

        <!-- Progress bar -->
        <div v-if="showProgress" style="margin-bottom: 1rem;">
          <ProgressBar :progress="job.progress" :status="job.status" />
          <div v-if="job.progress && job.progress.message" class="progress-message">
            {{ job.progress.message }}
          </div>
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

      <!-- Console output -->
      <div class="card" v-if="showConsole">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
          <h2 style="margin-bottom: 0;">Konsole</h2>
          <div style="display: flex; gap: 0.5rem; align-items: center;">
            <label style="font-size: 0.75rem; color: var(--text-muted); display: flex; align-items: center; gap: 0.3rem;">
              <input type="checkbox" v-model="autoScrollLog" /> Auto-Scroll
            </label>
            <button class="btn btn-sm" @click="fetchLog" :disabled="logLoading">
              {{ logLoading ? '...' : '↻ Aktualisieren' }}
            </button>
          </div>
        </div>
        <div class="console" ref="consoleEl">
          <pre class="console-text">{{ logText || 'Warte auf Ausgabe...' }}</pre>
        </div>
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

      <!-- Contour Plots -->
      <div class="card" v-if="job.status === 'completed'">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
          <h2 style="margin-bottom: 0;">Contour Plots</h2>
          <button v-if="!hasPlots" class="btn btn-primary btn-sm" @click="onGeneratePlots" :disabled="plotBusy">
            <span v-if="plotBusy" class="spinner" style="margin-right: .3rem;"></span>
            Plots generieren
          </button>
          <button v-else class="btn btn-sm" @click="onRegeneratePlots" :disabled="plotBusy">
            <span v-if="plotBusy" class="spinner" style="margin-right: .3rem;"></span>
            Plots neu generieren
          </button>
        </div>

        <div v-if="!hasPlots && !plotBusy" class="plot-empty">
          Noch keine Plots vorhanden. Klicke auf „Plots generieren" oder warte kurz —
          Plots werden nach der Simulation automatisch erstellt.
        </div>

        <div v-if="!hasPlots && plotBusy" style="text-align: center; padding: 1rem;">
          <span class="spinner"></span> Plots werden generiert...
        </div>

        <div v-if="hasPlots" class="plot-gallery">
          <div v-for="plot in job.plot_files" :key="plot" class="plot-item">
            <div class="plot-image-wrapper">
              <img
                :src="plotUrl(plot)"
                :alt="plot"
                class="plot-image"
                loading="lazy"
                @click="openPlotFullscreen(plot)"
              />
            </div>
            <div class="plot-actions">
              <span class="plot-filename">{{ plot }}</span>
              <a :href="plotDownloadUrl(plot)" class="btn btn-sm btn-primary" download>
                ⬇ PNG
              </a>
            </div>
          </div>
        </div>
      </div>

      <!-- Fullscreen plot overlay -->
      <div v-if="fullscreenPlot" class="plot-overlay" @click="fullscreenPlot = null">
        <div class="plot-overlay-content" @click.stop>
          <img :src="plotUrl(fullscreenPlot)" :alt="fullscreenPlot" class="plot-overlay-image" />
          <div class="plot-overlay-actions">
            <span>{{ fullscreenPlot }}</span>
            <a :href="plotDownloadUrl(fullscreenPlot)" class="btn btn-sm btn-primary" download>
              ⬇ PNG herunterladen
            </a>
            <button class="btn btn-sm" @click="fullscreenPlot = null">Schließen</button>
          </div>
        </div>
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
import ProgressBar from '@/components/ProgressBar.vue';

export default {
  name: 'JobDetail',

  components: { ProgressBar },

  data() {
    return {
      job: null,
      loading: true,
      busy: false,
      plotBusy: false,
      pollTimer: null,
      logPollTimer: null,
      plotPollTimer: null,
      fullscreenPlot: null,
      logText: '',
      logLoading: false,
      autoScrollLog: true,
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
    showProgress() {
      return ['meshing', 'meshed', 'simulating', 'completed'].includes(this.job?.status);
    },
    isRunning() {
      return ['meshing', 'simulating'].includes(this.job?.status);
    },
    hasPlots() {
      return this.job?.plot_files && this.job.plot_files.length > 0;
    },
    showConsole() {
      return this.job && this.job.status !== 'pending';
    },
    meshPlotUrl() {
      return this.job ? api.getMeshPlotUrl(this.job.id) : '';
    },
  },

  async mounted() {
    await this.fetchJob();
    await this.fetchLog();
    this.startPolling();
    this.startLogPolling();
  },

  beforeUnmount() {
    this.stopPolling();
    this.stopLogPolling();
    this.stopPlotPolling();
  },

  watch: {
    isRunning(val) {
      if (val) {
        this.startPolling();
        this.startLogPolling();
      } else {
        this.stopPolling();
        // Fetch log one last time after completion
        setTimeout(() => this.fetchLog(), 2000);
        setTimeout(() => this.stopLogPolling(), 5000);
      }
    },
    'job.status'(newStatus, oldStatus) {
      // When transitioning to completed, fetch log once more
      if (newStatus === 'completed' && oldStatus !== 'completed') {
        setTimeout(() => this.fetchLog(), 3000);
      }
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

    async fetchLog() {
      if (!this.job) return;
      this.logLoading = true;
      try {
        const { data } = await api.getJobLog(this.job.id);
        this.logText = data.log || '';
        this.$nextTick(() => {
          if (this.autoScrollLog && this.$refs.consoleEl) {
            this.$refs.consoleEl.scrollTop = this.$refs.consoleEl.scrollHeight;
          }
        });
      } catch (err) {
        // Ignore log fetch errors
      } finally {
        this.logLoading = false;
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

    startLogPolling() {
      if (this.logPollTimer) return;
      this.logPollTimer = setInterval(this.fetchLog, 4000);
    },

    stopLogPolling() {
      if (this.logPollTimer) {
        clearInterval(this.logPollTimer);
        this.logPollTimer = null;
      }
    },

    async onRun() {
      this.busy = true;
      this.logText = '';
      try {
        await api.startRun(this.job.id);
        await this.fetchJob();
        this.startLogPolling();
      } catch (err) {
        alert(err.response?.data?.error || 'Fehler beim Starten.');
      } finally {
        this.busy = false;
      }
    },

    async onMesh() {
      this.busy = true;
      this.logText = '';
      try {
        await api.startMesh(this.job.id);
        await this.fetchJob();
        this.startLogPolling();
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
        this.startLogPolling();
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

    plotUrl(filename) {
      return api.getPlotUrl(this.job.id, filename);
    },

    plotDownloadUrl(filename) {
      return api.getPlotDownloadUrl(this.job.id, filename);
    },

    openPlotFullscreen(filename) {
      this.fullscreenPlot = filename;
    },

    async onGeneratePlots() {
      this.plotBusy = true;
      try {
        await api.generatePlots(this.job.id);
        this.startPlotPolling();
      } catch (err) {
        alert(err.response?.data?.error || 'Fehler beim Plot-Start.');
        this.plotBusy = false;
      }
    },

    async onRegeneratePlots() {
      await this.onGeneratePlots();
    },

    startPlotPolling() {
      if (this.plotPollTimer) return;
      this.plotPollTimer = setInterval(async () => {
        await this.fetchJob();
        if (this.hasPlots) {
          this.stopPlotPolling();
          this.plotBusy = false;
        }
      }, 5000);
      setTimeout(() => {
        this.stopPlotPolling();
        this.plotBusy = false;
      }, 300000);
    },

    stopPlotPolling() {
      if (this.plotPollTimer) {
        clearInterval(this.plotPollTimer);
        this.plotPollTimer = null;
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
.progress-message {
  margin-top: 0.4rem;
  font-size: 0.8rem;
  color: var(--text-muted);
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

/* Plot gallery */
.plot-empty {
  text-align: center;
  padding: 1.5rem;
  color: var(--text-muted);
  font-size: 0.9rem;
}
.plot-gallery {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
}
.plot-item {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  background: #fafafa;
}
.plot-image-wrapper {
  padding: 0.5rem;
  text-align: center;
  background: white;
  cursor: pointer;
}
.plot-image {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  transition: transform 0.2s;
}
.plot-image:hover {
  transform: scale(1.01);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
.plot-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  border-top: 1px solid var(--border);
  background: var(--bg, #f5f5f5);
}
.plot-filename {
  font-size: 0.8rem;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Fullscreen overlay */
.plot-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}
.plot-overlay-content {
  max-width: 95vw;
  max-height: 95vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}
.plot-overlay-image {
  max-width: 100%;
  max-height: 80vh;
  border-radius: 8px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
}
.plot-overlay-actions {
  display: flex;
  gap: 1rem;
  align-items: center;
  color: white;
  font-size: 0.9rem;
}

/* Console */
.console {
  background: #1e1e1e;
  border: 1px solid #333;
  border-radius: var(--radius);
  max-height: 400px;
  min-height: 120px;
  overflow-y: auto;
  overflow-x: auto;
  scrollbar-color: #555 #1e1e1e;
}
.console-text {
  margin: 0;
  padding: 0.75rem 1rem;
  font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', 'Consolas', 'Monaco', monospace;
  font-size: 0.8rem;
  line-height: 1.5;
  color: #d4d4d4;
  white-space: pre-wrap;
  word-break: break-all;
}
.btn-sm {
  font-size: 0.75rem;
  padding: 0.25rem 0.6rem;
}

/* Mesh plot */
.mesh-plot-wrapper {
  text-align: center;
  padding: 0.5rem;
  background: white;
  border: 1px solid var(--border);
  border-radius: var(--radius);
}
.mesh-plot-image {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
}
</style>
