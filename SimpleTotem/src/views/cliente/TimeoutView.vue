<template>
  <div class="timeout-view">
    <div class="timeout-content animate-fade-in">
      <span class="timeout-icon">⏱</span>
      <h2 class="timeout-headline">Sessão encerrada</h2>
      <p class="timeout-subheadline">Seu tempo de inatividade expirou.</p>
      <p class="timeout-redirect">Redirecionando em {{ countdown }}s...</p>
      <PrimaryActionButton
        label="VOLTAR AO INÍCIO"
        @click="goHome"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'
import { usePaymentStore } from '@/stores/payment'
import { useSessionStore } from '@/stores/session'
import PrimaryActionButton from '@/components/shared/PrimaryActionButton.vue'

const router = useRouter()
const cart = useCartStore()
const payment = usePaymentStore()
const session = useSessionStore()

const countdown = ref(5)
let timer = null

onMounted(() => {
  // Limpa tudo
  cart.clearCart()
  payment.resetPayment()
  session.endSession()

  timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(timer)
      goHome()
    }
  }, 1000)
})

onUnmounted(() => {
  clearInterval(timer)
})

function goHome() {
  clearInterval(timer)
  router.replace({ name: 'home' })
}
</script>

<style scoped>
.timeout-view {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(
    135deg,
    #fef5f5 0%,
    #fef0f0 50%,
    #fee5e5 100%
  );
}

.timeout-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-xl);
  text-align: center;
  padding: var(--space-2xl);
  max-width: 480px;
}

.timeout-icon {
  font-size: 5rem;
  animation: pulse-fade 2s ease-in-out infinite;
}

@keyframes pulse-fade {
  0%, 100% {
    opacity: 0.6;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.1);
  }
}

.timeout-headline {
  font-size: var(--font-size-3xl);
  font-weight: 900;
  color: #0f172a;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.timeout-subheadline {
  font-size: var(--font-size-lg);
  color: #64748b;
  font-weight: 500;
}

.timeout-redirect {
  font-size: var(--font-size-md);
  color: #64748b;
  opacity: 0.8;
  font-weight: 600;
}
</style>
