<template>
  <button
    class="lang-switcher"
    type="button"
    :class="{ compact }"
    :title="lang.t.changeLanguage || lang.currentLabel"
    @click="lang.cycleLanguage()"
  >
    <span class="lang-flag">{{ lang.currentFlag }}</span>
    <span v-if="!compact" class="lang-label">{{ lang.currentLabel }}</span>
  </button>
</template>

<script setup>
import { useLanguageStore } from '@/stores/language'

defineProps({
  compact: { type: Boolean, default: false },
})

const lang = useLanguageStore()
</script>

<style scoped>
.lang-switcher {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  min-height: 48px;
  min-width: 48px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(245, 124, 0, 0.2);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  box-shadow: var(--shadow-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--text-color);
  z-index: 200;
}

.lang-switcher.compact {
  padding: 10px 14px;
  min-height: 48px;
  min-width: 48px;
}

.lang-switcher:active {
  transform: scale(0.97);
  border-color: rgba(245, 124, 0, 0.4);
}

.lang-flag {
  font-size: 1.4rem;
  line-height: 1;
}

.lang-label {
  font-size: var(--font-size-sm);
  letter-spacing: 0.02em;
}
</style>
