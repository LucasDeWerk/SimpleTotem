import { ref } from 'vue'

/**
 * Composable para usar a impressora térmica
 */
export function useThermalPrinter() {
  const printing = ref(false)
  const printError = ref(null)
  const lastPrintResult = ref(null)

  /**
   * Envia linhas de texto para a impressora
   * @param {string[]} lines - Array de strings
   * @param {object} options - { skipInit, skipCut }
   */
  async function printLines(lines, options = {}) {
    try {
      printing.value = true
      printError.value = null

      if (!window.electronAPI?.printer) {
        throw new Error('API de impressora não disponível')
      }

      const result = await window.electronAPI.printer.printLines(lines, options)
      lastPrintResult.value = result

      if (!result.success) {
        printError.value = result.message || 'Erro ao imprimir'
      }

      return result
    } catch (error) {
      printError.value = error.message
      console.error('[Printer] Erro:', error)
      return { success: false, message: error.message }
    } finally {
      printing.value = false
    }
  }

  /**
   * Envia buffer raw para a impressora
   * @param {ArrayBuffer|Uint8Array} bufferData
   */
  async function printRaw(bufferData) {
    try {
      printing.value = true
      printError.value = null

      if (!window.electronAPI?.printer) {
        throw new Error('API de impressora não disponível')
      }

      const result = await window.electronAPI.printer.printRaw(bufferData)
      lastPrintResult.value = result

      if (!result.success) {
        printError.value = result.message || 'Erro ao imprimir'
      }

      return result
    } catch (error) {
      printError.value = error.message
      console.error('[Printer] Erro:', error)
      return { success: false, message: error.message }
    } finally {
      printing.value = false
    }
  }

  const RECEIPT_WIDTH = 48

  function center(text) {
    const t = String(text || '')
    if (t.length >= RECEIPT_WIDTH) return t.substring(0, RECEIPT_WIDTH)
    const pad = Math.floor((RECEIPT_WIDTH - t.length) / 2)
    return ' '.repeat(pad) + t
  }

  function formatMoney(value) {
    return `R$ ${Number(value || 0).toFixed(2)}`
  }

  /**
   * Monta e imprime o comprovante do pedido.
   */
  function buildReceiptLines(orderData) {
    const sep = '-'.repeat(RECEIPT_WIDTH)
    const lines = [
      '',
      center(orderData.company?.name || 'SIMPLETOTEM'),
      center(orderData.company?.cnpj || ''),
      sep,
      center(`Pedido #${orderData.orderNumber || '—'}`),
      center(orderData.date || ''),
      sep,
    ]

    for (const item of orderData.items || []) {
      const qty = item.quantity ?? 1
      const total = qty * (item.unitPrice ?? 0)
      lines.push(`${item.name}`.substring(0, RECEIPT_WIDTH))
      lines.push(`  ${qty}x ${formatMoney(item.unitPrice)} = ${formatMoney(total)}`)
    }

    lines.push(sep)
    lines.push(`Subtotal:${' '.repeat(RECEIPT_WIDTH - 9 - formatMoney(orderData.subtotal).length)}${formatMoney(orderData.subtotal)}`)

    if (orderData.discount > 0) {
      lines.push(`Desconto:${' '.repeat(RECEIPT_WIDTH - 9 - formatMoney(orderData.discount).length)}-${formatMoney(orderData.discount)}`)
    }

    lines.push(`TOTAL:${' '.repeat(RECEIPT_WIDTH - 6 - formatMoney(orderData.total).length)}${formatMoney(orderData.total)}`)
    lines.push(`Pagamento: ${orderData.paymentMethod || '—'}`)

    if (orderData.pickupCode) {
      lines.push(sep)
      lines.push(center('Codigo'))
      lines.push(center(String(orderData.pickupCode)))
    }

    lines.push(sep, '', '')
    return lines
  }

  async function printComplete(orderData) {
    const lines = buildReceiptLines(orderData)
    return printLines(lines, { cut: true })
  }

  /**
   * Testa a impressora
   */
  async function testPrint() {
    try {
      printing.value = true
      printError.value = null

      if (!window.electronAPI?.printer) {
        throw new Error('API de impressora não disponível')
      }

      const result = await window.electronAPI.printer.testPrint()
      lastPrintResult.value = result

      if (!result.success) {
        printError.value = result.message || 'Erro no teste de impressão'
      }

      return result
    } catch (error) {
      printError.value = error.message
      console.error('[Printer] Erro:', error)
      return { success: false, message: error.message }
    } finally {
      printing.value = false
    }
  }

  return {
    printing,
    printError,
    lastPrintResult,
    printLines,
    printRaw,
    printComplete,
    testPrint,
  }
}
