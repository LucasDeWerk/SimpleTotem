<template>
  <div class="timeout-overlay">
    <div class="timeout-content animate-fade-in">
      <div class="timeout-icon">⏱</div>
      <p class="timeout-message">{{ message || lang.t.sessionWillEnd }}</p>
      <div class="timeout-countdown">
        <span class="timeout-seconds">{{ secondsLeft }}</span>
        <span class="timeout-label">{{ lang.t.secondsUnit }}</span>
      </div>
      <button class="timeout-continue" @click="$emit('continue')">
        {{ lang.t.continueShoppingBtn }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { useLanguageStore } from '@/stores/language'

defineProps({
  secondsLeft: { type: Number, default: 0 },
  message: { type: String, default: '' },
})

defineEmits(['continue'])

const lang = useLanguageStore()
</script>

<style scoped>
.timeout-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.timeout-content {
  text-align: center;
  color: white;
  padding: var(--space-3xl);
}

.timeout-icon {
  font-size: 4rem;
  margin-bottom: var(--space-lg);
}

.timeout-message {
  font-size: var(--font-size-xl);
  margin-bottom: var(--space-xl);
  opacity: 0.9;
}

.timeout-countdown {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: var(--space-2xl);
}

.timeout-seconds {
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary);
}

.timeout-label {
  font-size: var(--font-size-md);
  opacity: 0.7;
}

.timeout-continue {
  min-height: var(--btn-min-height);
  padding: var(--space-md) var(--space-2xl);
  background: var(--color-primary);
  color: white;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  border-radius: var(--radius-md);
  letter-spacing: 0.5px;
  transition: transform var(--transition-fast);
  border: none;
  cursor: pointer;
}

.timeout-continue:active {
  transform: scale(0.97);
}
</style>
