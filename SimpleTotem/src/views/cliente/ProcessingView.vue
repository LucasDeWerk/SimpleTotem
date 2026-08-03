<template>
  <div class="processing-view">
    <div class="processing-content animate-fade-in">

      <template v-if="!erro">
        <div v-if="!mostrarQr" class="processing-spinner">
          <div class="spinner-ring"></div>
        </div>

        <h2 class="processing-headline">
          {{ mostrarQr ? lang.t.scanPixQr : lang.t.processingPayment }}
        </h2>

        <p v-if="mensagemAtual" class="processing-message">{{ mensagemAtual }}</p>
        <p v-else-if="mostrarQr" class="processing-subheadline">{{ lang.t.scanPixHint }}</p>
        <p v-else class="processing-subheadline">{{ lang.t.followPinpad }}</p>

        <PixQrCode
          v-if="mostrarQr && qrcodePayload"
          :payload="qrcodePayload"
        />

        <p v-if="mensagemRodape" class="processing-footer-msg">{{ mensagemRodape }}</p>

        <p class="processing-help">{{ lang.t.processingHelp }}</p>
        <p class="processing-cancel-hint">{{ lang.t.cancelViaPinpad }}</p>

        <div class="processing-actions">
          <button class="processing-secondary-btn" type="button" @click="voltar">
            {{ lang.t.backToMenu }}
          </button>
        </div>
      </template>

      <template v-else>
        <div class="processing-error-icon">✕</div>
        <h2 class="processing-headline error">{{ lang.t.paymentNotApproved }}</h2>
        <p class="processing-subheadline">{{ erro }}</p>
        <div class="processing-error-actions">
          <PrimaryActionButton
            :label="lang.t.tryAgain"
            :fullWidth="true"
            @click="voltar"
          />
          <button class="processing-cancel-btn" type="button" @click="encerrarPedido">
            {{ lang.t.cancelOrder }}
          </button>
        </div>
      </template>

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
import PrimaryActionButton from '@/components/shared/PrimaryActionButton.vue'
import PixQrCode from '@/components/shared/PixQrCode.vue'

const router = useRouter()
const cart = useCartStore()
const payment = usePaymentStore()
const session = useSessionStore()
const lang = useLanguageStore()

const erro = ref('')

const txStatus = computed(() => payment.transactionStatus)

const mostrarQr = computed(() =>
  Boolean(txStatus.value?.qrcode_ativo && txStatus.value?.qrcode)
)

const qrcodePayload = computed(() => txStatus.value?.qrcode || '')

const mensagemAtual = computed(() => txStatus.value?.mensagem_atual || '')

const mensagemRodape = computed(() => {
  const msgs = txStatus.value?.mensagens || []
  if (msgs.length < 2) return ''
  return msgs[msgs.length - 1] !== mensagemAtual.value ? msgs[msgs.length - 1] : ''
})

const iniciou = ref(false)

onMounted(async () => {
  if (iniciou.value) return
  iniciou.value = true
  session.pauseSession()

  payment.setCompletedOrder(cart)
  const ok = await payment.iniciarTransacao(cart)
  if (ok) {
    cart.clearCart()
    router.push({ name: 'success' })
  } else {
    erro.value = payment.errorMessage || lang.t.paymentError
  }
})

function voltar() {
  payment.resetPayment()
  router.push({ name: 'payment' })
}

/** Só disponível após o pagamento já ter finalizado (negado/erro) — nesse
 * ponto não há mais transação ativa no pinpad para cancelar, então só
 * encerra o pedido e volta ao catálogo. */
function encerrarPedido() {
  payment.resetPayment()
  router.push({ name: 'catalog' })
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
  gap: var(--space-lg);
  text-align: center;
  padding: var(--space-2xl);
  max-width: 560px;
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
  border-top-color: var(--color-primary);
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
  color: var(--color-error);
}

.processing-subheadline,
.processing-message {
  font-size: var(--font-size-lg);
  color: #64748b;
  font-weight: 500;
  max-width: 480px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.processing-footer-msg {
  font-size: var(--font-size-md);
  color: #94a3b8;
  font-weight: 500;
}

.processing-help {
  font-size: var(--font-size-md);
  color: #94a3b8;
  font-weight: 500;
  max-width: 400px;
  line-height: 1.5;
}

.processing-cancel-hint {
  font-size: var(--font-size-md);
  color: var(--color-primary);
  font-weight: 600;
  max-width: 400px;
  line-height: 1.5;
}

.processing-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  width: 100%;
  max-width: 360px;
  margin-top: var(--space-md);
}

.processing-error-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(244, 67, 54, 0.1);
  color: var(--color-error);
  font-size: 2.5rem;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
}

.processing-error-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  width: 100%;
  max-width: 360px;
  margin-top: var(--space-md);
}

.processing-cancel-btn,
.processing-secondary-btn {
  min-height: var(--btn-min-height);
  padding: var(--space-md) var(--space-xl);
  border-radius: var(--radius-md);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  letter-spacing: 0.5px;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.processing-cancel-btn {
  background: transparent;
  border: 2px solid var(--color-border);
  color: #64748b;
}

.processing-secondary-btn {
  background: rgba(245, 124, 0, 0.08);
  border: 2px solid rgba(245, 124, 0, 0.15);
  color: var(--color-primary);
}

.processing-cancel-btn:active,
.processing-secondary-btn:active {
  background: var(--bg-color-secondary);
}
</style>
