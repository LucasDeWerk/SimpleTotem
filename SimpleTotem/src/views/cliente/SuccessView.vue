<template>
  <div class="success-view">
    <div class="success-content animate-fade-in">
      <div class="success-icon-wrap">
        <span class="success-icon">✓</span>
      </div>

      <h2 class="success-headline">{{ lang.t.purchaseDone }}</h2>

      <div class="success-details">
        <div class="detail-row">
          <span class="detail-label">{{ lang.t.orderNumber }}</span>
          <span class="detail-value">#{{ orderNumber }}</span>
        </div>
        <div v-if="authCode" class="detail-row">
          <span class="detail-label">{{ lang.t.transactionCode }}</span>
          <span class="detail-value highlight">{{ authCode }}</span>
        </div>
        <div v-if="nsuDisplay" class="detail-row">
          <span class="detail-label">{{ lang.t.nsuLabel }}</span>
          <span class="detail-value">{{ nsuDisplay }}</span>
        </div>
      </div>

      <div v-if="printing" class="print-status">
        <div class="spinner-small"></div>
        <p>{{ lang.t.printing }}</p>
      </div>

      <p v-if="printError" class="print-error">
        ⚠️ {{ lang.t.printError }} {{ printError }}
        <span class="print-error-hint">{{ lang.t.printFailedHint }}</span>
      </p>

      <p v-if="printSuccess" class="print-success">
        ✓ {{ lang.t.printSuccess }}
      </p>

      <p class="success-countdown">
        {{ lang.t.backIn }} <strong>{{ countdown }}</strong>{{ lang.t.seconds }}
      </p>

      <PrimaryActionButton
        :label="lang.t.backToStart"
        @click="newOrder"
        :disabled="printing"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'
import { usePaymentStore } from '@/stores/payment'
import { useSessionStore } from '@/stores/session'
import { useLanguageStore } from '@/stores/language'
import { useThermalPrinter } from '@/composables/useThermalPrinter'
import PrimaryActionButton from '@/components/shared/PrimaryActionButton.vue'

const router = useRouter()
const cart = useCartStore()
const payment = usePaymentStore()
const session = useSessionStore()
const lang = useLanguageStore()
const { printing, printComplete, printLines } = useThermalPrinter()

const countdown = ref(10)
const printError = ref(null)
const printSuccess = ref(false)

const order = computed(() => payment.completedOrder)
const tx = computed(() => payment.transactionResult)

const orderNumber = computed(() => {
  const id = tx.value?.id_venda
  if (id && id > 0) return id
  if (tx.value?.nsu_sitef) return tx.value.nsu_sitef
  return '—'
})

const authCode = computed(() => tx.value?.autorizacao || '')

const nsuDisplay = computed(() => {
  const nsu = tx.value?.nsu_host || tx.value?.nsu_sitef || ''
  if (!nsu || nsu === authCode.value) return ''
  return nsu
})

let timer = null

onMounted(async () => {
  session.pauseSession()
  await printReceipt()

  timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(timer)
      resetAndGoHome()
    }
  }, 1000)
})

onUnmounted(() => {
  clearInterval(timer)
})

function buildMinimalTxLines() {
  const lines = ['', 'COMPROVANTE TEF', '----------------']
  if (tx.value?.modalidade) lines.push(tx.value.modalidade)
  if (tx.value?.bandeira) lines.push(tx.value.bandeira)
  if (tx.value?.nsu_sitef) lines.push(`NSU: ${tx.value.nsu_sitef}`)
  if (tx.value?.nsu_host) lines.push(`Host: ${tx.value.nsu_host}`)
  if (tx.value?.autorizacao) lines.push(`AUT: ${tx.value.autorizacao}`)
  if (tx.value?.total_cobrado != null) {
    lines.push(`TOTAL: R$ ${Number(tx.value.total_cobrado).toFixed(2)}`)
  }
  lines.push('----------------', '')
  return lines
}

async function printReceipt() {
  try {
    if (!window.electronAPI?.printer) {
      printError.value = 'Impressora indisponível (abra pelo Electron, não pelo navegador)'
      return
    }

    // 1) Cupom TEF bruto — exatamente como a Fiserv/SiTef enviou (TC 122)
    const cupomBruto = tx.value?.cupom_bruto
    const blocosTef = tx.value?.linhas_cupom || []
    const temCupomTef = Boolean(cupomBruto) || blocosTef.some(b => String(b).length > 0)
    if (temCupomTef) {
      const payload = cupomBruto ? [cupomBruto] : blocosTef
      console.log('[SuccessView] Imprimindo cupom bruto TEF:', payload.join('').length, 'chars')
      const result = await printLines(payload, { cut: true, cupomFiserv: true })
      if (result.success) printSuccess.value = true
      else printError.value = result.message || lang.t.printError
      return
    }

    // 2) Recibo do pedido (itens + total)
    if (order.value?.items?.length) {
      const orderData = {
        company: { name: 'SIMPLETOTEM', cnpj: '00.000.000/0000-00' },
        orderNumber: orderNumber.value,
        date: new Date().toLocaleString('pt-BR'),
        items: order.value.items.map(item => ({
          name: item.name,
          quantity: item.quantity,
          unitPrice: item.unitPrice,
        })),
        subtotal: order.value.subtotal,
        discount: order.value.discount,
        total: order.value.total,
        paymentMethod: order.value.paymentMethod || '—',
        pickupCode: authCode.value,
      }
      console.log('[SuccessView] Imprimindo recibo do pedido')
      const result = await printComplete(orderData)
      if (result.success) printSuccess.value = true
      else printError.value = result.message || lang.t.printError
      return
    }

    // 3) Comprovante mínimo com dados da transação
    const minimal = buildMinimalTxLines()
    if (minimal.length > 3) {
      console.log('[SuccessView] Imprimindo comprovante mínimo TEF')
      const result = await printLines(minimal, { cut: true })
      if (result.success) printSuccess.value = true
      else printError.value = result.message || lang.t.printError
      return
    }

    printError.value = 'Sem dados para impressão'
    console.warn('[SuccessView] Nada para imprimir — tx:', tx.value, 'order:', order.value)
  } catch (error) {
    printError.value = error.message || lang.t.printError
    console.error('[SuccessView] Erro ao imprimir:', error)
  }
}

async function resetAndGoHome() {
  cart.clearCart()
  payment.resetPayment()
  await router.replace({ name: 'home' })
  session.endSession()
}

function newOrder() {
  clearInterval(timer)
  resetAndGoHome()
}
</script>

<style scoped>
.success-view {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f0fdf4 0%, #e8fdf0 50%, #dffce7 100%);
}

.success-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-xl);
  text-align: center;
  padding: var(--space-2xl);
  max-width: 480px;
}

.success-icon-wrap {
  width: 120px;
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #4caf50;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.4);
  }
  50% {
    transform: scale(1.05);
    box-shadow: 0 0 0 20px rgba(76, 175, 80, 0);
  }
}

.success-icon {
  font-size: 4rem;
  color: white;
  line-height: 1;
  font-weight: 900;
}

.success-headline {
  font-size: var(--font-size-3xl);
  font-weight: 900;
  color: #4caf50;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.success-details {
  width: 100%;
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.08), rgba(76, 175, 80, 0.04));
  border: 1px solid rgba(76, 175, 80, 0.15);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-label {
  font-size: var(--font-size-md);
  color: #64748b;
  font-weight: 500;
}

.detail-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: #0f172a;
}

.detail-value.highlight {
  color: #4caf50;
  font-size: var(--font-size-2xl);
  font-weight: 900;
}

.print-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-lg);
  background: rgba(76, 175, 80, 0.08);
  border: 1px solid rgba(76, 175, 80, 0.15);
  border-radius: var(--radius-md);
  color: #4caf50;
  font-weight: 600;
}

.spinner-small {
  width: 32px;
  height: 32px;
  border: 4px solid rgba(76, 175, 80, 0.15);
  border-top-color: #4caf50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.print-error {
  padding: var(--space-lg);
  background: rgba(244, 67, 54, 0.1);
  color: #f44336;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  border: 1px solid rgba(244, 67, 54, 0.2);
  font-weight: 600;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.print-error-hint {
  font-weight: var(--font-weight-bold);
  color: #b91c1c;
}

.print-success {
  padding: var(--space-lg);
  background: rgba(76, 175, 80, 0.1);
  color: #4caf50;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  border: 1px solid rgba(76, 175, 80, 0.2);
}

.success-countdown {
  font-size: var(--font-size-md);
  color: #64748b;
  font-weight: 600;
}
</style>
