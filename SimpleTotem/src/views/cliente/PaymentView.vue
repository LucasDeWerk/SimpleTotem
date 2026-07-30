<template>
  <ScreenContainer :title="lang.t.payment" :subtitle="stepSubtitle">
    <div class="payment-wrapper">

      <!-- Carregando métodos -->
      <div v-if="payment.loadingMethods" class="payment-state">
        <div class="payment-spinner"></div>
        <p>{{ lang.t.loadingPaymentMethods }}</p>
      </div>

      <!-- Erro / sem métodos -->
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

      <!-- PASSO 1: Seleção do método -->
      <template v-else-if="!showInstallmentStep">
        <div class="payment-methods">
          <PaymentMethodCard
            v-for="method in payment.availableMethods"
            :key="method.type"
            :type="method.type"
            :label="method.label"
            :icon="paymentIcon(method.type, method.label)"
            :active="payment.selectedMethod?.type === method.type"
            :available="method.available"
            :unavailable-label="lang.t.unavailable"
            @click="onSelectMethod(method)"
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
              @click="onConfirmMethod"
            />
          </div>
        </template>
      </template>

      <!-- PASSO 2: Seleção de parcelamento (somente crédito) -->
      <template v-else>
        <div class="installment-wrapper">

          <!-- Opções de tipo — mesmo padrão visual do PaymentMethodCard -->
          <div class="installment-options">
            <button
              v-for="opt in installmentOptions"
              :key="opt.tipo"
              class="installment-option"
              :class="{ active: selectedTipo === opt.tipo }"
              type="button"
              @click="selectedTipo = opt.tipo"
            >
              <span class="inst-icon">{{ opt.icon }}</span>
              <span class="inst-label">{{ opt.label }}</span>
              <span v-if="selectedTipo === opt.tipo" class="inst-check">✓</span>
            </button>
          </div>

          <!-- Seletor de quantidade — somente para parcelado -->
          <div v-if="selectedTipo !== 'a_vista'" class="parcelas-selector">
            <p class="parcelas-label">Número de parcelas:</p>
            <div class="parcelas-grid">
              <button
                v-for="n in parcelas"
                :key="n"
                class="parcela-btn"
                :class="{ active: numParcelas === n }"
                type="button"
                @click="numParcelas = n"
              >
                {{ n }}x
              </button>
            </div>
          </div>

          <!-- Resumo -->
          <div class="payment-summary">
            <div class="payment-total-row">
              <span class="payment-total-label">{{ lang.t.totalToPay }}</span>
              <span class="payment-total-value">
                R$ {{ (cart.vendaCalculada?.total ?? cart.total).toFixed(2) }}
              </span>
            </div>
            <p v-if="selectedTipo !== 'a_vista'" class="parcela-hint">
              {{ numParcelas }}x de R$ {{ parcelValue }}
            </p>
          </div>

          <!-- Ações -->
          <PrimaryActionButton
            label="Confirmar Pagamento"
            :fullWidth="true"
            @click="confirmPayment"
          />
          <button class="payment-secondary-btn" type="button" @click="showInstallmentStep = false">
            Voltar
          </button>

        </div>
      </template>

    </div>
  </ScreenContainer>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'
import { usePaymentStore } from '@/stores/payment'
import { useSessionStore } from '@/stores/session'
import { useLanguageStore } from '@/stores/language'
import ScreenContainer from '@/components/shared/ScreenContainer.vue'
import PaymentMethodCard from '@/components/shared/PaymentMethodCard.vue'
import PrimaryActionButton from '@/components/shared/PrimaryActionButton.vue'

const router = useRouter()
const cart = useCartStore()
const payment = usePaymentStore()
const session = useSessionStore()
const lang = useLanguageStore()

// ── Parcelamento ─────────────────────────────────────────────────────────────
const showInstallmentStep = ref(false)
const selectedTipo = ref('a_vista')
const numParcelas = ref(1)

const installmentOptions = [
  { tipo: 'a_vista', label: 'À vista', icon: '💳' },
  { tipo: 'parcelado_estabelecimento', label: 'Parcelado pelo estabelecimento', icon: '🏪' },
  { tipo: 'parcelado_administradora', label: 'Parcelado pela administradora', icon: '🏦' },
]

const parcelas = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

const parcelValue = computed(() => {
  const total = cart.vendaCalculada?.total ?? cart.total
  if (!numParcelas.value || numParcelas.value <= 0) return '0,00'
  return (total / numParcelas.value).toFixed(2).replace('.', ',')
})

// ── Computed ─────────────────────────────────────────────────────────────────
const methodsUnavailable = computed(() =>
  !payment.loadingMethods &&
  (payment.methodsLoadError || payment.availableMethods.length === 0)
)

const methodsReady = computed(() =>
  !payment.loadingMethods &&
  !payment.methodsLoadError &&
  payment.availableMethods.length > 0
)

function isCredit(method) {
  const key = `${method?.type || ''} ${method?.label || ''} ${method?.descricao || ''}`.toLowerCase()
  return key.includes('cred') || method?.type === '3'
}

const stepSubtitle = computed(() =>
  showInstallmentStep.value ? 'Como deseja parcelar?' : lang.t.choosePayment
)

onMounted(async () => {
  session.pauseSession()
  await payment.fetchPaymentMethods()
})

onUnmounted(() => {
  if (router.currentRoute.value.name !== 'processing') {
    session.resumeSession()
  }
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

function onSelectMethod(method) {
  payment.selectMethod(method)
}

function onConfirmMethod() {
  if (!payment.selectedMethod) return
  if (isCredit(payment.selectedMethod)) {
    selectedTipo.value = 'a_vista'
    numParcelas.value = 1
    showInstallmentStep.value = true
  } else {
    confirmPayment()
  }
}

function confirmPayment() {
  if (!payment.selectedMethod) return
  // Armazena a escolha de parcelamento no store para o ProcessingView usar
  payment.setParcelamento(
    selectedTipo.value,
    selectedTipo.value === 'a_vista' ? 1 : numParcelas.value
  )
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

/* ── Parcelamento ─────────────────────────────────────────────── */
.installment-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
}

/* Mesmo padrão visual do PaymentMethodCard */
.installment-options {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.installment-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-lg);
  padding: var(--space-xl) var(--space-2xl);
  background: var(--bg-card);
  border: 2px solid transparent;
  border-radius: var(--radius-lg);
  min-height: 110px;
  width: 100%;
  text-align: left;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: border-color var(--transition-fast), background var(--transition-fast), box-shadow var(--transition-fast), transform var(--transition-fast);
}

.installment-option:active {
  transform: scale(0.98);
}

.installment-option.active {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
  box-shadow: var(--shadow-md);
}

.inst-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.inst-label {
  font-size: clamp(1.125rem, 2.5vw, 1.5rem);
  font-weight: var(--font-weight-semibold);
  color: var(--text-color);
  flex: 1;
}

.inst-check {
  font-size: 2rem;
  color: var(--color-primary);
  font-weight: var(--font-weight-bold);
  flex-shrink: 0;
}

/* Seletor de parcelas */
.parcelas-selector {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.parcelas-label {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: #64748b;
}

.parcelas-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
}

.parcela-btn {
  min-width: 72px;
  min-height: var(--btn-min-height);
  padding: var(--space-sm);
  border: 2px solid transparent;
  border-radius: var(--radius-md);
  background: var(--bg-card);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--text-color);
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: border-color var(--transition-fast), background var(--transition-fast), transform var(--transition-fast);
}

.parcela-btn:active {
  transform: scale(0.96);
}

.parcela-btn.active {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
  color: var(--color-primary);
  box-shadow: var(--shadow-md);
}

.parcela-hint {
  font-size: var(--font-size-md);
  color: var(--text-color-laranja);
  font-weight: var(--font-weight-medium);
  text-align: right;
}
</style>
