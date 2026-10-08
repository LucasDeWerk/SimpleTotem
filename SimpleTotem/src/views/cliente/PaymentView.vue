<template>
  <ScreenContainer :title="lang.t.payment" :subtitle="lang.t.choosePayment">
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

      <!-- Seleção do método -->
      <template v-else-if="!showParcelamento">
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

          <p v-if="impressoraErro" class="payment-error">
            {{ impressoraErro }}
          </p>

          <div class="payment-actions">
            <PrimaryActionButton
              :label="verificandoImpressora ? lang.t.checkingPrinter : lang.t.confirmPayment"
              :fullWidth="true"
              :disabled="!payment.selectedMethod || payment.status === 'processing' || verificandoImpressora"
              @click="onConfirmMethod"
            />
          </div>
        </template>
      </template>

      <!-- Parcelamento do crédito — só aparece pra crédito; débito/PIX seguem direto -->
      <template v-else>
        <h3 class="installment-title">{{ lang.t.installmentTitle }}</h3>

        <div class="installment-options">
          <button
            class="installment-option"
            :class="{ active: parcelamentoTipo === 'a_vista' }"
            type="button"
            @click="selecionarParcelamento('a_vista')"
          >
            {{ lang.t.installmentCash }}
          </button>
          <button
            class="installment-option"
            :class="{ active: parcelamentoTipo === 'parcelado_estabelecimento' }"
            type="button"
            @click="selecionarParcelamento('parcelado_estabelecimento')"
          >
            {{ lang.t.installmentMerchant }}
          </button>
          <button
            class="installment-option"
            :class="{ active: parcelamentoTipo === 'parcelado_administradora' }"
            type="button"
            @click="selecionarParcelamento('parcelado_administradora')"
          >
            {{ lang.t.installmentIssuer }}
          </button>
        </div>

        <div v-if="parcelamentoTipo !== 'a_vista'" class="installment-stepper">
          <button
            class="installment-stepper-btn"
            type="button"
            :disabled="numParcelasEscolhidas <= MIN_PARCELAS"
            @click="decrementarParcelas"
          >−</button>
          <span class="installment-stepper-value">{{ numParcelasEscolhidas }}x</span>
          <button
            class="installment-stepper-btn"
            type="button"
            :disabled="numParcelasEscolhidas >= MAX_PARCELAS"
            @click="incrementarParcelas"
          >+</button>
        </div>

        <div class="payment-actions">
          <PrimaryActionButton
            :label="lang.t.confirmPayment"
            :fullWidth="true"
            @click="confirmarParcelamento"
          />
          <button class="payment-secondary-btn" type="button" @click="voltarParcelamento">
            {{ lang.t.back }}
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
import * as api from '@/services/api'

const router = useRouter()
const cart = useCartStore()
const payment = usePaymentStore()
const session = useSessionStore()
const lang = useLanguageStore()

const MIN_PARCELAS = 2
const MAX_PARCELAS = 12

const showParcelamento = ref(false)
const parcelamentoTipo = ref('a_vista')
const numParcelasEscolhidas = ref(MIN_PARCELAS)

const verificandoImpressora = ref(false)
const impressoraErro = ref('')

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

/**
 * Motivo para NÃO deixar o cliente pagar, ou '' se pode seguir.
 *
 * Pagar sem poder imprimir gera venda aprovada sem comprovante: a aplicação
 * nunca confirma (item 8.1.1 exige imprimir antes de FinalizaFuncaoSiTef) e a
 * transação fica pendente no SiTef.
 *
 * Fail-open de propósito quando a checagem é inconclusiva: só bloqueia com
 * evidência de problema (backend diz que não está pronta, ou o sensor responde
 * "sem papel"). Uma falha na consulta não deve parar as vendas do totem.
 */
async function motivoImpressoraIndisponivel() {
  try {
    const st = await api.obterStatusImpressora()
    if (st && st.pronta === false) return lang.t.printerUnavailableBlock
  } catch (err) {
    console.warn('[Payment] Não foi possível checar a impressora no backend:', err?.message)
  }

  // Sensor de papel só existe no Electron (detém o canal USB); ausente no browser.
  try {
    const papel = await window.electronAPI?.printer?.paperStatus?.()
    if (papel?.suportado && papel.temPapel === false) return lang.t.printerNoPaperBlock
  } catch (err) {
    console.warn('[Payment] Não foi possível ler o sensor de papel:', err?.message)
  }

  return ''
}

async function onConfirmMethod() {
  if (!payment.selectedMethod || verificandoImpressora.value) return

  verificandoImpressora.value = true
  impressoraErro.value = ''
  try {
    const motivo = await motivoImpressoraIndisponivel()
    if (motivo) {
      impressoraErro.value = motivo
      return
    }
  } finally {
    verificandoImpressora.value = false
  }

  // Crédito: mostra a escolha de parcelamento antes de seguir. Débito/PIX
  // seguem direto, sempre à vista — não faz sentido parcelar nesses.
  if (payment.selectedMethod.type === '3') {
    parcelamentoTipo.value = 'a_vista'
    numParcelasEscolhidas.value = MIN_PARCELAS
    showParcelamento.value = true
    return
  }
  payment.setParcelamento('a_vista', 1)
  router.push({ name: 'processing' })
}

function selecionarParcelamento(tipo) {
  parcelamentoTipo.value = tipo
  if (tipo !== 'a_vista' && numParcelasEscolhidas.value < MIN_PARCELAS) {
    numParcelasEscolhidas.value = MIN_PARCELAS
  }
}

function incrementarParcelas() {
  if (numParcelasEscolhidas.value < MAX_PARCELAS) numParcelasEscolhidas.value++
}

function decrementarParcelas() {
  if (numParcelasEscolhidas.value > MIN_PARCELAS) numParcelasEscolhidas.value--
}

function confirmarParcelamento() {
  const parcelas = parcelamentoTipo.value === 'a_vista' ? 1 : numParcelasEscolhidas.value
  payment.setParcelamento(parcelamentoTipo.value, parcelas)
  router.push({ name: 'processing' })
}

function voltarParcelamento() {
  showParcelamento.value = false
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

.installment-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: #0f172a;
  text-align: center;
}

.installment-options {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.installment-option {
  min-height: var(--btn-min-height);
  padding: var(--space-md) var(--space-xl);
  background: var(--bg-card);
  border: 2px solid transparent;
  border-radius: var(--radius-md);
  color: var(--text-color);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  text-align: left;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: border-color var(--transition-fast), background var(--transition-fast);
}

.installment-option.active {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}

.installment-stepper {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-xl);
}

.installment-stepper-btn {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  border: 2px solid var(--color-primary);
  background: transparent;
  color: var(--color-primary);
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.installment-stepper-btn:active:not(:disabled) {
  background: var(--color-primary-light);
}

.installment-stepper-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.installment-stepper-value {
  font-size: var(--font-size-2xl);
  font-weight: 900;
  color: #0f172a;
  min-width: 3ch;
  text-align: center;
}

</style>
