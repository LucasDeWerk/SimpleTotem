import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const STORAGE_KEY = 'simplesfique_sessao'

function loadStored() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export const useSimpleSfiqueStore = defineStore('simplesfique', () => {
  const sessao = ref(loadStored())

  const isConnected = computed(() => Boolean(sessao.value?.token_ativo))
  const idSaas = computed(() => sessao.value?.id_saas ?? null)
  const idEmpresa = computed(() => sessao.value?.id_empresa ?? null)

  function setSessao(data) {
    sessao.value = data
    if (data) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  function clearSessao() {
    setSessao(null)
  }

  return {
    sessao,
    isConnected,
    idSaas,
    idEmpresa,
    setSessao,
    clearSessao
  }
})
