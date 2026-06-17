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

    <TimeoutOverlay
      v-if="showTimeoutWarning"
      :secondsLeft="session.secondsLeft"
      :message="lang.t.stillThere"
      @continue="continueSession"
    />

    <div v-if="showFloatingLanguage" class="layout-lang-switcher">
      <LanguageSwitcher />
    </div>
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
import { useIdleTimer } from '@/composables/useIdleTimer'
import TotemHeader from '@/components/shared/TotemHeader.vue'
import TimeoutOverlay from '@/components/shared/TimeoutOverlay.vue'
import LanguageSwitcher from '@/components/shared/LanguageSwitcher.vue'

const route = useRoute()
const router = useRouter()
const cart = useCartStore()
const session = useSessionStore()
const device = useDeviceStore()
const catalog = useCatalogStore()
const lang = useLanguageStore()

useIdleTimer()

const SESSION_PAUSE_ROUTES = ['payment', 'processing', 'success']

const showHeader = computed(() => {
  const noHeader = ['home', 'catalog', 'processing', 'success', 'timeout']
  return !noHeader.includes(route.name)
})

const showBack = computed(() => route.meta.showBack === true)

const showFloatingLanguage = computed(() => route.name === 'catalog')

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

.layout-lang-switcher {
  position: fixed;
  top: 24px;
  right: 24px;
  z-index: 200;
}

@media (max-width: 768px) {
  .layout-lang-switcher {
    top: 16px;
    right: 16px;
  }
}
</style>
