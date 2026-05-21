'use strict'

const { ipcMain } = require('electron')
const usb = require('usb')
const escpos = require('escpos')

// Adapter USB do escpos
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
 * Retorna o device USB correspondente ou null.
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
    const config = lista.find(d => d.tipo_dispositivo === 'impressora' && d.ativo)

    if (!config) {
      console.log('[Printer] Nenhuma impressora configurada no backend.')
      return null
    }

    const targetVid = parseInt(config.vendor_id, 16)
    const targetPid = parseInt(config.product_id, 16)
    const devices = usb.getDeviceList()
    const device = devices.find(
      d =>
        d.deviceDescriptor.idVendor === targetVid &&
        d.deviceDescriptor.idProduct === targetPid
    )

    if (!device) {
      console.log(
        `[Printer] Impressora configurada não encontrada no USB: ${config.vendor_id}:${config.product_id}`
      )
      return null
    }

    console.log(
      `[Printer] Impressora encontrada: ${config.vendor_id}:${config.product_id} (${config.nome})`
    )
    return device
  } catch (err) {
    console.error('[Printer] Erro ao buscar impressora:', err.message)
    return null
  }
}

// ─── Impressão principal ───────────────────────────────────────────────────

/**
 * Imprime um array de strings na impressora térmica.
 * @param {string[]} lines
 * @param {object} options  { cut: bool, bold: bool }
 */
async function printLines(lines, options = {}) {
  return new Promise(async (resolve) => {
    const device = await findConfiguredPrinter()
    if (!device) {
      return resolve({ success: false, message: 'Impressora não encontrada ou não configurada.' })
    }

    if (!escposUSB) {
      return resolve({ success: false, message: 'Driver escpos-usb não disponível.' })
    }

    try {
      const adapter = new escposUSB(device)
      const printer = new escpos.Printer(adapter, { encoding: 'CP860' })

      adapter.open((err) => {
        if (err) {
          console.error('[Printer] Erro ao abrir porta USB:', err.message)
          return resolve({ success: false, message: err.message })
        }

        try {
          printer.font('a').align('lt').style('normal').size(1, 1)

          for (const line of lines) {
            printer.text(line)
          }

          if (options.cut !== false) {
            printer.cut()
          }

          printer.close(() => {
            resolve({ success: true })
          })
        } catch (printErr) {
          console.error('[Printer] Erro durante impressão:', printErr.message)
          try { printer.close() } catch (_) {}
          resolve({ success: false, message: printErr.message })
        }
      })
    } catch (adapterErr) {
      console.error('[Printer] Erro ao criar adapter:', adapterErr.message)
      resolve({ success: false, message: adapterErr.message })
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
    const device = await findConfiguredPrinter()
    if (!device) {
      return resolve({ success: false, message: 'Impressora não encontrada ou não configurada.' })
    }

    if (!escposUSB) {
      return resolve({ success: false, message: 'Driver escpos-usb não disponível.' })
    }

    try {
      const adapter = new escposUSB(device)
      adapter.open((err) => {
        if (err) {
          return resolve({ success: false, message: err.message })
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
