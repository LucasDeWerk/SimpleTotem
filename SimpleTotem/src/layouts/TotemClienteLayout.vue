<template>
  <div class="totem-cliente-layout">
    <TotemHeader
      v-if="showHeader"
      :showBack="showBack"
      :cartCount="cart.itemCount"
      :cartTotal="cart.total"
      :currentStep="currentStep"
      :showClock="true"
      :showLanguage="true"
      :connectionStatus="device.isOnline"
      :hidden="false"
      @back="goBack"
      @goToCart="goToCart"
    />

    <main class="totem-main">
      <router-view v-slot="{ Component, route }">
        <transition name="fade" mode="out-in">
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </main>

    <!-- Barra de navegação obrigatória (Fiserv req. 1.3) -->
    <nav v-if="showNavBar" class="totem-nav-bar">
      <button class="nav-btn nav-btn--ghost" type="button" @click="goMenuInicial">
        ← Menu Inicial
      </button>
      <button class="nav-btn nav-btn--encerrar" type="button" @click="encerrar">
        Encerrar
      </button>
    </nav>

    <TimeoutOverlay
      v-if="showTimeoutWarning"
      :secondsLeft="session.secondsLeft"
      :message="lang.t.stillThere"
      @continue="continueSession"
    />

  </div>
</template>

<script setup>
import { computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'
import { useSessionStore } from '@/stores/session'
import { useDeviceStore } from '@/stores/device'
import { useCatalogStore } from '@/stores/catalog'
import { useLanguageStore } from '@/stores/language'
import { usePaymentStore } from '@/stores/payment'
import { useIdleTimer } from '@/composables/useIdleTimer'
import TotemHeader from '@/components/shared/TotemHeader.vue'
import TimeoutOverlay from '@/components/shared/TimeoutOverlay.vue'

const route = useRoute()
const router = useRouter()
const cart = useCartStore()
const session = useSessionStore()
const device = useDeviceStore()
const catalog = useCatalogStore()
const lang = useLanguageStore()
const payment = usePaymentStore()

useIdleTimer()

const SESSION_PAUSE_ROUTES = ['payment', 'processing', 'success']

// NavBar obrigatória em todas as telas exceto: home, processing (pagamento em andamento), success, timeout
const NAV_BAR_HIDDEN = ['home', 'processing', 'success', 'timeout']
const showNavBar = computed(() => !NAV_BAR_HIDDEN.includes(route.name))

const showHeader = computed(() => {
  const noHeader = ['home', 'catalog', 'processing', 'success', 'timeout']
  return !noHeader.includes(route.name)
})

const showBack = computed(() => route.meta.showBack === true)

const currentStep = computed(() => {
  const steps = {
    cart: lang.t.reviseOrder,
    payment: lang.t.payment,
  }
  return steps[route.name] || ''
})

const showTimeoutWarning = computed(() => {
  if (SESSION_PAUSE_ROUTES.includes(route.name)) return false
  return session.isActive &&
         !session.paused &&
         session.secondsLeft <= 15 &&
         session.secondsLeft > 0 &&
         route.name !== 'home' &&
         route.name !== 'timeout'
})

watch(
  () => route.name,
  (name) => {
    if (SESSION_PAUSE_ROUTES.includes(name)) {
      session.pauseSession()
    } else if (session.isActive && session.paused) {
      session.resumeSession()
    }
  },
  { immediate: true }
)

watch(
  () => session.isActive,
  (active, wasActive) => {
    // 'success' gerencia o próprio encerramento via countdown
    const rotasProtegidas = ['home', 'timeout', 'success']
    if (wasActive && !active && !rotasProtegidas.includes(route.name)) {
      router.replace({ name: 'timeout' })
    }
  }
)

function goBack() {
  const target = route.meta.backTo
  if (target) {
    router.push({ name: target })
  } else {
    router.back()
  }
}

function goToCart() {
  router.push({ name: 'cart' })
}

function continueSession() {
  session.resetTimer()
}

function goMenuInicial() {
  router.push({ name: 'catalog' })
}

function encerrar() {
  cart.clearCart()
  payment.resetPayment()
  session.endSession()
  router.replace({ name: 'home' })
}

onMounted(() => {
  device.init()
  catalog.fetchCatalog()
})
</script>

<style scoped>
.totem-cliente-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-color);
  overflow: hidden;
}

.totem-main {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Mesma linguagem visual do TotemHeader */
.totem-nav-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-lg);
  background: var(--bg-navbar);
  flex-shrink: 0;
  height: 72px;
}

.nav-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 48px;
  padding: var(--space-sm) var(--space-xl);
  border-radius: var(--radius-md);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  letter-spacing: 0.5px;
  text-transform: uppercase;
  cursor: pointer;
  border: none;
  transition: background var(--transition-fast);
}

/* Mesmo padrão do header-back-btn e header-cart-btn */
.nav-btn--ghost {
  background: rgba(255, 255, 255, 0.15);
  color: var(--text-color-secondary);
}

.nav-btn--ghost:active {
  background: rgba(255, 255, 255, 0.3);
}

/* ENCERRAR: branco com texto vermelho — destaque sem sair do sistema */
.nav-btn--encerrar {
  background: rgba(255, 255, 255, 0.9);
  color: var(--color-error);
}

.nav-btn--encerrar:active {
  background: rgba(255, 255, 255, 1);
}
</style>
