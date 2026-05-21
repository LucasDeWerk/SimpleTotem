import { defineStore } from 'pinia'
import { ref } from 'vue'
import { obterMetodosPagamento, iniciarTransacao as apiIniciarTransacao } from '@/services/api'

export const usePaymentStore = defineStore('payment', () => {
  const selectedMethod = ref(null)
  const status = ref('idle') // idle | processing | success | error
  const transactionResult = ref(null)  // resposta completa do backend
  const errorMessage = ref('')
  const availableMethods = ref([])

  function selectMethod(method) {
    selectedMethod.value = method
  }

  async function fetchPaymentMethods() {
    try {
      const methods = await obterMetodosPagamento()
      availableMethods.value = methods || []
    } catch (err) {
      console.error('[Payment] Erro ao buscar métodos de pagamento:', err)
      availableMethods.value = []
    }
  }

  /**
   * Inicia a transação no backend (SiTef + gravação + cupom).
   * Bloqueante — aguarda o retorno sem timeout.
   *
   * @param {object} cartStore  instância do useCartStore
   */
  async function iniciarTransacao(cartStore) {
    if (!selectedMethod.value) return false

    status.value = 'processing'
    errorMessage.value = ''
    transactionResult.value = null

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

      const resultado = await apiIniciarTransacao(payload)
      transactionResult.value = resultado

      // Imprime cupom via Electron se disponível
      if (resultado.linhas_cupom?.length && window.printerAPI?.printLines) {
        window.printerAPI.printLines(resultado.linhas_cupom, { cut: true })
          .catch(err => console.warn('[Payment] Erro ao imprimir cupom:', err))
      }

      status.value = 'success'
      return true
    } catch (err) {
      status.value = 'error'
      errorMessage.value = err.message || 'Erro ao processar pagamento'
      console.error('[Payment] Erro em iniciarTransacao:', err)
      return false
    }
  }

  function resetPayment() {
    selectedMethod.value = null
    status.value = 'idle'
    transactionResult.value = null
    errorMessage.value = ''
  }

  return {
    selectedMethod,
    status,
    transactionResult,
    errorMessage,
    availableMethods,
    selectMethod,
    fetchPaymentMethods,
    iniciarTransacao,
    resetPayment,
  }
})


