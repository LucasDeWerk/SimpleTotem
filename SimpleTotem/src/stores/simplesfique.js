import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '@/services/api'

export const useSimpleSfiqueStore = defineStore('simplesfique', () => {
  const sessao = ref(null)
  const sessaoCarregada = ref(false)

  const isConnected = computed(() => Boolean(sessao.value?.token_ativo))
  const idSaas = computed(() => sessao.value?.id_saas ?? null)
  const idEmpresa = computed(() => sessao.value?.id_empresa ?? null)

  function setSessao(data) {
    sessao.value = data
  }

  async function hydrate() {
    if (sessaoCarregada.value) return sessao.value
    try {
      const data = await api.obterSessaoSimpleSfique()
      sessao.value = data
    } catch (err) {
      console.warn('[SimpleSfique] Sessão indisponível:', err.message)
      sessao.value = null
    } finally {
      sessaoCarregada.value = true
    }
    return sessao.value
  }

  function clearSessao() {
    sessao.value = null
    sessaoCarregada.value = false
  }

  return {
    sessao,
    sessaoCarregada,
    isConnected,
    idSaas,
    idEmpresa,
    setSessao,
    hydrate,
    clearSessao
  }
})
