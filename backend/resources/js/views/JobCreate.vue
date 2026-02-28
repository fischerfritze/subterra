<template>
  <div>
    <div class="page-header">
      <h1>Neue Simulation</h1>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="success" class="alert alert-success">{{ success }}</div>

    <form @submit.prevent="submit">
      <!-- Mesh Mode -->
      <div class="card">
        <h2>Konfiguration</h2>
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">Anordnung</label>
            <select v-model="form.meshMode[0]" class="form-select">
              <option value="hexa">Hexagonal</option>
              <option value="square">Quadratisch</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Ringe</label>
            <input v-model.number="form.meshMode[1]" type="number" min="1" max="10" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">Konvektion</label>
            <select v-model="form.enableConvection" class="form-select">
              <option :value="true">Aktiviert</option>
              <option :value="false">Deaktiviert</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Mesh -->
      <div class="card">
        <h2>Mesh</h2>
        <div class="form-grid">
          <ValueUnit label="Mesh-Faktor" v-model="form.mesh.meshFactor" />
          <ValueUnit label="Mesh fein" v-model="form.mesh.meshFine" />
          <ValueUnit label="Bohrloch-Abstand" v-model="form.mesh.boreholeDistance" />
          <ValueUnit label="X-Länge" v-model="form.mesh.xLength" />
          <ValueUnit label="Y-Länge" v-model="form.mesh.yLength" />
          <ValueUnit label="X-Zentrum" v-model="form.mesh.xCenter" />
          <ValueUnit label="Y-Zentrum" v-model="form.mesh.yCenter" />
        </div>
      </div>

      <!-- Time -->
      <div class="card">
        <h2>Zeit</h2>
        <div class="form-grid">
          <ValueUnit label="Zeitschritt" v-model="form.time.timeStepHours" />
          <ValueUnit label="Simulationsjahre" v-model="form.time.simulationYears" />
        </div>
      </div>

      <!-- Ground -->
      <div class="card">
        <h2>Untergrund</h2>
        <div class="form-grid">
          <ValueUnit label="Modelltyp" v-model="form.ground.modelType" />
          <ValueUnit label="Wärmekapazitätsdichte" v-model="form.ground.heatCapacityDensity" />
          <ValueUnit label="Wärmeleitfähigkeit" v-model="form.ground.thermalConductivity" />
          <ValueUnit label="Porosität" v-model="form.ground.porosity" />
          <ValueUnit label="Temperatur" v-model="form.ground.temperature" />
        </div>
      </div>

      <!-- Groundwater -->
      <div class="card">
        <h2>Grundwasser</h2>
        <div class="form-grid">
          <ValueUnit label="Dichte" v-model="form.groundwater.density" />
          <ValueUnit label="Spez. Wärmekapazität" v-model="form.groundwater.specificHeat" />
          <ValueUnit label="Wärmeleitfähigkeit" v-model="form.groundwater.thermalConductivity" />
          <ValueUnit label="Geschwindigkeit X" v-model="form.groundwater.velocityX" />
          <ValueUnit label="Geschwindigkeit Y" v-model="form.groundwater.velocityY" />
        </div>
      </div>

      <!-- Air -->
      <div class="card">
        <h2>Luft</h2>
        <div class="form-grid">
          <ValueUnit label="Wärmekapazitätsdichte" v-model="form.air.heatCapacityDensity" />
          <ValueUnit label="Wärmeleitfähigkeit" v-model="form.air.thermalConductivity" />
        </div>
      </div>

      <!-- Temperature -->
      <div class="card">
        <h2>Temperatur</h2>
        <div class="form-grid">
          <ValueUnit label="Absoluttemperatur" v-model="form.temperatureAbsolute" />
          <ValueUnit label="Heißtemperatur" v-model="form.temperatureHot" />
        </div>
      </div>

      <!-- Power -->
      <div class="card">
        <h2>Leistung</h2>
        <div class="form-grid">
          <ValueUnit label="Koeffizient A" v-model="form.power.coefficientA" />
          <ValueUnit label="Koeffizient B" v-model="form.power.coefficientB" />
          <ValueUnit label="Rohr-Radius" v-model="form.power.pipeRadius" />
          <ValueUnit label="Wirkungsgrad" v-model="form.power.efficiency" />
        </div>
      </div>

      <!-- Actions -->
      <div class="actions">
        <button type="submit" class="btn btn-primary" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          Job erstellen &amp; starten
        </button>
        <button type="button" class="btn" @click="resetForm" style="background: var(--border);">
          Zurücksetzen
        </button>
      </div>
    </form>
  </div>
</template>

<script>
import api from '@/services/api.js';
import ValueUnit from '@/components/ValueUnit.vue';

const DEFAULT_PARAMS = {
  meshMode: ['hexa', 2],
  enableConvection: true,
  temperatureAbsolute: { value: 273.15, unit: 'K' },
  temperatureHot: { value: 40, unit: '°C' },
  mesh: {
    meshFactor: { value: 1, unit: 'm' },
    meshFine: { value: 0.25, unit: 'm' },
    boreholeDistance: { value: 5, unit: 'm' },
    xLength: { value: 400, unit: 'm' },
    yLength: { value: 200, unit: 'm' },
    xCenter: { value: -100, unit: 'm' },
    yCenter: { value: 0, unit: 'm' },
  },
  time: {
    timeStepHours: { value: 24, unit: 'h' },
    simulationYears: { value: 5, unit: 'year' },
  },
  ground: {
    modelType: { value: 1, unit: '1' },
    heatCapacityDensity: { value: 2.0, unit: 'MJ/m³/K' },
    thermalConductivity: { value: 2.0, unit: 'W/m/K' },
    porosity: { value: 0.2, unit: '1' },
    temperature: { value: 12, unit: '°C' },
  },
  groundwater: {
    density: { value: 997, unit: 'kg/m³' },
    specificHeat: { value: 4190, unit: 'J/kg/K' },
    thermalConductivity: { value: 0.598, unit: 'W/m/K' },
    velocityX: { value: 2, unit: 'cm/day' },
    velocityY: { value: 0, unit: 'cm/day' },
  },
  air: {
    heatCapacityDensity: { value: 1.2, unit: 'kJ/m³/K' },
    thermalConductivity: { value: 0.02, unit: 'W/m/K' },
  },
  power: {
    coefficientA: { value: 5.5, unit: 'W/m' },
    coefficientB: { value: 50, unit: 'W/m' },
    pipeRadius: { value: 0.09, unit: 'm' },
    efficiency: { value: 0.6, unit: '1' },
  },
};

export default {
  name: 'JobCreate',
  components: { ValueUnit },

  data() {
    return {
      form: JSON.parse(JSON.stringify(DEFAULT_PARAMS)),
      loading: false,
      error: null,
      success: null,
    };
  },

  methods: {
    async submit() {
      this.error = null;
      this.success = null;
      this.loading = true;

      try {
        // Create job
        const { data } = await api.createJob(this.form);
        const jobId = data.id;

        // Immediately dispatch mesh + simulation (chained)
        await api.startRun(jobId);

        this.success = `Job ${jobId} erstellt und gestartet.`;
        this.$router.push({ name: 'job-detail', params: { id: jobId } });
      } catch (err) {
        if (err.response?.data?.errors) {
          const msgs = Object.values(err.response.data.errors).flat();
          this.error = msgs.join(' | ');
        } else if (err.response?.data?.message) {
          this.error = err.response.data.message;
        } else {
          this.error = err.message;
        }
      } finally {
        this.loading = false;
      }
    },

    resetForm() {
      this.form = JSON.parse(JSON.stringify(DEFAULT_PARAMS));
      this.error = null;
      this.success = null;
    },
  },
};
</script>
