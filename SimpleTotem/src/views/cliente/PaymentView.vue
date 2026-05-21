<template>
  <ScreenContainer title="Pagamento" subtitle="Escolha a forma de pagamento">
    <div class="payment-wrapper">

      <!-- Métodos de pagamento -->
      <div class="payment-methods">
        <PaymentMethodCard
          v-for="method in payment.availableMethods"
          :key="method.type"
          :type="method.type"
          :label="method.label"
          :active="payment.selectedMethod?.type === method.type"
          :available="method.available"
          @click="payment.selectMethod(method)"
        />
      </div>

      <!-- Total a pagar (do servidor) -->
      <div class="payment-summary">
        <div class="payment-total-row">
          <span class="payment-total-label">Total a pagar:</span>
          <span class="payment-total-value">
            R$ {{ (cart.vendaCalculada?.total ?? cart.total).toFixed(2) }}
          </span>
        </div>
      </div>

      <!-- Erro -->
      <p v-if="payment.status === 'error'" class="payment-error">
        {{ payment.errorMessage || 'Erro ao processar pagamento. Tente novamente.' }}
      </p>

      <!-- Ação -->
      <div class="payment-actions">
        <PrimaryActionButton
          label="CONFIRMAR PAGAMENTO"
          :fullWidth="true"
          :disabled="!payment.selectedMethod || payment.status === 'processing'"
          @click="confirmPayment"
        />
      </div>
    </div>
  </ScreenContainer>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'
import { usePaymentStore } from '@/stores/payment'
import ScreenContainer from '@/components/shared/ScreenContainer.vue'
import PaymentMethodCard from '@/components/shared/PaymentMethodCard.vue'
import PrimaryActionButton from '@/components/shared/PrimaryActionButton.vue'

const router  = useRouter()
const cart    = useCartStore()
const payment = usePaymentStore()

onMounted(async () => {
  await payment.fetchPaymentMethods()
})

async function confirmPayment() {
  if (!payment.selectedMethod) return
  // Navega para a tela de carregamento imediatamente — a transação roda lá
  router.push({ name: 'processing' })
}
</script>

<style scoped>
.payment-wrapper {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 100%;
  max-width: 860px;
  margin: 0 auto;
  width: 100%;
  padding: var(--space-2xl) 0;
  gap: var(--space-2xl);
}

.payment-methods {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.payment-summary {
  background: linear-gradient(135deg, rgba(245, 124, 0, 0.08), rgba(245, 124, 0, 0.04));
  border: 1px solid rgba(245, 124, 0, 0.15);
  border-radius: var(--radius-lg);
  padding: var(--space-xl);
}

.payment-total-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.payment-total-label {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  color: #0f172a;
}

.payment-total-value {
  font-size: clamp(2rem, 5vw, 3rem);
  font-weight: 900;
  color: var(--text-color-laranja);
  letter-spacing: -0.01em;
}

.payment-error {
  color: #f44336;
  font-size: var(--font-size-md);
  font-weight: 600;
  padding: var(--space-md) var(--space-lg);
  background: rgba(244, 67, 54, 0.08);
  border-radius: var(--radius-md);
  border: 1px solid rgba(244, 67, 54, 0.2);
  text-align: center;
}

.payment-actions {}
</style>


<style scoped>
.payment-wrapper {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 100%;
  max-width: 860px;
  margin: 0 auto;
  width: 100%;
  padding: var(--space-2xl) 0;
  gap: var(--space-2xl);
}

.payment-methods {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.payment-summary {
  background: linear-gradient(135deg, rgba(245, 124, 0, 0.08), rgba(245, 124, 0, 0.04));
  border: 1px solid rgba(245, 124, 0, 0.15);
  border-radius: var(--radius-lg);
  padding: var(--space-xl);
}

.payment-total-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.payment-total-label {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  color: #0f172a;
}

.payment-total-value {
  font-size: clamp(2rem, 5vw, 3rem);
  font-weight: 900;
  color: var(--text-color-laranja);
  letter-spacing: -0.01em;
}

.payment-actions {}
</style>
