<template>
  <div class="totem-cliente-layout">
    <!-- Header só aparece em telas que não são o catálogo principal -->
    <TotemHeader
      v-if="showHeader"
      :showBack="showBack"
      :cartCount="cart.itemCount"
      :cartTotal="cart.total"
      :currentStep="currentStep"
      :showClock="true"
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

    <!-- Aviso de inatividade (15 segundos para expiração) -->
    <TimeoutOverlay
      v-if="showTimeoutWarning"
      :secondsLeft="session.secondsLeft"
      message="Você ainda está aí?"
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
import { useIdleTimer } from '@/composables/useIdleTimer'
import TotemHeader from '@/components/shared/TotemHeader.vue'
import TimeoutOverlay from '@/components/shared/TimeoutOverlay.vue'

const route = useRoute()
const router = useRouter()
const cart = useCartStore()
const session = useSessionStore()
const device = useDeviceStore()
const catalog = useCatalogStore()

useIdleTimer()

// O header não aparece na home e no catálogo (que tem layout próprio)
const showHeader = computed(() => {
  const noHeader = ['home', 'catalog', 'processing', 'success', 'timeout']
  return !noHeader.includes(route.name)
})

const showBack = computed(() => route.meta.showBack === true)

const currentStep = computed(() => {
  const steps = {
    cart: 'Revise seu pedido',
    payment: 'Pagamento'
  }
  return steps[route.name] || ''
})

// Mostrar aviso quando está ativo, a 15 segundos do timeout, e não na home
const showTimeoutWarning = computed(() => {
  return session.isActive &&
         session.secondsLeft <= 15 &&
         session.secondsLeft > 0 &&
         route.name !== 'home' &&
         route.name !== 'timeout'
})

function goBack() {
  router.back()
}

function goToCart() {
  router.push({ name: 'cart' })
}

function continueSession() {
  session.resetTimer()
}

// Quando a sessão expira (secondsLeft = 0), vai para home
watch(() => session.secondsLeft, (val) => {
  if (val <= 0 && session.isActive === false && route.name !== 'home') {
    // Limpar carrinho e estado
    cart.clearCart()
    // Redirecionar para home
    router.replace({ name: 'home' })
  }
})

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
</style>
