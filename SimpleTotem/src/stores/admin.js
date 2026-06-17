import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/services/api'
import { useCompanyStore } from '@/stores/company'

export const useAdminStore = defineStore('admin', () => {
  const isAuthenticated = ref(sessionStorage.getItem('admin_authenticated') === 'true')
  const adminUser = ref(localStorage.getItem('admin_user') || '')
  /** Senha OS em memória — usada ao salvar empresa, nunca no localStorage. */
  const osSenha = ref('')

  const tokenStatus = ref('idle')
  const lastFullSync = ref(localStorage.getItem('last_full_sync') || null)
  const syncStatus = ref('idle')
  const syncMessage = ref('')
  const syncProgress = ref({
    empresas: false,
    grupos: false,
    subgrupos: false,
    marcas: false,
    medidas: false,
    produtos: false
  })

  async function login(usuario, senha) {
    await api.loginSistema(usuario, senha)
    isAuthenticated.value = true
    adminUser.value = usuario
    osSenha.value = senha
    sessionStorage.setItem('admin_authenticated', 'true')
    localStorage.setItem('admin_user', usuario)
    return true
  }

  function markAuthenticated(usuario) {
    isAuthenticated.value = true
    adminUser.value = usuario || adminUser.value
    sessionStorage.setItem('admin_authenticated', 'true')
    if (usuario) localStorage.setItem('admin_user', usuario)
  }

  function logout() {
    isAuthenticated.value = false
    adminUser.value = ''
    osSenha.value = ''
    sessionStorage.removeItem('admin_authenticated')
    sessionStorage.removeItem('admin_token')
    localStorage.removeItem('admin_user')
  }

  async function syncAll() {
    syncStatus.value = 'syncing'
    syncMessage.value = 'Iniciando sincronização...'
    resetProgress()

    try {
      const resultado = await api.sincronizarCompleto()
      const etapas = resultado?.etapas || {}

      syncProgress.value.empresas = Boolean(etapas.empresa)
      syncProgress.value.grupos = Boolean(etapas.grupos)
      syncProgress.value.subgrupos = Boolean(etapas.subgrupos)
      syncProgress.value.marcas = Boolean(etapas.marcas)
      syncProgress.value.medidas = Boolean(etapas.medidas)
      syncProgress.value.produtos = Boolean(etapas.produtos)

      lastFullSync.value = new Date().toISOString()
      localStorage.setItem('last_full_sync', lastFullSync.value)

      syncStatus.value = 'success'
      syncMessage.value = '✅ Sincronização completa realizada com sucesso!'

      const company = useCompanyStore()
      await company.check()
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
    adminUser,
    osSenha,
    tokenStatus,
    lastFullSync,
    syncStatus,
    syncMessage,
    syncProgress,
    login,
    markAuthenticated,
    logout,
    syncAll,
    resetSync
  }
})
