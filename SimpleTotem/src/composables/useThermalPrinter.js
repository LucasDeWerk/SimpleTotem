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

  /** Peso em kg com vírgula e 3 casas: 1.185 → "1,185 kg". */
  function formatKg(value) {
    return `${Number(value || 0).toFixed(3).replace('.', ',')} kg`
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
      const total = Math.round(qty * (item.unitPrice ?? 0) * 100) / 100
      lines.push(`${item.name}`.substring(0, RECEIPT_WIDTH))
      lines.push(padLine(
        item.pesavel
          ? `  ${formatKg(qty)} x ${formatMoney(item.unitPrice)}/kg`
          : `  ${qty}x ${formatMoney(item.unitPrice)}`,
        formatMoney(total),
      ))
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

    // Dados reais retornados pela Fiserv/CliSiTef — exigência de exibir/imprimir
    // os dados da transação sem alteração (mesmos campos da tela de aprovado).
    const temDadosSitef = orderData.modalidade || orderData.bandeira ||
      orderData.nsuSitef || orderData.nsuHost || orderData.autorizacao || orderData.documentoPix
    if (temDadosSitef) {
      lines.push(sep)
      if (orderData.modalidade) lines.push(`Modalidade: ${orderData.modalidade}`)
      if (orderData.bandeira) lines.push(`Bandeira: ${orderData.bandeira}`)
      if (orderData.autorizacao) lines.push(`Autorização: ${orderData.autorizacao}`)
      if (orderData.documentoPix) lines.push(`Documento: ${orderData.documentoPix}`)
      if (orderData.nsuSitef) lines.push(`NSU SiTef: ${orderData.nsuSitef}`)
      if (orderData.nsuHost) lines.push(`NSU Host: ${orderData.nsuHost}`)
    }

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

    if (item.pesavel) {
      lines.push('', center(formatKg(item.quantity)))
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
      // pesável: quantity é o peso em kg — um único ticket por pesagem
      const qty = item.pesavel ? 1 : Math.max(1, Number(item.quantity) || 1)
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
   * Ticket de retirada da Ticketera: 1 por ticket devolvido na venda, com QR code
   * (conteúdo = UUID do ticket) em ESC/POS. Falha de um não interrompe os demais.
   */
  function buildTicketRetiradaBytes(ticket, nomeProduto, senha, pesavel = false) {
    const enc = new TextEncoder()
    const ascii = (t) => enc.encode(String(t ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '') + '\n')
    const qr = enc.encode(String(ticket.id))
    const len = qr.length + 3
    const qty = Number(ticket.quantidade) || 1
    return new Uint8Array([
      0x1b, 0x40, 0x1b, 0x61, 0x01,
      0x1b, 0x45, 0x01, ...ascii('TICKET DE RETIRADA'), 0x1b, 0x45, 0x00,
      ...ascii(senha ? `SENHA ${senha}` : ''),
      ...ascii((pesavel
        ? `${nomeProduto || ''} ${formatKg(ticket.quantidade)}`
        : `${qty > 1 ? qty + 'x ' : ''}${nomeProduto || ''}`).substring(0, RECEIPT_WIDTH)),
      0x1d, 0x28, 0x6b, 0x04, 0x00, 0x31, 0x41, 0x32, 0x00,
      0x1d, 0x28, 0x6b, 0x03, 0x00, 0x31, 0x43, 0x07,
      0x1d, 0x28, 0x6b, 0x03, 0x00, 0x31, 0x45, 0x31,
      0x1d, 0x28, 0x6b, len & 0xff, len >> 8, 0x31, 0x50, 0x30, ...qr,
      0x1d, 0x28, 0x6b, 0x03, 0x00, 0x31, 0x51, 0x30,
      ...ascii(new Date().toLocaleString('pt-BR')),
      0x0a, 0x0a, 0x0a, 0x1d, 0x56, 0x42, 0x00,
    ])
  }

  async function printTicketsRetirada(tickets, items, senha) {
    const porProduto = new Map((items || []).map(i => [Number(i.productId), i]))
    let printed = 0
    const failed = []
    for (const t of tickets || []) {
      const item = porProduto.get(Number(t.id_produto))
      const result = await printRaw(Array.from(buildTicketRetiradaBytes(t, item?.name, senha, Boolean(item?.pesavel))))
      if (result.success) printed++
      else failed.push({ ticket: t.id, message: result.message })
    }
    return { success: failed.length === 0, printed, failed }
  }

  /**
   * Cupom fiscal (NFC-e) devolvido pelo venda-nfce: itens, totais, chave de acesso,
   * protocolo e QR code da consulta (URL em <qrCode> do XML assinado).
   */
  async function printCupomFiscal(cupomFiscal, { cpf } = {}) {
    if (!cupomFiscal || cupomFiscal.erro_cupom_fiscal) return { success: false, message: 'Sem cupom fiscal' }
    const enc = new TextEncoder()
    const asc = (t) => enc.encode(String(t ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '') + '\n')
    const L = (t) => [...asc(String(t).substring(0, RECEIPT_WIDTH))]
    const money = (v) => Number(v || 0).toFixed(2).replace('.', ',')
    const sep = '-'.repeat(RECEIPT_WIDTH)

    let chave = '', protocolo = '', urlQr = ''
    try {
      const doc = new DOMParser().parseFromString(cupomFiscal.xml || '', 'application/xml')
      const infNFe = doc.querySelector('infNFe')
      chave = (infNFe?.getAttribute('Id') || '').replace(/^NFe/, '')
      protocolo = doc.querySelector('nProt')?.textContent || ''
      urlQr = doc.querySelector('qrCode')?.textContent?.trim() || ''
    } catch (e) {
      console.warn('[Printer] XML da NFC-e ilegível:', e.message)
    }

    chave = cupomFiscal.chave_acesso || chave
    protocolo = cupomFiscal.protocolo || protocolo
    const numero = cupomFiscal.cupom?.numero_cupom || (chave ? String(Number(chave.slice(25, 34))) : '')
    const emp = cupomFiscal.empresa || {}
    const tot = cupomFiscal.totais || {}
    const bytes = [0x1b, 0x40, 0x1b, 0x61, 0x01]
    bytes.push(...L(emp.fantasia || ''), ...L(emp.cnpj ? `CNPJ ${emp.cnpj}` : ''))
    bytes.push(...L('DANFE NFC-e - Documento Auxiliar'), ...L('da Nota Fiscal de Consumidor Eletronica'))
    bytes.push(...L(sep), 0x1b, 0x61, 0x00)
    for (const it of cupomFiscal.itens || []) {
      bytes.push(...L(it.descproduto || ''))
      const qtdTxt = String(it.unidade || '').toUpperCase() === 'KG'
        ? `${Number(it.quantidade).toFixed(3).replace('.', ',')} KG`
        : `${Number(it.quantidade)}`
      bytes.push(...L(padLine(`${qtdTxt} x ${money(it.vlr_unitario)}`, money(it.vlr_total))))
    }
    bytes.push(...L(sep))
    if (Number(tot.vlr_desconto) > 0) bytes.push(...L(padLine('Desconto', money(tot.vlr_desconto))))
    bytes.push(0x1b, 0x45, 0x01, ...L(padLine('TOTAL R$', money(tot.vlr_liquido ?? tot.vlr_total_produto))), 0x1b, 0x45, 0x00)
    bytes.push(...L(sep), 0x1b, 0x61, 0x01)
    bytes.push(...L(`NFC-e ${numero}  ${cupomFiscal.cupom?.dtemissao || ''}`))
    if (chave) bytes.push(...L('Chave de acesso:'), ...L(chave.replace(/(\d{4})/g, '$1 ').trim()))
    if (protocolo) bytes.push(...L(`Protocolo: ${protocolo}`))
    bytes.push(...L(cpf ? `CONSUMIDOR CPF ${cpf}` : 'CONSUMIDOR NAO IDENTIFICADO'))
    if (urlQr) {
      const qr = enc.encode(urlQr)
      const len = qr.length + 3
      bytes.push(
        0x1d, 0x28, 0x6b, 0x04, 0x00, 0x31, 0x41, 0x32, 0x00,
        0x1d, 0x28, 0x6b, 0x03, 0x00, 0x31, 0x43, 0x05,
        0x1d, 0x28, 0x6b, 0x03, 0x00, 0x31, 0x45, 0x31,
        0x1d, 0x28, 0x6b, len & 0xff, len >> 8, 0x31, 0x50, 0x30, ...qr,
        0x1d, 0x28, 0x6b, 0x03, 0x00, 0x31, 0x51, 0x30,
      )
      bytes.push(...L('Consulte pela chave de acesso ou QR code'))
    }
    bytes.push(0x0a, 0x0a, 0x0a, 0x1d, 0x56, 0x42, 0x00)
    return printRaw(bytes)
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
    printTicketsRetirada,
    printCupomFiscal,
    testPrint,
  }
}
