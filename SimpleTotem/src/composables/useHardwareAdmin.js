import { ref, computed } from 'vue'
import {
  listarDispositivosUSB,
  obterStatusHardware,
  atribuirDispositivoHardware,
  removerAtribuicaoHardware,
} from '@/services/api'

export const CATEGORIAS = [
  {
    id: 'impressora',
    label: 'Impressora',
    icon: '🖨️',
    descricao: 'Térmica ESC/POS — Bematech, Epson, Elgin, qualquer uma',
    temTeste: true,
  },
  {
    id: 'terminal_pagamento',
    label: 'Pinpad / TEF',
    icon: '💳',
    descricao: 'Terminal de pagamento USB — Gertec, Ingenico, PAX, qualquer um',
    temTeste: false,
  },
  {
    id: 'leitor_barcode',
    label: 'Leitor',
    icon: '📷',
    descricao: 'Scanner de código de barras USB',
    temTeste: false,
  },
]

export function useHardwareAdmin() {
  const carregando = ref(false)
  const configurando = ref(null)
  const testandoImpressao = ref(false)
  const mensagens = ref({})
  const resultadoTeste = ref(null)
  const dispositivosUSB = ref([])
  const statusGeral = ref(null)
  const erroGlobal = ref(null)

  const categoriasComStatus = computed(() => {
    const cats = statusGeral.value?.categorias || {}
    return CATEGORIAS.map((cat) => {
      const info = cats[cat.id] || {}
      return {
        ...cat,
        ...info,
        badge: calcBadge(info),
      }
    })
  })

  function calcBadge(info) {
    if (!info.configurado) return 'pendente'
    if (info.ok) return 'ok'
    if (info.conectado) return 'sem_permissao'
    return 'desconectado'
  }

  function labelBadge(badge) {
    return {
      ok: 'Operacional',
      sem_permissao: 'Sem permissão',
      desconectado: 'Desconectado',
      pendente: 'Não configurado',
    }[badge] || badge
  }

  function mensagemErroApi(e) {
    const msg = e?.message || String(e)
    if (msg.includes('404')) {
      return 'Endpoint não encontrado — reinicie o backend (porta 8000 pode estar com versão antiga).'
    }
    if (msg.includes('Failed to fetch') || msg.includes('NetworkError')) {
      return 'Não foi possível conectar ao backend em localhost:8000.'
    }
    return msg
  }

  async function carregarTudo() {
    carregando.value = true
    mensagens.value = {}
    erroGlobal.value = null
    try {
      statusGeral.value = await obterStatusHardware()
    } catch (e) {
      console.error('[Hardware]', e)
      erroGlobal.value = mensagemErroApi(e)
    } finally {
      carregando.value = false
    }
  }

  async function buscarUSB() {
    carregando.value = true
    try {
      dispositivosUSB.value = await listarDispositivosUSB()
    } catch (e) {
      dispositivosUSB.value = []
    } finally {
      carregando.value = false
    }
  }

  async function atribuir(categoriaId, device) {
    configurando.value = `${categoriaId}-${device.vendorId}`
    mensagens.value[categoriaId] = null
    try {
      await atribuirDispositivoHardware({
        categoria: categoriaId,
        vendor_id: device.vendorId,
        product_id: device.productId,
        nome: device.produto,
        fabricante: device.fabricante,
      })
      await carregarTudo()
      mensagens.value[categoriaId] = {
        tipo: 'ok',
        texto: `${device.produto} configurado como ${labelCategoria(categoriaId)}.`,
      }
    } catch (e) {
      mensagens.value[categoriaId] = {
        tipo: 'erro',
        texto: e.message || 'Falha ao configurar.',
      }
    } finally {
      configurando.value = null
    }
  }

  async function remover(categoriaId) {
    try {
      await removerAtribuicaoHardware(categoriaId)
      mensagens.value[categoriaId] = { tipo: 'ok', texto: 'Configuração removida.' }
      await carregarTudo()
    } catch (e) {
      mensagens.value[categoriaId] = { tipo: 'erro', texto: e.message }
    }
  }

  async function testarImpressao() {
    testandoImpressao.value = true
    resultadoTeste.value = null
    try {
      if (!window.electronAPI?.printer) {
        throw new Error('Teste de impressão só funciona no app Electron.')
      }
      const result = await window.electronAPI.printer.testPrint()
      resultadoTeste.value = result.success
        ? { tipo: 'ok', texto: 'Impressão OK!' }
        : { tipo: 'erro', texto: result.message || 'Erro ao imprimir.' }
    } catch (e) {
      resultadoTeste.value = { tipo: 'erro', texto: e.message }
    } finally {
      testandoImpressao.value = false
    }
  }

  function labelCategoria(id) {
    return CATEGORIAS.find((c) => c.id === id)?.label || id
  }

  function jaAtribuido(categoriaId, device) {
    const cfg = statusGeral.value?.categorias?.[categoriaId]?.configurado
    if (!cfg) return false
    return (
      cfg.vendor_id?.toLowerCase() === device.vendorId?.toLowerCase() &&
      cfg.product_id?.toLowerCase() === device.productId?.toLowerCase()
    )
  }

  return {
    carregando,
    configurando,
    testandoImpressao,
    mensagens,
    resultadoTeste,
    dispositivosUSB,
    statusGeral,
    erroGlobal,
    categoriasComStatus,
    labelBadge,
    labelCategoria,
    jaAtribuido,
    carregarTudo,
    buscarUSB,
    atribuir,
    remover,
    testarImpressao,
  }
}
