import { ref, computed, onBeforeUnmount } from 'vue'
import { obterPesoBalanca } from '@/services/api'

const INTERVALO_MS = 300

/**
 * Leitura ao vivo da balança (GET /balanca/peso em polling).
 * Use start() ao abrir a tela de produto pesável; para sozinho ao desmontar.
 */
export function useBalanca() {
  const pesoG = ref(null)
  const estavel = ref(false)
  const porta = ref(null)
  const status = ref('conectando') // conectando | ok | instavel | sem_resposta | desconectada | invalido | erro

  let ativo = false
  let timer = null

  const pesoKg = computed(() => (pesoG.value == null ? null : pesoG.value / 1000))
  // só libera a venda com peso estável e maior que zero
  const pronto = computed(() => status.value === 'ok' && estavel.value && pesoG.value > 0)
  const indisponivel = computed(() =>
    ['sem_resposta', 'desconectada', 'erro'].includes(status.value)
  )

  /** Uma leitura, atualizando o estado. */
  async function lerUma() {
    try {
      const r = await obterPesoBalanca()
      status.value = r.status
      pesoG.value = r.peso_g
      estavel.value = Boolean(r.estavel)
      porta.value = r.porta ?? null
    } catch {
      status.value = 'erro' // backend fora do ar
      pesoG.value = null
      estavel.value = false
    }
  }

  async function ciclo() {
    if (!ativo) return
    await lerUma()
    if (ativo) timer = setTimeout(ciclo, INTERVALO_MS) // sequencial: nunca sobrepõe requisições
  }

  function start() {
    if (ativo) return
    ativo = true
    status.value = 'conectando' // descarta leitura antiga: nada de liberar venda com peso velho
    pesoG.value = null
    estavel.value = false
    ciclo()
  }

  function stop() {
    ativo = false
    clearTimeout(timer)
  }

  onBeforeUnmount(stop)

  return { pesoG, pesoKg, estavel, status, porta, pronto, indisponivel, lerUma, start, stop }
}
