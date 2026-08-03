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
        <div v-if="codigoSenha" class="detail-row senha-row">
          <span class="detail-label">Retire seu pedido</span>
          <span class="detail-value senha-codigo">{{ codigoSenha }}</span>
        </div>
      </div>

      <!-- Cupom fiscal -->
      <div v-if="mostrarCupomFiscal" class="cupom-fiscal-section">
        <button
          v-if="!cupomEmitido"
          class="btn-cupom"
          type="button"
          :disabled="emitindoCupom"
          @click="emitirCupomFiscal"
        >
          <span v-if="emitindoCupom" class="spinner-small"></span>
          {{ emitindoCupom ? 'Emitindo...' : 'Emitir Cupom Fiscal' }}
        </button>
        <p v-if="cupomEmitido" class="cupom-success">✓ Cupom emitido com sucesso</p>
        <p v-if="cupomErro" class="cupom-error">⚠️ {{ cupomErro }}</p>
      </div>

      <!-- Escolha de comprovante TEF (Fiserv req. 2) -->
      <div v-if="showReceiptChoice && !receiptChosen" class="receipt-choice">
        <p class="receipt-choice-title">Deseja imprimir o comprovante?</p>
        <div class="receipt-choice-buttons">
          <PrimaryActionButton
            label="Imprimir comprovante"
            :fullWidth="true"
            @click="chooseReceipt('imprimir')"
          />
          <button class="receipt-skip-btn" type="button" @click="chooseReceipt('nao')">
            Não quero comprovante
          </button>
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
import { useSimpleSfiqueStore } from '@/stores/simplesfique'
import { useSettingsStore } from '@/stores/settings'
import { useThermalPrinter } from '@/composables/useThermalPrinter'
import PrimaryActionButton from '@/components/shared/PrimaryActionButton.vue'
import { confirmarPagamento, obterEmpresaSinc } from '@/services/api'

const router = useRouter()
const cart = useCartStore()
const payment = usePaymentStore()
const session = useSessionStore()
const lang = useLanguageStore()
const sfique = useSimpleSfiqueStore()
const settings = useSettingsStore()
const { printing, printComplete, printLines, printProductTickets } = useThermalPrinter()

const countdown = ref(10)
const printError = ref(null)
const printSuccess = ref(false)
const emitindoCupom = ref(false)
const cupomEmitido = ref(false)
const cupomErro = ref('')
const receiptChosen = ref(false)
const empresaInfo = ref(null)

const order = computed(() => payment.completedOrder)
const tx = computed(() => payment.transactionResult)

// Fiserv req. 2 — só exibe escolha se há impressora e dados de comprovante
const showReceiptChoice = computed(() =>
  Boolean(window.electronAPI?.printer) && Boolean(
    tx.value?.cupom_bruto ||
    tx.value?.linhas_cupom?.some(b => String(b).length > 0) ||
    tx.value?.nsu_sitef
  )
)

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

const codigoSenha = computed(() => tx.value?.codigo_senha || '')
const mostrarCupomFiscal = computed(() => Boolean(tx.value?.emite_cupom_fiscal))

let timer = null

onMounted(async () => {
  session.pauseSession()

  // Dados reais da empresa para o cabeçalho do cupom (evita placeholder tipo "SIMPLETOTEM")
  try {
    empresaInfo.value = await obterEmpresaSinc()
  } catch (err) {
    console.warn('[SuccessView] Não foi possível obter dados da empresa para o cupom:', err.message)
  }

  // venda-completa já emitiu o cupom internamente — não precisa emitir de novo
  if (tx.value?.cupom_fiscal) {
    cupomEmitido.value = true
  }

  // Se não há impressora ou não há dados de comprovante, confirma imediatamente (sem impressão)
  if (!showReceiptChoice.value) {
    receiptChosen.value = true
    await _confirmarSiTef(true)
  }

  // Caso haja impressora, a confirmação ocorre em chooseReceipt() após impressão

  // Tickets de produção por produto (ex.: cozinha) — independem da escolha do comprovante do cliente
  if (settings.imprimirTicketsIndividuais && window.electronAPI?.printer) {
    const resultado = await printProductTickets(order.value?.items, orderNumber.value)
    if (resultado.failed.length) {
      console.warn('[SuccessView] Falha ao imprimir alguns tickets de produção:', resultado.failed)
    }
  }

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

async function chooseReceipt(choice) {
  receiptChosen.value = true
  if (choice === 'imprimir') {
    const impressaoOk = await printReceipt()
    await _confirmarSiTef(impressaoOk)
  } else {
    // Usuário optou por não imprimir — não é falha, confirma normalmente
    await _confirmarSiTef(true)
  }
}

async function _confirmarSiTef(impressaoOk) {
  const tid = tx.value?.transacao_id
  if (!tid) return  // não é transação SiTef local, não precisa confirmar
  try {
    await confirmarPagamento({
      transacao_id: tid,
      confirma: impressaoOk ? 1 : 0,
      impressao_ok: impressaoOk,
      xml_emitido: true,  // sem integração NF-e: sempre true
      codigo_senha: codigoSenha.value || null,
      cupom_fiscal: tx.value?.cupom_fiscal || null,
    })
    if (!impressaoOk) {
      printError.value = (printError.value || '') + ' — pagamento desfeito automaticamente'
    }
  } catch (err) {
    console.error('[SuccessView] Erro ao confirmar SiTef:', err)
  }
}

async function printReceipt() {
  try {
    if (!window.electronAPI?.printer) {
      printError.value = 'Impressora indisponível (abra pelo Electron, não pelo navegador)'
      return false
    }

    // 1) Cupom TEF bruto — exatamente como a Fiserv/SiTef enviou (TC 122)
    const cupomBruto = tx.value?.cupom_bruto
    const blocosTef = tx.value?.linhas_cupom || []
    const temCupomTef = Boolean(cupomBruto) || blocosTef.some(b => String(b).length > 0)
    if (temCupomTef) {
      const payload = cupomBruto ? [cupomBruto] : blocosTef
      console.log('[SuccessView] Imprimindo cupom bruto TEF:', payload.join('').length, 'chars')
      const result = await printLines(payload, { cut: true, cupomFiserv: true })
      if (result.success) { printSuccess.value = true; return true }
      printError.value = result.message || lang.t.printError
      return false
    }

    // 2) Recibo do pedido (itens + total)
    if (order.value?.items?.length) {
      const orderData = {
        company: {
          name: empresaInfo.value?.nome_fantasia || empresaInfo.value?.razao_social || 'SIMPLETOTEM',
          cnpj: empresaInfo.value?.cpf_cnpj || '',
        },
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
        pickupCode: codigoSenha.value || authCode.value,
      }
      console.log('[SuccessView] Imprimindo recibo do pedido')
      const result = await printComplete(orderData)
      if (result.success) { printSuccess.value = true; return true }
      printError.value = result.message || lang.t.printError
      return false
    }

    // 3) Comprovante mínimo com dados da transação
    const minimal = buildMinimalTxLines()
    if (minimal.length > 3) {
      console.log('[SuccessView] Imprimindo comprovante mínimo TEF')
      const result = await printLines(minimal, { cut: true })
      if (result.success) { printSuccess.value = true; return true }
      printError.value = result.message || lang.t.printError
      return false
    }

    printError.value = 'Sem dados para impressão'
    console.warn('[SuccessView] Nada para imprimir — tx:', tx.value, 'order:', order.value)
    return false
  } catch (error) {
    printError.value = error.message || lang.t.printError
    console.error('[SuccessView] Erro ao imprimir:', error)
    return false
  }
}

async function emitirCupomFiscal() {
  // venda-completa já emitiu internamente — apenas marca como feito
  if (tx.value?.cupom_fiscal) {
    cupomEmitido.value = true
    return
  }
  // Fallback: fluxo separado (seção 5 da doc) com emissão manual
  if (!tx.value?.cupom_fiscal_id) return
  emitindoCupom.value = true
  cupomErro.value = ''
  try {
    await sfique.emitirCupom(tx.value.cupom_fiscal_id)
    cupomEmitido.value = true
  } catch (err) {
    cupomErro.value = err.message || 'Erro ao emitir cupom fiscal'
  } finally {
    emitindoCupom.value = false
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

.senha-row {
  margin-top: var(--space-sm);
  padding-top: var(--space-sm);
  border-top: 1px solid rgba(76, 175, 80, 0.15);
}

.senha-codigo {
  font-size: 3rem;
  font-weight: 900;
  color: var(--color-primary, #f57c00);
  line-height: 1;
}

.cupom-fiscal-section {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-sm);
}

.btn-cupom {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  min-height: var(--btn-min-height, 52px);
  padding: var(--space-md) var(--space-2xl);
  background: var(--color-primary, #f57c00);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-lg);
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-cupom:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.cupom-success {
  color: #4caf50;
  font-size: var(--font-size-sm);
  font-weight: 700;
}

.cupom-error {
  color: #ef4444;
  font-size: var(--font-size-sm);
  font-weight: 600;
}

/* Mesmo padrão de success-details — card verde */
.receipt-choice {
  width: 100%;
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.08), rgba(76, 175, 80, 0.04));
  border: 1px solid rgba(76, 175, 80, 0.15);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-lg);
}

.receipt-choice-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: #0f172a;
  text-align: center;
}

.receipt-choice-buttons {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  width: 100%;
}

/* Botão secundário segue o padrão payment-secondary-btn da PaymentView */
.receipt-skip-btn {
  width: 100%;
  min-height: var(--btn-min-height);
  padding: var(--space-md) var(--space-xl);
  background: transparent;
  border: 2px solid var(--color-primary);
  border-radius: var(--radius-md);
  color: var(--color-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  letter-spacing: 0.5px;
  text-transform: uppercase;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.receipt-skip-btn:active {
  background: var(--color-primary-light);
}
</style>
