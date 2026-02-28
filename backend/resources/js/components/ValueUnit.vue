<template>
  <div class="form-group">
    <label class="form-label">{{ label }}</label>
    <div class="form-row">
      <input
        :value="modelValue.value"
        @input="$emit('update:modelValue', { ...modelValue, value: parseFloat($event.target.value) || 0 })"
        type="number"
        step="any"
        class="form-input"
      />
      <span style="font-size: 0.8rem; color: var(--text-muted); white-space: nowrap; padding: 0.5rem 0;">
        {{ modelValue.unit }}
      </span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ValueUnit',
  props: {
    label: { type: String, required: true },
    modelValue: { type: Object, required: true },
  },
  emits: ['update:modelValue'],
};
</script>
