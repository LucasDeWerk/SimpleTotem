<template>
  <button
    class="payment-method-card"
    :class="{ active, unavailable: !available }"
    :disabled="!available"
    @click="$emit('click')"
  >
    <span class="pm-label">{{ label }}</span>
    <span v-if="active" class="pm-check">✓</span>
    <span v-if="!available" class="pm-unavailable">Indisponível</span>
  </button>
</template>

<script setup>
defineProps({
  type: { type: String, required: true },
  label: { type: String, required: true },
  active: { type: Boolean, default: false },
  available: { type: Boolean, default: true }
})

defineEmits(['click'])
</script>

<style scoped>
.payment-method-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-lg);
  padding: var(--space-xl) var(--space-2xl);
  background: var(--bg-card);
  border: 2px solid transparent;
  border-radius: var(--radius-lg);
  min-height: 110px;
  width: 100%;
  text-align: left;
  transition: border-color var(--transition-fast), transform var(--transition-fast), box-shadow var(--transition-fast);
  box-shadow: var(--shadow-sm);
}

.payment-method-card:active:not(:disabled) {
  transform: scale(0.98);
}

.payment-method-card.active {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
  box-shadow: var(--shadow-md);
}

.payment-method-card.unavailable {
  opacity: 0.4;
  cursor: not-allowed;
}

.pm-label {
  font-size: clamp(1.25rem, 3vw, 1.75rem);
  font-weight: var(--font-weight-semibold);
  color: var(--text-color);
  flex: 1;
}

.pm-check {
  font-size: 2rem;
  color: var(--color-primary);
  font-weight: var(--font-weight-bold);
}

.pm-unavailable {
  font-size: var(--font-size-sm);
  color: var(--color-error);
}
</style>
