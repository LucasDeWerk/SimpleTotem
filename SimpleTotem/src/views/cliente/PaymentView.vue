<template>
  <ScreenContainer :title="lang.t.payment" :subtitle="lang.t.choosePayment">
    <div class="payment-wrapper">

      <div v-if="payment.loadingMethods" class="payment-state">
        <div class="payment-spinner"></div>
        <p>{{ lang.t.loadingPaymentMethods }}</p>
      </div>

      <div v-else-if="methodsUnavailable" class="payment-state payment-state-empty">
        <span class="payment-state-icon">💳</span>
        <p>{{ payment.methodsLoadError ? lang.t.paymentMethodsError : lang.t.noPaymentMethods }}</p>
        <div class="payment-fallback-actions">
          <PrimaryActionButton
            :label="lang.t.retryLoad"
            :fullWidth="true"
            @click="retryLoad"
          />
          <button class="payment-secondary-btn" type="button" @click="goToCart">
            {{ lang.t.backToCart }}
          </button>
        </div>
      </div>

      <div v-else class="payment-methods">
        <PaymentMethodCard
          v-for="method in payment.availableMethods"
          :key="method.type"
          :type="method.type"
          :label="method.label"
          :icon="paymentIcon(method.type, method.label)"
          :active="payment.selectedMethod?.type === method.type"
          :available="method.available"
          :unavailable-label="lang.t.unavailable"
          @click="payment.selectMethod(method)"
        />
      </div>

      <template v-if="methodsReady">
        <div class="payment-summary">
          <div class="payment-total-row">
            <span class="payment-total-label">{{ lang.t.totalToPay }}</span>
            <span class="payment-total-value">
              R$ {{ (cart.vendaCalculada?.total ?? cart.total).toFixed(2) }}
            </span>
          </div>
        </div>

        <p v-if="payment.selectedMethod" class="payment-confirm-hint">
          {{ lang.t.confirmPaymentWith }} <strong>{{ payment.selectedMethod.label }}</strong>
        </p>

        <p v-if="payment.status === 'error'" class="payment-error">
          {{ payment.errorMessage || lang.t.paymentError }}
        </p>

        <div class="payment-actions">
          <PrimaryActionButton
            :label="lang.t.confirmPayment"
            :fullWidth="true"
            :disabled="!payment.selectedMethod || payment.status === 'processing'"
            @click="confirmPayment"
          />
        </div>
      </template>
    </div>
  </ScreenContainer>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'
import { usePaymentStore } from '@/stores/payment'
import { useLanguageStore } from '@/stores/language'
import ScreenContainer from '@/components/shared/ScreenContainer.vue'
import PaymentMethodCard from '@/components/shared/PaymentMethodCard.vue'
import PrimaryActionButton from '@/components/shared/PrimaryActionButton.vue'

const router = useRouter()
const cart = useCartStore()
const payment = usePaymentStore()
const lang = useLanguageStore()

const methodsUnavailable = computed(() =>
  !payment.loadingMethods &&
  (payment.methodsLoadError || payment.availableMethods.length === 0)
)

const methodsReady = computed(() =>
  !payment.loadingMethods &&
  !payment.methodsLoadError &&
  payment.availableMethods.length > 0
)

onMounted(async () => {
  await payment.fetchPaymentMethods()
})

function paymentIcon(type, label) {
  const key = `${type || ''} ${label || ''}`.toLowerCase()
  if (key.includes('pix')) return '📱'
  if (key.includes('débito') || key.includes('debito')) return '💳'
  if (key.includes('crédito') || key.includes('credito')) return '💳'
  if (key.includes('dinheiro') || key.includes('cash')) return '💵'
  return '💳'
}

async function retryLoad() {
  await payment.fetchPaymentMethods()
}

function goToCart() {
  router.push({ name: 'cart' })
}

async function confirmPayment() {
  if (!payment.selectedMethod) return
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

.payment-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-lg);
  padding: var(--space-2xl);
  text-align: center;
  color: #64748b;
  font-size: var(--font-size-lg);
  font-weight: 500;
}

.payment-state-empty {
  background: rgba(245, 124, 0, 0.06);
  border: 1px dashed rgba(245, 124, 0, 0.25);
  border-radius: var(--radius-lg);
}

.payment-state-icon {
  font-size: 3rem;
  line-height: 1;
}

.payment-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid rgba(245, 124, 0, 0.15);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.payment-fallback-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  width: 100%;
  max-width: 360px;
}

.payment-secondary-btn {
  min-height: var(--btn-min-height);
  padding: var(--space-md) var(--space-xl);
  background: transparent;
  border: 2px solid var(--color-primary);
  border-radius: var(--radius-md);
  color: var(--color-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  letter-spacing: 0.5px;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.payment-secondary-btn:active {
  background: var(--color-primary-light);
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

.payment-confirm-hint {
  font-size: var(--font-size-lg);
  color: #64748b;
  text-align: center;
  font-weight: 500;
}

.payment-confirm-hint strong {
  color: var(--color-primary);
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
</style>
