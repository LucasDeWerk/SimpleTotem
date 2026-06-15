<template>
  <header class="totem-header" v-if="!hidden">
    <div class="header-left">
      <button v-if="showBack" class="header-back-btn touch-target" @click="$emit('back')" :aria-label="lang.t.back">
        <span class="back-icon">←</span>
      </button>
      <div class="header-logo">
        <span class="logo-text">Simple<span class="logo-accent">Totem</span></span>
      </div>
    </div>

    <div class="header-center">
      <span v-if="currentStep" class="header-step">{{ currentStep }}</span>
    </div>

    <div class="header-right">
      <LanguageSwitcher v-if="showLanguage" compact />
      <div v-if="showClock" class="header-clock">{{ clock }}</div>
      <div
        v-if="connectionStatus !== undefined"
        class="connection-status"
        :class="connectionStatus ? 'online' : 'offline'"
        :title="connectionStatus ? lang.t.online : lang.t.offline"
        :aria-label="connectionStatus ? lang.t.online : lang.t.offline"
      >
        <span class="connection-dot" />
        <span class="connection-label">{{ connectionStatus ? lang.t.online : lang.t.offline }}</span>
      </div>
      <button
        v-if="cartCount > 0"
        class="header-cart-btn touch-target"
        @click="$emit('goToCart')"
        :aria-label="`${lang.t.yourCart}, ${cartCount} ${cartCount === 1 ? lang.t.item : lang.t.items}`"
      >
        <span class="cart-icon">🛒</span>
        <span class="cart-badge">{{ cartCount }}</span>
        <span class="cart-total">R$ {{ cartTotal.toFixed(2) }}</span>
      </button>
    </div>
  </header>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useLanguageStore } from '@/stores/language'
import LanguageSwitcher from './LanguageSwitcher.vue'

defineProps({
  showBack: { type: Boolean, default: false },
  cartCount: { type: Number, default: 0 },
  cartTotal: { type: Number, default: 0 },
  currentStep: { type: String, default: '' },
  showClock: { type: Boolean, default: true },
  showLanguage: { type: Boolean, default: false },
  connectionStatus: { type: Boolean, default: undefined },
  hidden: { type: Boolean, default: false },
})

defineEmits(['back', 'goToCart'])

const lang = useLanguageStore()
const clock = ref('')
let clockInterval = null

function updateClock() {
  const now = new Date()
  clock.value = now.toLocaleTimeString(lang.currentLocale, { hour: '2-digit', minute: '2-digit' })
}

watch(() => lang.currentLocale, updateClock)

onMounted(() => {
  updateClock()
  clockInterval = setInterval(updateClock, 30000)
})

onUnmounted(() => {
  clearInterval(clockInterval)
})
</script>

<style scoped>
.totem-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md) var(--space-lg);
  background: var(--bg-navbar);
  color: var(--text-color-secondary);
  height: 72px;
  flex-shrink: 0;
  z-index: 100;
  gap: var(--space-sm);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  min-width: 0;
  flex-shrink: 1;
}

.header-back-btn {
  background: rgba(255,255,255,0.15);
  color: white;
  border-radius: var(--radius-md);
  width: 48px;
  height: 48px;
  font-size: 1.5rem;
  transition: background var(--transition-fast);
  border: none;
  cursor: pointer;
  flex-shrink: 0;
}

.header-back-btn:active {
  background: rgba(255,255,255,0.3);
}

.header-logo {
  display: flex;
  align-items: center;
  min-width: 0;
}

.logo-text {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: white;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.logo-accent {
  color: #ffe0b2;
}

.header-center {
  flex: 1;
  text-align: center;
  min-width: 0;
}

.header-step {
  font-size: var(--font-size-sm);
  opacity: 0.8;
  text-transform: uppercase;
  letter-spacing: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-shrink: 0;
}

.header-right :deep(.lang-switcher) {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.25);
  color: white;
  box-shadow: none;
  min-height: 48px;
  min-width: 48px;
  padding: 8px 12px;
}

.header-right :deep(.lang-switcher:active) {
  background: rgba(255, 255, 255, 0.25);
}

.header-clock {
  font-size: var(--font-size-md);
  opacity: 0.9;
  white-space: nowrap;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-xs);
  opacity: 0.9;
}

.connection-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.connection-status.online .connection-dot {
  background: var(--color-success);
}

.connection-status.offline .connection-dot {
  background: var(--color-error);
}

.connection-label {
  white-space: nowrap;
}

.header-cart-btn {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  background: rgba(255,255,255,0.15);
  color: white;
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-md);
  min-height: 48px;
  transition: background var(--transition-fast);
  border: none;
  cursor: pointer;
  flex-shrink: 0;
}

.header-cart-btn:active {
  background: rgba(255,255,255,0.3);
}

.cart-icon {
  font-size: 1.3rem;
}

.cart-badge {
  background: white;
  color: var(--color-primary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  min-width: 22px;
  height: 22px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 6px;
}

.cart-total {
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-sm);
  white-space: nowrap;
}

@media (max-width: 900px) {
  .header-clock,
  .connection-label {
    display: none;
  }
}

@media (max-width: 720px) {
  .header-step {
    display: none;
  }

  .cart-total {
    display: none;
  }

  .logo-text {
    font-size: var(--font-size-lg);
  }

  .totem-header {
    padding: var(--space-sm) var(--space-md);
  }
}
</style>
