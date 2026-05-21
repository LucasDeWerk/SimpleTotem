<template>
  <div class="success-view">
    <div class="success-content animate-fade-in">
      <div class="success-icon-wrap">
        <span class="success-icon">[OK]</span>
      </div>

      <h2 class="success-headline">Compra realizada!</h2>

      <div class="success-details">
        <div class="detail-row">
          <span class="detail-label">Número da compra</span>
          <span class="detail-value">#{{ orderNumber }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Código de retirada</span>
          <span class="detail-value highlight">{{ pickupCode }}</span>
        </div>
      </div>

      <!-- Status de impressão -->
      <div v-if="printing" class="print-status">
        <div class="spinner-small"></div>
        <p>Imprimindo comprovante...</p>
      </div>

      <p v-if="printError" class="print-error">
        ⚠️ Erro na impressão: {{ printError }}
      </p>

      <p v-if="printSuccess" class="print-success">
        ✓ Comprovante impresso com sucesso!
      </p>

      <p class="success-countdown">
        Voltando ao início em <strong>{{ countdown }}</strong>s
      </p>

      <PrimaryActionButton
        label="VOLTAR AO INÍCIO"
        icon="home"
        @click="newOrder"
        :disabled="printing"
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
import { useThermalPrinter } from '@/composables/useThermalPrinter'
import PrimaryActionButton from '@/components/shared/PrimaryActionButton.vue'

const router = useRouter()
const cart = useCartStore()
const payment = usePaymentStore()
const session = useSessionStore()
const { printing, printComplete } = useThermalPrinter()

const orderNumber = ref(Math.floor(1000 + Math.random() * 9000))
const pickupCode = ref('A' + Math.floor(10 + Math.random() * 90))
const countdown = ref(10)
const printError = ref(null)
const printSuccess = ref(false)

let timer = null

onMounted(async () => {
  // Imprimir comprovante automaticamente
  await printReceipt()

  // Iniciar contagem regressiva
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

async function printReceipt() {
  try {
    const orderData = {
      company: {
        name: 'SIMPLETOTEM',
        cnpj: '00.000.000/0000-00'
      },
      orderNumber: orderNumber.value,
      date: new Date().toLocaleString('pt-BR'),
      items: cart.items.map(item => ({
        name: item.name,
        quantity: item.quantity,
        unitPrice: item.unitPrice
      })),
      subtotal: cart.subtotal,
      discount: cart.discount,
      total: cart.total,
      paymentMethod: payment.selectedMethod?.label || 'Não informado',
      pickupCode: pickupCode.value
    }

    const result = await printComplete(orderData)

    if (result.success) {
      printSuccess.value = true
    } else {
      printError.value = result.message || 'Erro ao imprimir'
    }
  } catch (error) {
    printError.value = error.message || 'Erro ao imprimir comprovante'
    console.error('[SuccessView] Erro ao imprimir:', error)
  }
}

function resetAndGoHome() {
  cart.clearCart()
  payment.resetPayment()
  session.endSession()
  router.replace({ name: 'home' })
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
  background: linear-gradient(
    135deg,
    #f0fdf4 0%,
    #e8fdf0 50%,
    #dffce7 100%
  );
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
  font-size: 5rem;
  color: white;
  line-height: 1;
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
