<template>
  <header class="totem-header" v-if="!hidden">
    <div class="header-left">
      <button v-if="showBack" class="header-back-btn touch-target" @click="$emit('back')">
        <span class="back-icon"><</span>
      </button>
      <div class="header-logo">
        <span class="logo-text">Simple<span class="logo-accent">Totem</span></span>
      </div>
    </div>

    <div class="header-center">
      <span v-if="currentStep" class="header-step">{{ currentStep }}</span>
    </div>

    <div class="header-right">
      <div v-if="showClock" class="header-clock">{{ clock }}</div>
      <div v-if="connectionStatus !== undefined" class="connection-dot" :class="connectionStatus ? 'online' : 'offline'" />
      <button v-if="cartCount > 0" class="header-cart-btn touch-target" @click="$emit('goToCart')">

        <span class="cart-badge">{{ cartCount }}</span>
        <span class="cart-total">R$ {{ cartTotal.toFixed(2) }}</span>
      </button>
    </div>
  </header>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  showBack: { type: Boolean, default: false },
  cartCount: { type: Number, default: 0 },
  cartTotal: { type: Number, default: 0 },
  currentStep: { type: String, default: '' },
  showClock: { type: Boolean, default: true },
  connectionStatus: { type: Boolean, default: undefined },
  hidden: { type: Boolean, default: false }
})

defineEmits(['back', 'goToCart'])

const clock = ref('')

let clockInterval = null

function updateClock() {
  const now = new Date()
  clock.value = now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

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
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.header-back-btn {
  background: rgba(255,255,255,0.15);
  color: white;
  border-radius: var(--radius-md);
  width: 48px;
  height: 48px;
  font-size: 1.5rem;
  transition: background var(--transition-fast);
}

.header-back-btn:active {
  background: rgba(255,255,255,0.3);
}

.back-icon {
  font-size: 1.5rem;
}

.header-logo {
  display: flex;
  align-items: center;
}

.logo-text {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: white;
}

.logo-accent {
  color: #ffe0b2;
}

.header-center {
  flex: 1;
  text-align: center;
}

.header-step {
  font-size: var(--font-size-sm);
  opacity: 0.8;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.header-clock {
  font-size: var(--font-size-md);
  opacity: 0.9;
}

.connection-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.connection-dot.online {
  background: var(--color-success);
}

.connection-dot.offline {
  background: var(--color-error);
}

.header-cart-btn {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  background: rgba(255,255,255,0.15);
  color: white;
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-md);
  height: 48px;
  transition: background var(--transition-fast);
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
}
</style>
