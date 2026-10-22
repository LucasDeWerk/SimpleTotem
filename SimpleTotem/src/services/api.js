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

/** Chamadas autenticadas com o token admin (role="admin", via /auth/system-login) —
 * usado pelos endpoints administrativos mais sensíveis (funções CliSiTef de
 * homologação Fiserv), diferente do apiFetch() padrão que usa o token do dispositivo. */
async function adminFetch(path, options = {}) {
  const token = _adminToken || sessionStorage.getItem('admin_token')
  if (!token) throw new Error('Sessão admin expirada')
  const res = await fetch(`${getApiBaseUrl()}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(options.headers || {})
    }
  })
  if (!res.ok) {
    const body = await res.text()
    let detail = body
    try { detail = JSON.parse(body)?.detail ?? body } catch (_) {}
    throw new Error(detail)
  }
  return res.status === 204 ? null : res.json()
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
/** Leitura atual da balança: { status, peso_g, estavel, porta }. */
export async function obterPesoBalanca() {
  return apiFetch('/balanca/peso')
}

/** Tara do prato (g), aplicada pelo backend sobre o peso bruto. */
export async function obterTaraBalanca() {
  return apiFetch('/balanca/tara')
}

export async function salvarTaraBalanca(taraG) {
  return apiFetch('/balanca/tara', { method: 'PUT', body: JSON.stringify({ tara_g: taraG }) })
}

/** Define a tara com o peso atual (prato vazio, estável). */
export async function capturarTaraBalanca() {
  return apiFetch('/balanca/tara/capturar', { method: 'POST' })
}

export async function obterStatusHardware() {
  return apiFetch('/hardware/status')
}

/** Evidência de pré-homologação Fiserv: status do parâmetro TLS (TokenRegistro). */
export async function obterStatusTlsSitef() {
  return apiFetch('/hardware/sitef/tls-status')
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

/**
 * Status da impressora (configurada/conectada/permissão + `pronta`). Usado no
 * painel de periféricos e para bloquear o pagamento quando o comprovante não
 * poderia ser impresso. O sensor de papel NÃO vem daqui: é lido no Electron
 * (window.electronAPI.printer.paperStatus).
 */
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

export async function salvarEmpresaSimpleSfique(empresa) {
  return apiFetch('/sinc/simplesfique/empresa', {
    method: 'POST',
    body: JSON.stringify(empresa),
  })
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
 * Responde a confirmação de cancelamento disparada pelo ANULA físico do
 * pinpad (Seq. 9) — a CliSiTef fica bloqueada esperando essa decisão real.
 */
export async function confirmarCancelamentoTransacao(transacaoId, confirma) {
  return apiFetch(`/vendas/transacao/${transacaoId}/confirmar-cancelamento`, {
    method: 'POST',
    body: JSON.stringify({ confirma }),
  })
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

// ─── Ticketera ─────────────────────────────────────────────────────────────────
//
// Todas as chamadas passam pelo backend local (/ticketera/*), que guarda o JWT
// da sessão, envia X-Terminal-Id e renova o token em 401.

// Mantido por compatibilidade com o store: a renovação agora é feita no backend.
let _sfiqueTokenRefresher = null
export function setSfiqueTokenRefresher(fn) {
  _sfiqueTokenRefresher = fn
}

async function ticketeraFetch(path, options = {}) {
  const res = await fetch(`${getApiBaseUrl()}/ticketera${path}`, {
    cache: 'no-store',
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${await getToken()}`,
      ...(options.headers || {}),
    },
  })
  if (!res.ok) {
    let msg = `Erro ${res.status}`
    try {
      const d = await res.json()
      const det = d.detail
      msg = (typeof det === 'string' ? det : det?.mensagem) || msg
    } catch {}
    const err = new Error(msg)
    err.status = res.status
    throw err
  }
  return res.json()
}

export async function sfLogin(email, senha) {
  const res = await fetch(`${getApiBaseUrl()}/sinc/simplesfique/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, senha }),
  })
  if (!res.ok) {
    let msg = `Erro ${res.status}`
    try { const d = await res.json(); msg = d.detail || msg } catch {}
    throw new Error(typeof msg === 'string' ? msg : 'Falha ao autenticar')
  }
  const data = await res.json()
  const sessao = await obterSessaoTotem()
  return { ...data, token: sessao?.jwt_token || '' }
}

export function sfTerminalAtual() {
  return ticketeraFetch('/terminal-atual')
}

export function sfListarTerminais() {
  return ticketeraFetch('/terminais')
}

export async function sfListarTiposPagamento() {
  return [
    { id: '3', descricao: 'Cartão de Crédito' },
    { id: '4', descricao: 'Cartão de Débito' },
    { id: '17', descricao: 'PIX' },
  ]
}

/** Retorna { access_token, terminal } — terminal traz as flags (emite_cupom_fiscal, emite_ticket, modo_ticket, pede_cpf). */
export function sfValidarSenha(terminalId, senha) {
  return ticketeraFetch(`/terminais/${terminalId}/validar-senha`, {
    method: 'POST',
    body: JSON.stringify({ senha }),
  })
}

// IDs de produto tratados como pesáveis, via .env (VITE_PRODUTOS_PESAVEIS=12,15) — para testar a
// balança enquanto a Ticketera não envia a flag. Quando ela enviar (produto.pesavel / unidade 'KG'), vale a da API.
const PRODUTOS_PESAVEIS_ENV = new Set(
  String(import.meta.env.VITE_PRODUTOS_PESAVEIS || '')
    .split(',').map(s => Number(s.trim())).filter(Boolean)
)

/** Cardápio do terminal, já no formato consumido pelo store (menus + menu_produtos). */
export async function sfObterConfig(terminalId, _cv, _pv, _token, terminal = null) {
  const data = await ticketeraFetch(`/terminais/${terminalId}/produtos`)
  const emiteTicket = terminal ? terminal.emite_ticket !== false : true
  const ambientes = new Map()
  const menu_produtos = (data.produtos || []).map(p => {
    if (p.ambiente_preparo_id != null) {
      ambientes.set(p.ambiente_preparo_id, { id: p.ambiente_preparo_id, nome: p.ambiente_preparo_nome })
    }
    return {
      produto_id: p.produto_id,
      menu_id: p.menu_id,
      nome_produto: p.produto?.nome || '',
      preco: Number(p.produto?.preco) || 0,
      foto: Array.isArray(p.produto?.fotos) ? p.produto.fotos[0] || '' : '',
      emite_ticket: emiteTicket,
      ambiente_preparo_id: p.ambiente_preparo_id ?? null,
      unidade: String(p.produto?.unidade || 'UN').toUpperCase(),
      pesavel: Boolean(p.produto?.pesavel) || String(p.produto?.unidade || '').toUpperCase() === 'KG'
        || PRODUTOS_PESAVEIS_ENV.has(Number(p.produto_id)),
    }
  })
  const menus = (data.menus || []).map(m => ({ id: m.id, nome: m.descmenu, ordem: m.ordem, ativo: m.ativo !== 'n' }))

  // Só para testar a balança (VITE_PRODUTO_TESTE_BALANCA=true, apenas em dev): produto fictício por kg
  // no 1º menu. Não existe na Ticketera — serve para validar a tela; a venda dele não fecha de verdade.
  if (import.meta.env.DEV && String(import.meta.env.VITE_PRODUTO_TESTE_BALANCA) === 'true' && menus.length) {
    menu_produtos.push({
      produto_id: 999001,
      menu_id: menus[0].id,
      nome_produto: 'TESTE Balança (por kg)',
      preco: 69.9,
      foto: '',
      emite_ticket: false,
      ambiente_preparo_id: null,
      unidade: 'KG',
      pesavel: true,
    })
  }

  return {
    updated: true,
    ambientes: [...ambientes.values()],
    menus,
    menu_produtos,
    terminal,
  }
}

/** Fecha a venda na Ticketera. Chamar só depois do pagamento aprovado. Sem retry automático. */
export function sfVendaCompleta(payload, { nfce = false } = {}) {
  return ticketeraFetch(`/venda?nfce=${nfce ? 'true' : 'false'}`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function sfValidarTicket(ticketId) {
  return ticketeraFetch(`/tickets/${encodeURIComponent(ticketId)}/validar`, { method: 'POST' })
}

// Pedidos aprovados e estorno — vêm do backend local (dados/vendas_homologacao.json),
// base real de evidência da homologação, não mais do mock do SimplesFique.

export function sfListarPedidos({ terminalId, codigoSenha, dataOperacao } = {}) {
  const params = new URLSearchParams()
  if (terminalId) params.set('terminal_id', terminalId)
  if (codigoSenha) params.set('codigo_senha', codigoSenha)
  if (dataOperacao) params.set('data_operacao', dataOperacao)
  const qs = params.toString()
  return apiFetch(`/vendas/pedidos${qs ? `?${qs}` : ''}`)
}

/** senhaSupervisor: digitada ao vivo no painel admin para autorizar o cancelamento (TC 500). */
export function sfEstornarPedido(pedidoId, motivo, senhaSupervisor) {
  return apiFetch(`/vendas/pedidos/${pedidoId}/estornar`, {
    method: 'PATCH',
    body: JSON.stringify({ motivo, senha_supervisor: senhaSupervisor }),
  })
}

// ─── Comunicação Fiserv — Menu Administrativo do pinpad (CliSiTef) ───────────
//
// Canal permanente do sistema com a Fiserv: abre o Menu Administrativo (110)
// de forma interativa. O backend inicia a função em subprocesso e mantém o
// stdin aberto; cada comando que exige decisão do operador (menu, sim/não,
// dado, senha mascarada) vira um "prompt" que só avança quando respondido
// pelo painel.

/** Inicia uma função administrativa/de teste CliSiTef. Retorna { execucao_id }. */
export function iniciarFuncaoAdmin(funcaoCodigo) {
  return adminFetch('/homologacao/funcao-admin/iniciar', {
    method: 'POST',
    body: JSON.stringify({ funcao_codigo: funcaoCodigo }),
  })
}

/** Estado atual da execução: mensagens acumuladas, prompt pendente, resultado final. */
export function obterStatusFuncaoAdmin(execucaoId) {
  return adminFetch(`/homologacao/funcao-admin/${execucaoId}/status`)
}

/** Envia a resposta do operador a um prompt pendente (menu, sim/não, dado, senha mascarada). */
export function responderFuncaoAdmin(execucaoId, valor) {
  return adminFetch(`/homologacao/funcao-admin/${execucaoId}/responder`, {
    method: 'POST',
    body: JSON.stringify({ valor }),
  })
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

