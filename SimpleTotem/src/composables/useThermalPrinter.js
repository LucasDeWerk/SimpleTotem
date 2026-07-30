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

  /** Alinha um rótulo à esquerda e um valor à direita na largura do papel. */
  function padLine(label, value, width = RECEIPT_WIDTH) {
    const l = String(label)
    const v = String(value)
    const spaces = Math.max(1, width - l.length - v.length)
    return l + ' '.repeat(spaces) + v
  }

  function bold(text) {
    return { text, bold: true }
  }

  /**
   * Monta o comprovante do pedido com um layout mais legível:
   * título/total em destaque (negrito) e separadores distintos por seção.
   */
  function buildReceiptLines(orderData) {
    const sep = '-'.repeat(RECEIPT_WIDTH)
    const sepForte = '='.repeat(RECEIPT_WIDTH)
    const lines = [
      '',
      bold(center(orderData.company?.name || 'SIMPLETOTEM')),
    ]

    if (orderData.company?.cnpj) {
      lines.push(center(`CNPJ ${orderData.company.cnpj}`))
    }

    lines.push(
      center('COMPROVANTE DE VENDA'),
      sepForte,
      center(`Pedido #${orderData.orderNumber || '—'}`),
      center(orderData.date || ''),
      sep,
    )

    for (const item of orderData.items || []) {
      const qty = item.quantity ?? 1
      const total = qty * (item.unitPrice ?? 0)
      lines.push(`${item.name}`.substring(0, RECEIPT_WIDTH))
      lines.push(padLine(`  ${qty}x ${formatMoney(item.unitPrice)}`, formatMoney(total)))
    }

    lines.push(sep)
    lines.push(padLine('Subtotal', formatMoney(orderData.subtotal)))

    if (orderData.discount > 0) {
      lines.push(padLine('Desconto', `-${formatMoney(orderData.discount)}`))
    }

    lines.push(sepForte)
    lines.push(bold(padLine('TOTAL', formatMoney(orderData.total))))
    lines.push(sep)
    lines.push(`Pagamento: ${orderData.paymentMethod || '—'}`)

    if (orderData.pickupCode) {
      lines.push(sepForte)
      lines.push(center('RETIRE SEU PEDIDO'))
      lines.push(bold(center(String(orderData.pickupCode))))
      lines.push(sepForte)
    }

    lines.push('', center('Obrigado pela preferência!'), sep, '', '')
    return lines
  }

  /**
   * Monta o ticket de produção de uma única unidade de um item
   * (ex.: para a cozinha/preparo) — um ticket por unidade, não por linha do pedido.
   */
  function buildTicketLines(item, orderNumber, unitIndex = 1, unitTotal = 1) {
    const sep = '-'.repeat(RECEIPT_WIDTH)
    const lines = [
      '',
      bold(center('TICKET DE PRODUÇÃO')),
      sep,
      center(`Pedido #${orderNumber || '—'}`),
    ]

    if (unitTotal > 1) {
      lines.push(center(`Unidade ${unitIndex} de ${unitTotal}`))
    }

    lines.push(
      sep,
      '',
      bold(center(String(item.name || '').substring(0, RECEIPT_WIDTH))),
    )

    if (item.notes) {
      lines.push('', center(String(item.notes).substring(0, RECEIPT_WIDTH)))
    }

    lines.push('', sep, center(new Date().toLocaleString('pt-BR')), '', '')
    return lines
  }

  async function printComplete(orderData) {
    const lines = buildReceiptLines(orderData)
    return printLines(lines, { cut: true })
  }

  /**
   * Imprime um ticket individual por unidade de cada item do pedido
   * (ex.: 2x Coxinha vira 2 tickets separados, um para cada unidade).
   * Controlado pelo ajuste "Imprimir ticket individual por produto" do admin —
   * não depende do emite_ticket vindo do ERP, que é usado para outro fim (payload de venda).
   * Retorna { success, printed, failed } sem interromper as demais unidades em caso de erro.
   */
  async function printProductTickets(items, orderNumber) {
    const alvo = items || []
    let printed = 0
    const failed = []

    for (const item of alvo) {
      const qty = Math.max(1, Number(item.quantity) || 1)
      for (let unit = 1; unit <= qty; unit++) {
        const result = await printLines(buildTicketLines(item, orderNumber, unit, qty), { cut: true })
        if (result.success) {
          printed++
        } else {
          failed.push({ item: item.name, unit, message: result.message })
        }
      }
    }

    return { success: failed.length === 0, printed, failed }
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
    printProductTickets,
    testPrint,
  }
}
