// ─── Configuração ─────────────────────────────────────────────────────────────

const BASE_URL = localStorage.getItem('api_base_url') || 'http://localhost:8000'

let _token = null

// ─── Auth ─────────────────────────────────────────────────────────────────────

async function getToken() {
  if (_token) return _token
  const res = await fetch(`${BASE_URL}/auth/login`, { method: 'POST' })
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
  const res = await fetch(`${BASE_URL}${path}`, {
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
    const retry = await fetch(`${BASE_URL}${path}`, {
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

// ─── Catálogo ─────────────────────────────────────────────────────────────────

export async function obterGrupos() {
  return apiFetch('/catalogo/grupos')
}

export async function obterSubgrupos(idGrupo) {
  const qs = idGrupo != null ? `?id_grupo=${idGrupo}` : ''
  return apiFetch(`/catalogo/subgrupos${qs}`)
}

export async function obterMarcas() {
  // Endpoint não existe ainda no backend — retorna lista vazia sem quebrar
  return []
}

export async function obterMedidas() {
  // Endpoint não existe ainda no backend — retorna lista vazia sem quebrar
  return []
}

export async function obterProdutos(filtros = {}) {
  const params = new URLSearchParams()
  if (filtros.id_grupo != null)    params.set('id_grupo',    filtros.id_grupo)
  if (filtros.id_subgrupo != null) params.set('id_subgrupo', filtros.id_subgrupo)
  const qs = params.toString() ? `?${params}` : ''
  return apiFetch(`/catalogo/produtos${qs}`)
}

export async function obterProduto(idProduto) {
  return apiFetch(`/catalogo/produtos/${idProduto}`)
}

// ─── Empresa / SaaS ───────────────────────────────────────────────────────────

export async function obterEmpresa() {
  return apiFetch('/empresa')
}

/** @deprecated use obterEmpresa() */
export async function obterEmpresas() {
  const empresa = await obterEmpresa()
  return empresa ? [empresa] : []
}

export async function obterSaas() {
  // Sem endpoint dedicado no backend — retorna null
  return null
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
  return (lista || []).find(d => d.tipo_dispositivo === tipo && d.ativo) || null
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
      ativo: true
    })
  })
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

// ─── Sincronização (Admin) ────────────────────────────────────────────────────
// Valida que o backend responde e retorna os dados atuais.

export async function sincronizarEmpresas() {
  return obterEmpresas()
}

export async function sincronizarGrupos() {
  return obterGrupos()
}

export async function sincronizarSubgrupos() {
  return obterSubgrupos()
}

export async function sincronizarMarcas() {
  return obterMarcas()
}

export async function sincronizarMedidas() {
  return obterMedidas()
}

export async function sincronizarProdutos() {
  return obterProdutos()
}

// ─── Vendas ───────────────────────────────────────────────────────────────────

export async function listarVendas() {
  return apiFetch('/vendas')
}

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
 * Executa a transação completa (SiTef + gravação + retorno de cupom).
 * Sem timeout — aguarda até o pinpad concluir.
 * @param {{ itens, total_cliente, metodo_pagamento_id, cupom? }} payload
 */
export async function iniciarTransacao(payload) {
  const token = await getToken()
  // fetch sem timeout — a transação com o pinpad pode demorar
  const res = await fetch(`${BASE_URL}/vendas/iniciatransacao`, {
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
    const retry = await fetch(`${BASE_URL}/vendas/iniciatransacao`, {
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


// ─── Warm-up: obtém o token assim que o módulo é importado ────────────────────
getToken().catch(err => console.warn('[API] Falha ao pré-carregar token:', err.message))

