import { storeToRefs } from 'pinia'
import { useCompanyStore } from '@/stores/company'

export function useCompanyInitialization() {
  const company = useCompanyStore()
  const { isChecking, hasCompanyData, error, isReady } = storeToRefs(company)

  return {
    isInitializing: isChecking,
    hasCompanyData,
    error,
    isReady,
    checkCompanyData: company.check
  }
}
