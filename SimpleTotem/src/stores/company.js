import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '@/services/api'

export const useCompanyStore = defineStore('company', () => {
  const hasCompanyData = ref(null)
  const isChecking = ref(false)
  const error = ref(null)
  let checkPromise = null

  const isReady = computed(() => hasCompanyData.value !== null && !isChecking.value)
  const needsSetup = computed(() => hasCompanyData.value === false)

  async function check() {
    if (checkPromise) return checkPromise

    checkPromise = (async () => {
      isChecking.value = true
      error.value = null

      try {
        const status = await api.obterStatusEmpresa()
        hasCompanyData.value = Boolean(status?.configurada)
      } catch (err) {
        error.value = err.message || 'Não foi possível verificar a empresa'
        hasCompanyData.value = false
      } finally {
        isChecking.value = false
        checkPromise = null
      }

      return hasCompanyData.value
    })()

    return checkPromise
  }

  function markConfigured() {
    hasCompanyData.value = true
    error.value = null
  }

  function reset() {
    hasCompanyData.value = null
    error.value = null
    checkPromise = null
    isChecking.value = false
  }

  return {
    hasCompanyData,
    isChecking,
    error,
    isReady,
    needsSetup,
    check,
    markConfigured,
    reset
  }
})
