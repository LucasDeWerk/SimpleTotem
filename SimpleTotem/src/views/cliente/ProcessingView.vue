<template>
  <div class="processing-view">
    <div class="processing-content animate-fade-in">

      <!-- Carregando -->
      <template v-if="!erro">
        <div class="processing-spinner">
          <div class="spinner-ring"></div>
        </div>
        <h2 class="processing-headline">Processando pagamento</h2>
        <p class="processing-subheadline">Siga as instruções no pinpad...</p>
      </template>

      <!-- Erro -->
      <template v-else>
        <div class="processing-error-icon">✕</div>
        <h2 class="processing-headline error">Pagamento não aprovado</h2>
        <p class="processing-subheadline">{{ erro }}</p>
        <button class="btn-voltar" @click="voltar">Tentar novamente</button>
      </template>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'
import { usePaymentStore } from '@/stores/payment'

const router  = useRouter()
const cart    = useCartStore()
const payment = usePaymentStore()

const erro = ref('')

onMounted(async () => {
  const ok = await payment.iniciarTransacao(cart)
  if (ok) {
    cart.clearCart()
    router.push({ name: 'success' })
  } else {
    erro.value = payment.errorMessage || 'Erro ao processar pagamento. Tente novamente.'
  }
})

function voltar() {
  payment.resetPayment()
  router.push({ name: 'payment' })
}
</script>

<style scoped>
.processing-view {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #fef9f5 0%, #fef5f0 50%, #fdeee7 100%);
}

.processing-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-xl);
  text-align: center;
  padding: var(--space-2xl);
  max-width: 520px;
  width: 100%;
}

.processing-spinner {
  width: 100px;
  height: 100px;
  position: relative;
}

.spinner-ring {
  width: 100%;
  height: 100%;
  border: 6px solid rgba(245, 124, 0, 0.15);
  border-top-color: #F57C00;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.processing-headline {
  font-size: var(--font-size-3xl);
  font-weight: 900;
  color: #0f172a;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.processing-headline.error {
  color: #dc2626;
}

.processing-subheadline {
  font-size: var(--font-size-lg);
  color: #64748b;
  font-weight: 500;
}

.processing-error-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: #fee2e2;
  color: #dc2626;
  font-size: 2.5rem;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-voltar {
  margin-top: var(--space-md);
  padding: var(--space-md) var(--space-2xl);
  background: #F57C00;
  color: #fff;
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--font-size-lg);
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-voltar:hover {
  background: #e65100;
}
</style>
