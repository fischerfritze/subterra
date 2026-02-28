<template>
  <div class="progress-bar-wrapper" :title="tooltip">
    <div class="progress-track">
      <div
        class="progress-fill"
        :class="phaseClass"
        :style="{ width: clampedPercent + '%' }"
      ></div>
    </div>
    <div class="progress-info">
      <span class="progress-label">{{ labelText }}</span>
      <span v-if="progress && progress.message" class="progress-message">{{ progress.message }}</span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ProgressBar',

  props: {
    /** Progress object from API: { phase, current_step, total_steps, percent, message } */
    progress: {
      type: Object,
      default: null,
    },
    /** Override status when no progress data (e.g., pending, meshing, completed) */
    status: {
      type: String,
      default: '',
    },
  },

  computed: {
    clampedPercent() {
      if (!this.progress) return this.fallbackPercent;
      return Math.min(100, Math.max(0, this.progress.percent || 0));
    },

    /** Round to nearest 5% for display */
    displayPercent() {
      const raw = Math.round(this.clampedPercent);
      return Math.round(raw / 5) * 5;
    },

    fallbackPercent() {
      switch (this.status) {
        case 'pending':     return 0;
        case 'meshing':     return 5;
        case 'meshed':      return 50;
        case 'simulating':  return 55;
        case 'completed':   return 100;
        case 'failed':      return 0;
        default:            return 0;
      }
    },

    phaseClass() {
      const phase = this.progress?.phase || this.status;
      return {
        'phase-mesh': phase === 'mesh' || this.status === 'meshing',
        'phase-simulation': phase === 'simulation' || this.status === 'simulating',
        'phase-completed': this.status === 'completed',
        'phase-failed': this.status === 'failed',
        'indeterminate': this.isIndeterminate,
      };
    },

    isIndeterminate() {
      return ['meshing', 'simulating'].includes(this.status) && !this.progress;
    },

    labelText() {
      if (this.status === 'completed') return '100%';
      if (this.status === 'failed') return 'Fehler';
      if (this.status === 'pending') return 'Wartend';
      if (this.status === 'meshed') return 'Mesh fertig';
      if (!this.progress) {
        if (this.status === 'meshing') return 'Mesh ' + this.fallbackPercent + '%';
        if (this.status === 'simulating') return 'Sim ' + this.fallbackPercent + '%';
        return '';
      }
      const phaseName = this.progress.phase === 'mesh' ? 'Mesh' : 'Sim';
      return phaseName + ' ' + this.displayPercent + '%';
    },

    tooltip() {
      if (!this.progress) return '';
      return this.progress.message || (this.progress.current_step + '/' + this.progress.total_steps);
    },
  },
};
</script>

<style scoped>
.progress-bar-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 80px;
}

.progress-track {
  width: 100%;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
  min-width: 0;
}

/* Phase colors */
.phase-mesh {
  background: linear-gradient(90deg, #f59e0b, #d97706);
}

.phase-simulation {
  background: linear-gradient(90deg, #3b82f6, #2563eb);
}

.phase-completed {
  background: linear-gradient(90deg, #22c55e, #16a34a);
}

.phase-failed {
  background: #ef4444;
  width: 100% !important;
  opacity: 0.3;
}

.indeterminate {
  width: 40% !important;
  animation: indeterminate 1.5s ease-in-out infinite;
}

@keyframes indeterminate {
  0%   { margin-left: 0;   width: 30%; }
  50%  { margin-left: 35%; width: 35%; }
  100% { margin-left: 0;   width: 30%; }
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.5rem;
  line-height: 1.2;
}

.progress-label {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text, #1e293b);
  white-space: nowrap;
}

.progress-message {
  font-size: 0.65rem;
  color: var(--text-muted, #64748b);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
