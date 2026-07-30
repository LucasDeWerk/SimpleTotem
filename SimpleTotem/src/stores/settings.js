import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const STORAGE_KEY = 'totem_settings'

function loadPersisted() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch (_) {
    return {}
  }
}

export const useSettingsStore = defineStore('settings', () => {
  const persisted = loadPersisted()

  // Imprime um ticket de produção separado para cada item do pedido marcado com emite_ticket
  const imprimirTicketsIndividuais = ref(Boolean(persisted.imprimirTicketsIndividuais))

  watch(imprimirTicketsIndividuais, (value) => {
    const current = loadPersisted()
    current.imprimirTicketsIndividuais = value
    localStorage.setItem(STORAGE_KEY, JSON.stringify(current))
  })

  return {
    imprimirTicketsIndividuais,
  }
})
