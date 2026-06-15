import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  obterMetodosPagamento,
  iniciarTransacao as apiIniciarTransacao,
  obterStatusTransacao,
} from '@/services/api'

const STATUS_FINAL = ['aprovada', 'negada', 'erro']

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
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
  let transacaoEmCurso = false

  function selectMethod(method) {
    selectedMethod.value = method
  }

  async function fetchPaymentMethods() {
    loadingMethods.value = true
    methodsLoadError.value = false
    try {
      const methods = await obterMetodosPagamento()
      availableMethods.value = methods || []
    } catch (err) {
      console.error('[Payment] Erro ao buscar métodos de pagamento:', err)
      availableMethods.value = []
      methodsLoadError.value = true
    } finally {
      loadingMethods.value = false
    }
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
        quantidade: item.quantity,
        preco_unitario: item.unitPrice,
      }))

      const payload = {
        itens,
        total_cliente: vendaCalculada?.total ?? cartStore.total,
        metodo_pagamento_id: selectedMethod.value.type,
      }

      const inicio = await apiIniciarTransacao(payload)
      const resultado = await aguardarTransacao(inicio.transacao_id)

      if (resultado.status === 'aprovada') {
        transactionResult.value = {
          status: 'aprovada',
          transacao_id: inicio.transacao_id,
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
    selectMethod,
    fetchPaymentMethods,
    iniciarTransacao,
    setCompletedOrder,
    resetPayment,
  }
})
