// ─── Configuração ─────────────────────────────────────────────────────────────

let _apiBaseUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

export function getApiBaseUrl() {
  return _apiBaseUrl
}

export function setApiBaseUrl(url) {
  _apiBaseUrl = (url || '').trim().replace(/\/$/, '') || 'http://localhost:8000'
  invalidateToken()
  _adminToken = null
}

let _token = null
let _adminToken = sessionStorage.getItem('admin_token') || null

// ─── Auth ─────────────────────────────────────────────────────────────────────

async function getToken() {
  if (_token) return _token
  const res = await fetch(`${getApiBaseUrl()}/auth/login`, { method: 'POST' })
  if (!res.ok) throw new Error(`Falha ao obter token: ${res.status}`)
  const data = await res.json()
  _token = data.access_token
  return _token
}

function invalidateToken() {
  _token = null
}

async function apiFetch(path, options = {}) {
  const token = await getToken()
  const res = await fetch(`${getApiBaseUrl()}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(options.headers || {})
    }
  })

  // Token expirado — tenta uma vez com novo token
  if (res.status === 401) {
    invalidateToken()
    const newToken = await getToken()
    const retry = await fetch(`${getApiBaseUrl()}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${newToken}`,
        ...(options.headers || {})
      }
    })
    if (!retry.ok) throw new Error(`Erro ${retry.status}: ${await retry.text()}`)
    return retry.status === 204 ? null : retry.json()
  }

  if (!res.ok) throw new Error(`Erro ${res.status}: ${await res.text()}`)
  return res.status === 204 ? null : res.json()
}

// ─── Empresa / SaaS ───────────────────────────────────────────────────────────

export async function obterStatusEmpresa() {
  const res = await fetch(`${getApiBaseUrl()}/empresa/status`)
  if (!res.ok) throw new Error(`Erro ${res.status}: ${await res.text()}`)
  return res.json()
}

export async function obterUsuarioSugerido() {
  const res = await fetch(`${getApiBaseUrl()}/auth/usuario-sugerido`)
  if (!res.ok) throw new Error(`Erro ${res.status}`)
  return res.json()
}

export async function loginSistema(usuario, senha) {
  const res = await fetch(`${getApiBaseUrl()}/auth/system-login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ usuario, senha })
  })
  if (!res.ok) {
    let detail = `Erro ${res.status}`
    try {
      const data = await res.json()
      detail = data.detail || detail
    } catch {
      detail = await res.text()
    }
    throw new Error(detail)
  }
  const data = await res.json()
  _token = data.access_token
  _adminToken = data.access_token
  sessionStorage.setItem('admin_token', data.access_token)
  return data
}

export async function validarAdmin() {
  const token = _adminToken || sessionStorage.getItem('admin_token')
  if (!token) throw new Error('Sessão admin expirada')
  const res = await fetch(`${getApiBaseUrl()}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('Token admin inválido')
  return res.json()
}

export async function testarConexaoApi(url) {
  const base = (url || getApiBaseUrl()).replace(/\/$/, '')
  const res = await fetch(`${base}/empresa/status`)
  if (!res.ok) throw new Error(`Erro ${res.status}`)
  return res.json()
}

export async function obterTerminalAtual() {
  return apiFetch('/terminal/atual')
}

// ─── Hardware (dispositivos) ──────────────────────────────────────────────────

/**
 * Lista dispositivos USB conectados via sysfs (Electron IPC).
 * Essa chamada é local — não vai ao backend.
 */
export async function listarDispositivosUSB() {
  if (!window.hardwareAPI?.listarUSB) {
    console.warn('[API] hardwareAPI.listarUSB não disponível')
    return []
  }
  return window.hardwareAPI.listarUSB()
}

/**
 * Retorna a configuração ativa para um tipo de dispositivo.
 * GET /hardware/dispositivos → filtra por tipo_dispositivo client-side.
 */
export async function obterConfigHardware(tipo) {
  const lista = await apiFetch('/hardware/dispositivos')
  return (lista || []).find(d => d.tipo_dispositivo === tipo && d.ativo !== 0 && d.ativo !== false) || null
}

/**
 * Salva (cria ou substitui) a configuração de um dispositivo.
 * Apaga o existente do mesmo tipo antes de criar.
 */
export async function salvarConfigHardware(config) {
  // Remove o anterior do mesmo tipo, se existir
  const lista = await apiFetch('/hardware/dispositivos')
  const anterior = (lista || []).find(d => d.tipo_dispositivo === config.tipo_dispositivo)
  if (anterior) {
    await apiFetch(`/hardware/dispositivos/${anterior.id}`, { method: 'DELETE' })
  }

  return apiFetch('/hardware/dispositivos', {
    method: 'POST',
    body: JSON.stringify({
      tipo_dispositivo: config.tipo_dispositivo,
      nome: config.nome,
      vendor_id: config.vendor_id,
      product_id: config.product_id,
      descricao: config.descricao || '',
      driver_id: config.driver_id || null,
      ativo: 1
    })
  })
}

/** Status consolidado de todos os periféricos. */
export async function obterStatusHardware() {
  return apiFetch('/hardware/status')
}

/**
 * Atribui QUALQUER dispositivo USB a um papel (impressora, pinpad, leitor).
 * Marca agnóstico — só precisa VID:PID.
 */
export async function atribuirDispositivoHardware(payload) {
  return apiFetch('/hardware/atribuir', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/** Remove atribuição de uma categoria. */
export async function removerAtribuicaoHardware(categoria) {
  return apiFetch(`/hardware/atribuir/${categoria}`, { method: 'DELETE' })
}

/**
 * Remove a configuração de um tipo de dispositivo.
 */
export async function removerConfigHardware(tipo) {
  const lista = await apiFetch('/hardware/dispositivos')
  const item = (lista || []).find(d => d.tipo_dispositivo === tipo)
  if (!item) return null
  return apiFetch(`/hardware/dispositivos/${item.id}`, { method: 'DELETE' })
}

/** Status da impressora Epson (USB, permissões, banco). */
export async function obterStatusImpressora() {
  return apiFetch('/hardware/impressora/status')
}

/** Detecta a impressora USB e sincroniza tconf_hardware. */
export async function configurarImpressora() {
  return apiFetch('/hardware/impressora/configurar', { method: 'POST' })
}

/** Status do pinpad Gertec (porta, permissões, CliSiTef.ini). */
export async function obterStatusPinpad() {
  return apiFetch('/hardware/pinpad/status')
}

/** Detecta o pinpad USB e atualiza script/CliSiTef.ini. */
export async function configurarPinpad() {
  return apiFetch('/hardware/pinpad/configurar', { method: 'POST' })
}

/** Lista portas seriais USB disponíveis no sistema (ttyUSB*, ttyACM*). */
export async function listarPortasSerial() {
  return apiFetch('/hardware/sitef/portas-serial')
}

/** Atualiza a porta do pinpad em CliSiTef.ini. */
export async function salvarPortaSitef(porta) {
  return apiFetch('/hardware/sitef/porta', {
    method: 'POST',
    body: JSON.stringify({ porta }),
  })
}

// ─── Sincronização (Admin) ────────────────────────────────────────────────────

export async function obterEmpresaSinc() {
  const res = await fetch(`${getApiBaseUrl()}/sinc/empresa`)
  if (!res.ok) throw new Error(`Erro ${res.status}`)
  if (res.status === 204) return null
  const text = await res.text()
  if (!text) return null
  return JSON.parse(text)
}

export async function obterSessaoSimpleSfique() {
  const res = await fetch(`${getApiBaseUrl()}/sinc/sessao`)
  if (!res.ok) throw new Error(`Erro ${res.status}`)
  const text = await res.text()
  if (!text) return null
  return JSON.parse(text)
}

export async function loginSimpleSfique(payload) {
  const token = _token || (await getToken())
  const res = await fetch(`${getApiBaseUrl()}/sinc/simplesfique/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    let detail = `Erro ${res.status}`
    try {
      const data = await res.json()
      detail = data.detail || data.erro || detail
    } catch {
      detail = (await res.text()) || detail
    }
    throw new Error(detail)
  }
  return res.json()
}

export async function salvarEmpresaSimpleSfique(empresa) {
  return apiFetch('/sinc/simplesfique/empresa', {
    method: 'POST',
    body: JSON.stringify(empresa),
  })
}

export async function sincronizarEtapa(etapa) {
  return apiFetch(`/sinc/pull/${etapa}`, { method: 'POST' })
}

export async function sincronizarCompleto() {
  return apiFetch('/sinc/pull/completa', { method: 'POST' })
}

// ─── Vendas ───────────────────────────────────────────────────────────────────

export async function obterMetodosPagamento() {
  return apiFetch('/vendas/metodos-pagamento')
}

export async function listarTiposPagamento() {
  return apiFetch('/vendas/pagamentos/tipos')
}

/**
 * Calcula o total da venda no servidor.
 * @param {{ produto_id, descricao, quantidade, preco_unitario }[]} itens
 */
export async function iniciarVenda(itens) {
  return apiFetch('/vendas/iniciavenda', {
    method: 'POST',
    body: JSON.stringify({ itens }),
  })
}

/**
 * Inicia transação SiTef (cartão ou PIX). Retorna { transacao_id, status }.
 * @param {{ itens, total_cliente, metodo_pagamento_id, cupom? }} payload
 */
export async function iniciarTransacao(payload) {
  const token = await getToken()
  // fetch sem timeout — a transação com o pinpad pode demorar
  const res = await fetch(`${getApiBaseUrl()}/vendas/iniciatransacao`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })

  if (res.status === 401) {
    invalidateToken()
    const newToken = await getToken()
    const retry = await fetch(`${getApiBaseUrl()}/vendas/iniciatransacao`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${newToken}`,
      },
      body: JSON.stringify(payload),
    })
    if (!retry.ok) throw new Error(`Erro ${retry.status}: ${await retry.text()}`)
    return retry.json()
  }

  if (!res.ok) {
    const body = await res.text()
    let detail = body
    try { detail = JSON.parse(body)?.detail ?? body } catch (_) {}
    throw new Error(detail)
  }
  return res.json()
}

/** Status em tempo real da transação SiTef (PIX QR, mensagens, resultado). */
export async function obterStatusTransacao(transacaoId) {
  return apiFetch(`/vendas/transacao/${transacaoId}`)
}

/**
 * Confirma ou desfaz a transação SiTef após impressão do cupom TEF e XML fiscal.
 * Deve ser chamado APÓS printReceipt() (Item 8.1.1 CliSiTef Autoatendimento).
 * @param {{ transacao_id: string, confirma: number, impressao_ok: boolean, xml_emitido: boolean }} payload
 */
export async function confirmarPagamento(payload) {
  return apiFetch('/vendas/confirmar', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

// ─── SimplesFique API ──────────────────────────────────────────────────────────

export function getSfiqueBaseUrl() {
  return (import.meta.env.VITE_SFIQUE_URL || 'http://192.168.10.51:8000').replace(/\/$/, '')
}

// Callback registrado pelo simplesfique store para renovar tokens em 401
let _sfiqueTokenRefresher = null
export function setSfiqueTokenRefresher(fn) {
  _sfiqueTokenRefresher = fn
}

// tokenType: 'jwt' | 'terminal' — determina qual token usar no retry
async function sfFetch(path, options = {}, token = null, tokenType = 'terminal') {
  const makeHeaders = (t) => ({
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(t ? { Authorization: `Bearer ${t}` } : {}),
    ...(options.headers || {}),
  })

  const res = await fetch(`${getSfiqueBaseUrl()}/api/v1${path}`, {
    ...options,
    headers: makeHeaders(token),
  })

  if (res.status === 401 && _sfiqueTokenRefresher) {
    const novosTokens = await _sfiqueTokenRefresher()
    if (novosTokens) {
      const novoToken = tokenType === 'jwt' ? novosTokens.jwt_token : novosTokens.terminal_token
      const retry = await fetch(`${getSfiqueBaseUrl()}/api/v1${path}`, {
        ...options,
        headers: makeHeaders(novoToken),
      })
      if (!retry.ok) {
        let detail = `Erro ${retry.status}`
        try { const d = await retry.json(); detail = d.detail || d.erro || detail } catch {}
        throw new Error(detail)
      }
      return retry.status === 204 ? null : retry.json()
    }
  }

  if (!res.ok) {
    let detail = `Erro ${res.status}`
    try { const d = await res.json(); detail = d.detail || d.erro || detail } catch {}
    throw new Error(detail)
  }
  return res.status === 204 ? null : res.json()
}

export function sfLogin(email, senha) {
  return sfFetch('/auth/login', { method: 'POST', body: JSON.stringify({ email, senha }) })
}

export function sfListarTerminais(jwtToken) {
  return sfFetch('/operacional/terminais', {}, jwtToken, 'jwt')
}

export function sfListarTiposPagamento(jwtToken) {
  return sfFetch('/financeiro/tipo-pagamento-recebimentos', {}, jwtToken, 'jwt')
}

export function sfValidarSenha(terminalId, senha, jwtToken) {
  return sfFetch(`/operacional/terminais/${terminalId}/validar-senha`, {
    method: 'POST',
    body: JSON.stringify({ senha, app: 'totem' }),
  }, jwtToken, 'jwt')
}

export function sfObterConfig(terminalId, configVersion, produtosVersion, terminalToken) {
  return sfFetch(
    `/totem/terminais/${terminalId}/config?config_version=${configVersion}&produtos_version=${produtosVersion}`,
    {},
    terminalToken,
    'terminal',
  )
}

export function sfEmitirCupom(cupomId, jwtToken) {
  return sfFetch('/vendas/cupom-fiscal/emitir', {
    method: 'POST',
    body: JSON.stringify({ cupom_id: cupomId }),
  }, jwtToken, 'jwt')
}

export function sfVendaCompleta(payload, terminalToken) {
  return sfFetch('/totem/venda-completa', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, terminalToken, 'terminal')
}

// ─── Sessão do totem (local backend) ─────────────────────────────────────────

export async function obterSessaoTotem() {
  const res = await fetch(`${getApiBaseUrl()}/sinc/sessao`)
  if (!res.ok) return null
  const text = await res.text()
  if (!text) return null
  try { return JSON.parse(text) } catch { return null }
}

export async function salvarSessaoTotem(payload) {
  return apiFetch('/sinc/simplesfique/sessao-totem', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function reloginSfique() {
  const res = await fetch(`${getApiBaseUrl()}/sinc/simplesfique/relogin`, { method: 'POST' })
  if (!res.ok) {
    let detail = `${res.status}`
    try { const d = await res.json(); detail = d.detail || detail } catch {}
    console.warn('[Sfique] Relogin automático falhou:', detail)
    return null
  }
  return res.json()
}

