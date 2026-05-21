import { ref, computed } from 'vue'

const isInitializing = ref(false)
const hasCompanyData = ref(true)
const error = ref(null)

export function useCompanyInitialization() {
  const checkCompanyData = async () => {
    // Sem lógica de banco de dados — apenas marca como pronto
    isInitializing.value = false
    hasCompanyData.value = true
  }

  return {
    isInitializing: computed(() => isInitializing.value),
    hasCompanyData: computed(() => hasCompanyData.value),
    error: computed(() => error.value),
    checkCompanyData
  }
}
