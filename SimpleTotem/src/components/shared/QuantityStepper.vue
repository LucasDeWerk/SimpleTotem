<template>
  <div class="quantity-stepper">
    <button
      class="stepper-btn stepper-minus"
      :disabled="modelValue <= min"
      @click="decrement"
    >−</button>
    <span class="stepper-value">{{ modelValue }}</span>
    <button
      class="stepper-btn stepper-plus"
      :disabled="modelValue >= max"
      @click="increment"
    >+</button>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: Number, required: true },
  min: { type: Number, default: 0 },
  max: { type: Number, default: 99 }
})

const emit = defineEmits(['update:modelValue'])

function increment() {
  if (props.modelValue < props.max) {
    emit('update:modelValue', props.modelValue + 1)
  }
}

function decrement() {
  if (props.modelValue > props.min) {
    emit('update:modelValue', props.modelValue - 1)
  }
}
</script>

<style scoped>
.quantity-stepper {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  background: var(--bg-color-secondary);
  border-radius: var(--radius-md);
  padding: 4px;
}

.stepper-btn {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  color: var(--text-color);
  font-size: 1.5rem;
  font-weight: var(--font-weight-bold);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background var(--transition-fast);
  border: 1px solid var(--color-border-light);
}

.stepper-btn:active:not(:disabled) {
  background: var(--color-primary-light);
}

.stepper-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.stepper-plus {
  color: var(--color-primary);
}

.stepper-value {
  min-width: 48px;
  text-align: center;
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-color);
}
</style>
