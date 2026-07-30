<template>
  <button
    class="primary-action-btn"
    :class="{ 'full-width': fullWidth, 'is-loading': loading }"
    :disabled="disabled || loading"
    @click="$emit('click')"
  >
    <span v-if="loading" class="btn-spinner" aria-hidden="true"></span>
    <span v-else-if="icon" class="btn-icon">{{ iconEmoji }}</span>
    <span class="btn-label">{{ label }}</span>
  </button>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  icon: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  fullWidth: { type: Boolean, default: false },
})

defineEmits(['click'])

const iconEmoji = computed(() => {
  if (props.icon === 'home') return '🏠'
  return props.icon
})
</script>

<style scoped>
.primary-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  min-height: var(--btn-min-height);
  padding: var(--space-md) var(--space-xl);
  background: var(--color-primary);
  color: white;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  border-radius: var(--radius-md);
  letter-spacing: 0.5px;
  transition: background var(--transition-fast), transform var(--transition-fast);
  border: none;
  cursor: pointer;
}

.primary-action-btn:active:not(:disabled) {
  background: var(--color-primary-hover);
  transform: scale(0.98);
}

.primary-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.primary-action-btn.full-width {
  width: 100%;
}

.primary-action-btn.is-loading {
  pointer-events: none;
}

.btn-spinner {
  width: 22px;
  height: 22px;
  border: 3px solid rgba(255, 255, 255, 0.35);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.btn-icon {
  font-size: 1.3rem;
}

.btn-label {
  text-transform: uppercase;
}
</style>
