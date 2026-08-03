import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/services/api'

export const useAdminStore = defineStore('admin', () => {
  const isAuthenticated = ref(sessionStorage.getItem('admin_authenticated') === 'true')
  const adminUser = ref('')
  const osSenha = ref('')

  async function login(usuario, senha) {
    await api.loginSistema(usuario, senha)
    isAuthenticated.value = true
    adminUser.value = usuario
    osSenha.value = senha
    sessionStorage.setItem('admin_authenticated', 'true')
    return true
  }

  function markAuthenticated(usuario) {
    isAuthenticated.value = true
    if (usuario) adminUser.value = usuario
    sessionStorage.setItem('admin_authenticated', 'true')
  }

  function logout() {
    isAuthenticated.value = false
    adminUser.value = ''
    osSenha.value = ''
    sessionStorage.removeItem('admin_authenticated')
    sessionStorage.removeItem('admin_token')
  }

  return {
    isAuthenticated,
    adminUser,
    osSenha,
    login,
    markAuthenticated,
    logout,
  }
})
