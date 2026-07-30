import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  iniciarTransacao as apiIniciarTransacao,
  obterStatusTransacao,
  sfVendaCompleta,
} from '@/services/api'
import { useDeviceStore } from '@/stores/device'
import { useSimpleSfiqueStore } from '@/stores/simplesfique'

const STATUS_FINAL = ['aprovada', 'negada', 'erro']

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

// IDs/descrições do SimplesFique para formas aceitas no totem
const SFIQUE_ID_MAP = {
  '3':  { forma: 'credito', label: 'Cartão de Crédito', sitef: 2  },
  '4':  { forma: 'debito',  label: 'Cartão de Débito',  sitef: 3  },
  '17': { forma: 'pix',     label: 'PIX',               sitef: 122 },
  '20': { forma: 'pix',     label: 'PIX',               sitef: 122 },
}

function normalizeMetodoId(rawId) {
  return String(rawId ?? '').replace(/^0+/, '') || '0'
}

function inferFormaPorDescricao(descricao = '') {
  const d = String(descricao).toLowerCase()
  if (d.includes('cred')) return 'credito'
  if (d.includes('deb')) return 'debito'
  // apenas 'pix' e 'instantaneo' são aceitos — carteira digital e transferência ficam de fora
  if (d.includes('pix') || d.includes('instantaneo')) return 'pix'
  return null
}

function mapFormapagamento(tipo, descricao = '') {
  const normalized = normalizeMetodoId(tipo)
  return SFIQUE_ID_MAP[normalized]?.forma ?? inferFormaPorDescricao(descricao) ?? 'dinheiro'
}

export const usePaymentStore = defineStore('payment', () => {
  const selectedMethod = ref(null)
  const status = ref('idle') // idle | processing | success | error
  const transactionResult = ref(null)
  const transactionStatus = ref(null)
  const errorMessage = ref('')
  const availableMethods = ref([])
  const completedOrder = ref(null)
  const loadingMethods = ref(false)
  const methodsLoadError = ref(false)
  const tipoParcelamento = ref('a_vista')
  const numParcelas = ref(1)
  // Dados guardados para retry quando venda-completa falha após pagamento aprovado
  const registroPendente = ref(null)
  let transacaoEmCurso = false

  function selectMethod(method) {
    selectedMethod.value = method
  }

  function setParcelamento(tipo, parcelas) {
    tipoParcelamento.value = tipo || 'a_vista'
    numParcelas.value = parcelas || 1
  }

  // Métodos fixos — crédito, débito e PIX cobrem os casos de uso do totem
  const METODOS_FIXOS = [
    { type: '3', rawType: '3', label: 'Cartão de Crédito', descricao: 'Cartão de Crédito', available: true },
    { type: '4', rawType: '4', label: 'Cartão de Débito', descricao: 'Cartão de Débito', available: true },
    { type: '17', rawType: '17', label: 'PIX', descricao: 'PIX', available: true },
  ]

  async function fetchPaymentMethods() {
    loadingMethods.value = true
    methodsLoadError.value = false
    availableMethods.value = METODOS_FIXOS
    loadingMethods.value = false
  }

  async function aguardarTransacao(transacaoId) {
    const deadline = Date.now() + 5 * 60 * 1000
    let pollsAprovada = 0

    while (true) {
      if (Date.now() > deadline) {
        throw new Error('Tempo esgotado aguardando o pagamento no pinpad')
      }

      const atual = await obterStatusTransacao(transacaoId)
      transactionStatus.value = atual

      if (STATUS_FINAL.includes(atual.status)) {
        if (atual.status === 'aprovada') {
          const temDados = Boolean(
            atual.cupom_bruto ||
            atual.linhas_cupom?.length ||
            atual.nsu_sitef ||
            atual.autorizacao
          )
          if (temDados || pollsAprovada >= 6) {
            return atual
          }
          pollsAprovada++
        } else {
          return atual
        }
      }

      await sleep(500)
    }
  }

  /**
   * Registra o pedido via venda-completa após aprovação SiTef.
   * Se o terminal emite cupom fiscal, propaga o erro (o caller decide o que fazer).
   * Caso contrário, falha silenciosa — não cancela o pagamento já aprovado.
   */
  async function registrarPedidoSfique(cartItems, txResult) {
    const sfique = useSimpleSfiqueStore()

    if (!sfique.isConfigured) {
      if (sfique.emiteCupomFiscal) {
        throw new Error('Terminal não configurado — cupom fiscal não pode ser emitido')
      }
      console.warn('[Payment] SimplesFique não configurado — pedido não registrado')
      return
    }

    const { terminalToken } = sfique

    const itensSfique = cartItems.map(item => ({
      produto_id: item.productId ?? null,
      menu_id: item.menu_id ?? null,
      ambiente_preparo_id: item.ambiente_preparo_id ?? null,
      nome_produto: item.name,
      quantidade: item.quantity,
      valor_unitario: item.unitPrice,
      emite_ticket: item.emite_ticket ?? false,
      observacao: item.notes || null,
    }))

    const formaRaw = selectedMethod.value?.type || ''
    const formaPagamento = mapFormapagamento(formaRaw, selectedMethod.value?.descricao || '')

    const payload = {
      itens: itensSfique,
      pagamento: {
        forma_pagamento: formaPagamento,
        gateway: 'fiserv',
        transaction_id: txResult.transacao_id || null,
        nsu: txResult.nsu_sitef || null,
        codigo_autorizacao: txResult.autorizacao || null,
      },
      idempotency_key: crypto.randomUUID(),
    }

    try {
      const resp = await sfVendaCompleta(payload, terminalToken)
      const codigoSenha = resp?.pedido?.codigo_senha || null
      const cupomFiscal = resp?.cupom_fiscal || null
      const cupomFiscalId = resp?.cupom_fiscal?.cupom?.id || null

      if (transactionResult.value) {
        transactionResult.value = {
          ...transactionResult.value,
          codigo_senha: codigoSenha,
          cupom_fiscal: cupomFiscal,
          cupom_fiscal_id: cupomFiscalId,
          emite_cupom_fiscal: Boolean(cupomFiscal),
        }
      }

      console.log('[Payment] ✅ Pedido registrado via venda-completa — senha:', codigoSenha)
    } catch (err) {
      if (sfique.emiteCupomFiscal) {
        // Terminal precisa do XML — propaga para o caller tratar
        throw err
      }
      console.warn('[Payment] ⚠️ Falha ao registrar pedido (pagamento já aprovado):', err.message)
    }
  }

  /**
   * Retenta apenas a venda-completa sem refazer o pagamento no pinpad.
   * Chamado pela ProcessingView quando há registroPendente.
   */
  async function retryRegistroPedido() {
    if (!registroPendente.value) return false
    status.value = 'processing'
    errorMessage.value = ''
    try {
      const { items, txResult } = registroPendente.value
      await registrarPedidoSfique(items, txResult)
      registroPendente.value = null
      status.value = 'success'
      return true
    } catch (err) {
      status.value = 'error'
      errorMessage.value = err.message || 'Falha ao confirmar pedido'
      console.error('[Payment] Retry registro falhou:', err)
      return false
    }
  }

  /**
   * Inicia transação SiTef (cartão ou PIX) e faz polling até concluir.
   */
  async function iniciarTransacao(cartStore) {
    if (!selectedMethod.value) return false
    if (transacaoEmCurso) {
      console.warn('[Payment] Transação já em andamento — ignorando duplicata')
      return false
    }
    transacaoEmCurso = true

    status.value = 'processing'
    errorMessage.value = ''
    transactionResult.value = null
    transactionStatus.value = null

    try {
      const vendaCalculada = cartStore.vendaCalculada
      const itens = cartStore.items.map(item => ({
        produto_id: item.productId,
        descricao: item.name,
        quantidade: Number(item.quantity),
        preco_unitario: Number(item.unitPrice),
      }))

      const device = useDeviceStore()
      const payload = {
        itens,
        total_cliente: Number(vendaCalculada?.total ?? cartStore.total),
        metodo_pagamento_id: selectedMethod.value.type,
        id_terminal: device.terminalId || undefined,
        tipo_parcelamento: tipoParcelamento.value,
        num_parcelas: numParcelas.value,
      }

      const inicio = await apiIniciarTransacao(payload)
      const resultado = await aguardarTransacao(inicio.transacao_id)

      if (resultado.status === 'aprovada') {
        transactionResult.value = {
          status: 'aprovada',
          transacao_id: inicio.transacao_id,
          id_venda: resultado.id_venda || null,
          nsu_sitef: resultado.nsu_sitef || '',
          nsu_host: resultado.nsu_host || '',
          autorizacao: resultado.autorizacao || '',
          modalidade: resultado.modalidade || '',
          bandeira: resultado.bandeira || '',
          total_cobrado: resultado.total_cobrado ?? cartStore.total,
          linhas_cupom: resultado.linhas_cupom || [],
          cupom_bruto: resultado.cupom_bruto || '',
          pix: resultado.pix || false,
        }

        try {
          await registrarPedidoSfique(cartStore.items, transactionResult.value)
        } catch (err) {
          // Pagamento aprovado mas venda-completa falhou e terminal precisa de XML
          registroPendente.value = {
            items: cartStore.items.map(i => ({ ...i })),
            txResult: { ...transactionResult.value },
          }
          status.value = 'error'
          errorMessage.value = 'Pagamento aprovado! Aguardando confirmação fiscal...'
          console.error('[Payment] Registro bloqueado por falha na venda-completa:', err.message)
          return false
        }

        status.value = 'success'
        return true
      }

      status.value = 'error'
      const msgSiTef = resultado.mensagem_atual
        || (resultado.mensagens?.length ? resultado.mensagens[resultado.mensagens.length - 1] : '')
      errorMessage.value = msgSiTef
        || resultado.erro
        || (resultado.resultado_codigo != null
          ? `Transação não aprovada (código ${resultado.resultado_codigo})`
          : 'Pagamento não aprovado')
      return false
    } catch (err) {
      status.value = 'error'
      errorMessage.value = err.message || 'Erro ao processar pagamento'
      console.error('[Payment] Erro em iniciarTransacao:', err)
      return false
    } finally {
      transacaoEmCurso = false
    }
  }

  function resetPayment() {
    selectedMethod.value = null
    status.value = 'idle'
    transactionResult.value = null
    transactionStatus.value = null
    errorMessage.value = ''
    completedOrder.value = null
    methodsLoadError.value = false
    tipoParcelamento.value = 'a_vista'
    numParcelas.value = 1
    registroPendente.value = null
    transacaoEmCurso = false
  }

  function setCompletedOrder(cartStore) {
    completedOrder.value = {
      items: cartStore.items.map(item => ({ ...item })),
      subtotal: cartStore.vendaCalculada?.subtotal ?? cartStore.subtotal,
      discount: cartStore.vendaCalculada?.desconto ?? cartStore.discount,
      total: cartStore.vendaCalculada?.total ?? cartStore.total,
      paymentMethod: selectedMethod.value?.label || '',
    }
  }

  return {
    selectedMethod,
    status,
    transactionResult,
    transactionStatus,
    errorMessage,
    availableMethods,
    completedOrder,
    loadingMethods,
    methodsLoadError,
    tipoParcelamento,
    numParcelas,
    selectMethod,
    setParcelamento,
    fetchPaymentMethods,
    iniciarTransacao,
    setCompletedOrder,
    resetPayment,
  }
})
