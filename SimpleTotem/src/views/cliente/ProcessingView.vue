<template>
  <div class="processing-view">
    <div class="processing-content animate-fade-in">

      <!-- ANULA físico no pinpad (Seq. 9) — a CliSiTef está bloqueada esperando
           a confirmação real, não pode ser respondida sozinha. -->
      <template v-if="aguardandoConfirmacaoCancelamento">
        <div class="processing-error-icon">?</div>
        <h2 class="processing-headline">{{ lang.t.cancelConfirmTitle }}</h2>
        <p class="processing-subheadline">
          {{ aguardandoConfirmacaoCancelamento.mensagem || lang.t.cancelConfirmDefaultMsg }}
        </p>
        <div class="processing-error-actions">
          <PrimaryActionButton
            :label="lang.t.cancelConfirmYes"
            :fullWidth="true"
            :disabled="enviandoConfirmacaoCancelamento"
            @click="responderCancelamento(true)"
          />
          <button
            class="processing-cancel-btn"
            type="button"
            :disabled="enviandoConfirmacaoCancelamento"
            @click="responderCancelamento(false)"
          >
            {{ lang.t.cancelConfirmNo }}
          </button>
        </div>
      </template>

      <template v-else-if="!erro">
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
      </template>

      <template v-else>
        <div class="processing-error-icon">✕</div>
        <!-- Requisito Fiserv: exibir TODAS as mensagens/códigos retornados, sem
             alteração. mensagemOperador é o texto literal que a CliSiTef mandou
             durante o fluxo (ex.: "Sem conexao Servidor"); codigoRetornado é o
             código numérico do resultado final + nossa descrição (claramente
             rotulada como interna) — os dois são dados distintos e nenhum dos
             dois pode sumir, mesmo quando só um deles existe. -->
        <h2 class="processing-headline error">{{ mensagemOperador || codigoRetornado || lang.t.paymentNotApproved }}</h2>
        <p v-if="mensagemOperador || codigoRetornado" class="processing-subheadline">{{ lang.t.paymentNotApproved }}</p>
        <p v-else class="processing-subheadline">{{ erro }}</p>
        <p v-if="mensagemOperador && codigoRetornado" class="processing-code">{{ codigoRetornado }}</p>
        <p v-if="dicaPinpadTimeout" class="processing-subheadline">{{ dicaPinpadTimeout }}</p>
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
import { confirmarCancelamentoTransacao } from '@/services/api'

const router = useRouter()
const cart = useCartStore()
const payment = usePaymentStore()
const session = useSessionStore()
const lang = useLanguageStore()

const erro = ref('')
const enviandoConfirmacaoCancelamento = ref(false)

const txStatus = computed(() => payment.transactionStatus)

// Requisito Fiserv: os dois vêm de campos independentes do backend — um não
// deve mascarar o outro (ver template).
const mensagemOperador = computed(() => txStatus.value?.mensagem_atual || '')
const codigoRetornado = computed(() => txStatus.value?.erro || '')

// Código -43 ("Problema na execução de rotina no pinpad") é o mesmo que
// aparece quando o pinpad estoura o próprio timeout esperando o cartão —
// dica adicional, sem substituir o dado real da CliSiTef acima.
const dicaPinpadTimeout = computed(() =>
  txStatus.value?.resultado_codigo === -43 ? lang.t.pinpadTimeoutHint : ''
)

const mostrarQr = computed(() =>
  Boolean(txStatus.value?.qrcode_ativo && txStatus.value?.qrcode)
)

const qrcodePayload = computed(() => txStatus.value?.qrcode || '')

const mensagemAtual = computed(() => txStatus.value?.mensagem_atual || '')

const aguardandoConfirmacaoCancelamento = computed(() => txStatus.value?.aguardando_confirmacao_cancelamento || null)

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

/** Responde a pergunta real da CliSiTef disparada pelo ANULA físico do
 * pinpad (Seq. 9) — a atualização de tela acontece no próximo polling. */
async function responderCancelamento(confirma) {
  const tid = txStatus.value?.transacao_id
  if (!tid || enviandoConfirmacaoCancelamento.value) return
  enviandoConfirmacaoCancelamento.value = true
  try {
    await confirmarCancelamentoTransacao(tid, confirma)
  } catch (err) {
    console.error('[ProcessingView] Erro ao responder confirmação de cancelamento:', err)
  } finally {
    enviandoConfirmacaoCancelamento.value = false
  }
}

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

.processing-code {
  font-size: var(--font-size-sm);
  color: #94a3b8;
  font-weight: 500;
  max-width: 480px;
  line-height: 1.4;
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

.processing-cancel-btn {
  min-height: var(--btn-min-height);
  padding: var(--space-md) var(--space-xl);
  border-radius: var(--radius-md);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  letter-spacing: 0.5px;
  cursor: pointer;
  transition: background var(--transition-fast);
  background: transparent;
  border: 2px solid var(--color-border);
  color: #64748b;
}

.processing-cancel-btn:active {
  background: var(--bg-color-secondary);
}
</style>
