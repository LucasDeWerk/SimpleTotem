import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/services/api'

export const useAdminStore = defineStore('admin', () => {
  const isAuthenticated = ref(localStorage.getItem('admin_authenticated') === 'true')
  const adminPin = ref(localStorage.getItem('admin_pin') || '1234')

  // Token
  const tokenStatus = ref('idle') // idle | syncing | success | error

  // Sync
  const lastFullSync = ref(localStorage.getItem('last_full_sync') || null)
  const syncStatus = ref('idle') // idle | syncing | success | error
  const syncMessage = ref('')
  const syncProgress = ref({
    empresas: false,
    grupos: false,
    subgrupos: false,
    marcas: false,
    medidas: false,
    produtos: false
  })

  function login(pin) {
    // Garantir que ambos sejam strings e comparar
    const enteredPin = String(pin).trim()
    const storedPin = String(adminPin.value).trim()

    if (enteredPin === storedPin) {
      isAuthenticated.value = true
      localStorage.setItem('admin_authenticated', 'true')
      return true
    }
    return false
  }

  function loginAuto() {
    isAuthenticated.value = true
    localStorage.setItem('admin_authenticated', 'true')
  }

  function setCompanyPin(pin) {
    adminPin.value = pin
    localStorage.setItem('admin_pin', pin)
  }

  function logout() {
    isAuthenticated.value = false
    localStorage.removeItem('admin_authenticated')
  }

  /**
   * Sincroniza todos os dados da API
   */
  async function syncAll() {
    syncStatus.value = 'syncing'
    syncMessage.value = 'Iniciando sincronização...'
    resetProgress()

    try {
      console.log('[Admin] 🔄 Sincronizando empresas...')
      await api.sincronizarEmpresas()
      syncProgress.value.empresas = true

      console.log('[Admin] 🔄 Sincronizando grupos...')
      await api.sincronizarGrupos()
      syncProgress.value.grupos = true

      console.log('[Admin] 🔄 Sincronizando subgrupos...')
      await api.sincronizarSubgrupos()
      syncProgress.value.subgrupos = true

      console.log('[Admin] 🔄 Sincronizando marcas...')
      await api.sincronizarMarcas()
      syncProgress.value.marcas = true

      console.log('[Admin] 🔄 Sincronizando medidas...')
      await api.sincronizarMedidas()
      syncProgress.value.medidas = true

      console.log('[Admin] 🔄 Sincronizando produtos...')
      await api.sincronizarProdutos()
      syncProgress.value.produtos = true

      lastFullSync.value = new Date().toISOString()
      localStorage.setItem('last_full_sync', lastFullSync.value)
      
      syncStatus.value = 'success'
      syncMessage.value = '✅ Sincronização completa realizada com sucesso!'
    } catch (err) {
      console.error('[Admin] ❌ Erro na sincronização:', err)
      syncStatus.value = 'error'
      syncMessage.value = `❌ Erro: ${err.message}`
    }
  }

  function resetProgress() {
    syncProgress.value = {
      empresas: false,
      grupos: false,
      subgrupos: false,
      marcas: false,
      medidas: false,
      produtos: false
    }
  }

  function resetSync() {
    syncStatus.value = 'idle'
    syncMessage.value = ''
    resetProgress()
  }

  return {
    isAuthenticated,
    tokenStatus,
    lastFullSync,
    syncStatus,
    syncMessage,
    syncProgress,
    login,
    loginAuto,
    setCompanyPin,
    logout,
    syncAll,
    resetSync
  }
})
