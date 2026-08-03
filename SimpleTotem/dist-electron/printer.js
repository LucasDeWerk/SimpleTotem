'use strict'

const { ipcMain } = require('electron')
const EventEmitter = require('events')
const usb = require('usb')
const escpos = require('escpos')

// escpos-usb foi escrito para node-usb v1 (usb.on global). v2 não expõe essa API.
function patchUsbV1Compat(usbModule) {
  if (typeof usbModule.on === 'function') return
  const events = new EventEmitter()
  usbModule.on = (...args) => events.on(...args)
  usbModule.removeAllListeners = (...args) => events.removeAllListeners(...args)
}
patchUsbV1Compat(usb)

// Adapter USB do escpos (carregar após o patch — escpos-usb reutiliza o mesmo módulo usb)
let escposUSB
try {
  escposUSB = require('escpos-usb')
} catch (_) {
  try {
    escposUSB = escpos.USB
  } catch (_2) {
    escposUSB = null
  }
}

const https = require('https')
const http  = require('http')

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000'

// ─── Utilitários ───────────────────────────────────────────────────────────

/**
 * Faz uma requisição HTTP simples sem dependências externas.
 */
function httpGet(url) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https') ? https : http
    mod.get(url, (res) => {
      let data = ''
      res.on('data', chunk => { data += chunk })
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(data) }) }
        catch (e) { resolve({ status: res.statusCode, body: data }) }
      })
    }).on('error', reject)
  })
}

function httpPost(url, body) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https') ? https : http
    const payload = JSON.stringify(body)
    const urlObj = new URL(url)
    const options = {
      hostname: urlObj.hostname,
      port: urlObj.port || (url.startsWith('https') ? 443 : 80),
      path: urlObj.pathname + urlObj.search,
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) }
    }
    const req = mod.request(options, (res) => {
      let data = ''
      res.on('data', chunk => { data += chunk })
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(data) }) }
        catch (e) { resolve({ status: res.statusCode, body: data }) }
      })
    })
    req.on('error', reject)
    req.write(payload)
    req.end()
  })
}

let _printerToken = null

async function getPrinterToken() {
  if (_printerToken) return _printerToken
  const res = await httpPost(`${API_BASE_URL}/auth/login`, {})
  if (res.status !== 200) throw new Error(`Falha no login: ${res.status}`)
  _printerToken = res.body.access_token
  return _printerToken
}

/**
 * Busca impressora configurada via backend API.
 * Retorna { vendorId, productId, nome } (serializável) ou null.
 */
async function findConfiguredPrinter() {
  try {
    const token = await getPrinterToken()
    const res = await new Promise((resolve, reject) => {
      const mod = API_BASE_URL.startsWith('https') ? https : http
      const urlObj = new URL(`${API_BASE_URL}/hardware/dispositivos`)
      const options = {
        hostname: urlObj.hostname,
        port: urlObj.port || (API_BASE_URL.startsWith('https') ? 443 : 80),
        path: urlObj.pathname,
        method: 'GET',
        headers: { Authorization: `Bearer ${token}` }
      }
      const req = mod.request(options, (r) => {
        let data = ''
        r.on('data', chunk => { data += chunk })
        r.on('end', () => {
          if (r.statusCode === 401) { _printerToken = null }
          try { resolve({ status: r.statusCode, body: JSON.parse(data) }) }
          catch (e) { resolve({ status: r.statusCode, body: [] }) }
        })
      })
      req.on('error', reject)
      req.end()
    })

    const lista = Array.isArray(res.body) ? res.body : []
    const config = lista.find(
      d => d.tipo_dispositivo === 'impressora' && d.ativo !== 0 && d.ativo !== false
    )

    if (!config) {
      console.log('[Printer] Nenhuma impressora configurada no backend.')
      return null
    }

    const vendorId = parseInt(config.vendor_id, 16)
    const productId = parseInt(config.product_id, 16)
    const device = usb.findByIds(vendorId, productId)

    if (!device) {
      console.log(
        `[Printer] Impressora configurada não encontrada no USB: ${config.vendor_id}:${config.product_id}`
      )
      return null
    }

    console.log(
      `[Printer] Impressora encontrada: ${config.vendor_id}:${config.product_id} (${config.nome})`
    )
    return { vendorId, productId, nome: config.nome }
  } catch (err) {
    console.error('[Printer] Erro ao buscar impressora:', err.message)
    return null
  }
}

function usbAccessHint() {
  return (
    'Sem permissão USB na impressora. Execute no totem: ' +
    'sudo bash script/configurar_impressora.sh'
  )
}

function formatPrinterError(err) {
  const msg = err?.message || String(err)
  if (msg.includes('LIBUSB_ERROR_ACCESS') || msg.includes('Access denied')) {
    return usbAccessHint()
  }
  return msg
}

function createUsbAdapter(printerConfig) {
  return new escposUSB(printerConfig.vendorId, printerConfig.productId)
}

/** Cupom TEF: 48 colunas, fonte A normal (size 0,0 = 1x — size 1,1 seria 2x). */
const RECEIPT_WIDTH = 48

/**
 * Quebra `text` em uma ou mais linhas de até `width` caracteres, sem descartar
 * conteúdo. Prefere quebrar nos espaços (sem cortar palavra ao meio); se uma
 * única palavra já for maior que `width`, quebra por tamanho fixo mesmo assim
 * (não há como preservar a palavra inteira numa linha só nesse caso).
 */
function wrapLine(text, width) {
  const str = String(text ?? '')
  if (str.length <= width) return [str]

  const out = []
  let current = ''

  for (const word of str.split(' ')) {
    if (word.length > width) {
      if (current) {
        out.push(current)
        current = ''
      }
      for (let i = 0; i < word.length; i += width) {
        out.push(word.substring(i, i + width))
      }
      continue
    }

    const candidate = current ? `${current} ${word}` : word
    if (candidate.length > width) {
      out.push(current)
      current = word
    } else {
      current = candidate
    }
  }
  if (current) out.push(current)

  return out
}

/**
 * Normaliza linhas para impressão. Cada item pode ser uma string simples
 * (imprime normal) ou um objeto { text, bold } para destacar títulos/totais.
 * Linhas vazias são preservadas para dar espaçamento real no papel.
 * Linhas maiores que RECEIPT_WIDTH são quebradas em várias linhas — nunca cortadas.
 */
function normalizePrintLines(lines) {
  const out = []
  for (const item of lines) {
    if (item === null || item === undefined) continue
    const isObj = typeof item === 'object' && 'text' in item
    const raw = isObj ? item.text : item
    const text = String(raw ?? '')
    const bold = isObj && Boolean(item.bold)
    for (const line of text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n')) {
      for (const wrapped of wrapLine(line.trim(), RECEIPT_WIDTH)) {
        out.push({ text: wrapped, bold })
      }
    }
  }
  return out
}

/** Concatena blocos do cupom TEF na ordem recebida da Fiserv. */
function joinCupomBruto(lines) {
  if (!Array.isArray(lines)) return String(lines ?? '')
  return lines.map((l) => String(l ?? '')).join('')
}

/** Remove bytes de controle que disparam avanço de papel sem imprimir texto. */
function sanitizeCupomLine(line) {
  return String(line)
    .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '')
    .trimEnd()
}

/**
 * Converte cupom SiTef/Fiserv em linhas para a térmica.
 * Spec: '\' e '\\n' são separadores de linha — não enviar buffer bruto (causa papel em branco).
 * Exigência Fiserv: imprimir a string exatamente como recebida, sem omissão ou
 * alteração — cada linha vai inteira num único comando de impressão, sem corte
 * NEM quebra feita por nós. Se ultrapassar RECEIPT_WIDTH, é a própria impressora
 * térmica (hardware) que continua na linha seguinte — não inserimos nenhum
 * caractere de quebra que não estivesse no conteúdo original.
 */
function parseCupomFiserv(linesOrText) {
  const texto = Array.isArray(linesOrText) ? joinCupomBruto(linesOrText) : String(linesOrText ?? '')
  if (!texto) return []

  const out = []
  const normalized = texto.replace(/\r\n/g, '\n').replace(/\r/g, '\n')

  for (const block of normalized.split('\n')) {
    for (const part of block.split('\\')) {
      const line = sanitizeCupomLine(part)
      if (line.trim()) {
        out.push(line)
      }
    }
  }

  return out
}

function configureReceiptPrinter(escposPrinter) {
  return escposPrinter
    .font('a')
    .align('lt')
    .style('normal')
    .size(0, 0)
}

// ─── Impressão principal ───────────────────────────────────────────────────

/**
 * Imprime um array de strings na impressora térmica.
 * @param {string[]} lines
 * @param {object} options  { cut: bool, bold: bool }
 */
async function printLines(lines, options = {}) {
  return new Promise(async (resolve) => {
    const printerConfig = await findConfiguredPrinter()
    if (!printerConfig) {
      return resolve({ success: false, message: 'Impressora não encontrada ou não configurada.' })
    }

    if (!escposUSB) {
      return resolve({ success: false, message: 'Driver escpos-usb não disponível.' })
    }

    const isCupomFiserv = options.cupomFiserv === true || options.raw === true
    const textLines = isCupomFiserv
      ? parseCupomFiserv(lines)
      : normalizePrintLines(Array.isArray(lines) ? lines : [])

    if (isCupomFiserv) {
      const bruto = joinCupomBruto(Array.isArray(lines) ? lines : [lines])
      console.log(
        `[Printer] Cupom Fiserv: ${bruto.length} chars → ${textLines.length} linha(s) texto`
      )
      if (!textLines.length) {
        return resolve({ success: false, message: 'Cupom TEF vazio ou sem linhas imprimíveis.' })
      }
    } else {
      console.log(`[Printer] Imprimindo ${textLines.length} linha(s)...`)
    }

    try {
      const adapter = createUsbAdapter(printerConfig)
      const escposPrinter = new escpos.Printer(adapter, {
        encoding: 'CP860',
        width: RECEIPT_WIDTH,
      })

      adapter.open((err) => {
        if (err) {
          const message = formatPrinterError(err)
          console.error('[Printer] Erro ao abrir porta USB:', message)
          return resolve({ success: false, message })
        }

        try {
          configureReceiptPrinter(escposPrinter)

          if (isCupomFiserv) {
            for (const line of textLines) {
              escposPrinter.text(line)
            }
          } else {
            for (const line of textLines) {
              if (line.bold) {
                escposPrinter.style('b').text(line.text).style('normal')
              } else {
                escposPrinter.text(line.text)
              }
            }
          }

          if (options.cut !== false) {
            escposPrinter.cut()
          }

          escposPrinter.close(() => {
            resolve({ success: true })
          })
        } catch (printErr) {
          console.error('[Printer] Erro durante impressão:', printErr.message)
          try { escposPrinter.close() } catch (_) {}
          resolve({ success: false, message: printErr.message })
        }
      })
    } catch (adapterErr) {
      const message = formatPrinterError(adapterErr)
      console.error('[Printer] Erro ao criar adapter:', message)
      resolve({ success: false, message })
    }
  })
}

/**
 * Impressão de teste simples.
 */
function testPrint() {
  const W = 48
  const SEP = '-'.repeat(W)
  const center = (txt) => {
    if (txt.length >= W) return txt.substring(0, W)
    const pad = Math.floor((W - txt.length) / 2)
    return ' '.repeat(pad) + txt
  }

  const lines = [
    '',
    center('TESTE DE IMPRESSAO'),
    SEP,
    center('SimpleTotem'),
    center('Impressora configurada com sucesso!'),
    SEP,
    center(new Date().toLocaleString('pt-BR')),
    '',
    '',
    ''
  ]

  return printLines(lines, { cut: true })
}

// ─── Raw print ─────────────────────────────────────────────────────────────

/**
 * Envia buffer raw para a impressora.
 * @param {number[]} bufferData  Array de bytes
 */
async function printRaw(bufferData) {
  return new Promise(async (resolve) => {
    const printerConfig = await findConfiguredPrinter()
    if (!printerConfig) {
      return resolve({ success: false, message: 'Impressora não encontrada ou não configurada.' })
    }

    if (!escposUSB) {
      return resolve({ success: false, message: 'Driver escpos-usb não disponível.' })
    }

    try {
      const adapter = createUsbAdapter(printerConfig)
      adapter.open((err) => {
        if (err) {
          return resolve({ success: false, message: formatPrinterError(err) })
        }
        const buf = Buffer.from(bufferData)
        adapter.write(buf, (writeErr) => {
          adapter.close()
          if (writeErr) {
            return resolve({ success: false, message: writeErr.message })
          }
          resolve({ success: true })
        })
      })
    } catch (e) {
      resolve({ success: false, message: e.message })
    }
  })
}

// ─── Setup IPC ─────────────────────────────────────────────────────────────

function setupPrinterIPC() {
  // Pré-aquece o token do backend assim que o Electron inicia
  getPrinterToken()
    .then(() => console.log('[Printer] Token pré-carregado com sucesso'))
    .catch(err => console.warn('[Printer] Falha ao pré-carregar token:', err.message))

  ipcMain.handle('printer:print-lines', async (_event, lines, options) => {
    return printLines(lines, options)
  })

  ipcMain.handle('printer:print-raw', async (_event, bufferData) => {
    return printRaw(bufferData)
  })

  ipcMain.handle('printer:test-print', async () => {
    return testPrint()
  })

  console.log('[Printer] IPC handlers registrados')
}

module.exports = { setupPrinterIPC, printLines, testPrint, printRaw }
