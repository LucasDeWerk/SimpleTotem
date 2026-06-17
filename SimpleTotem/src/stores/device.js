import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { obterTerminalAtual } from '@/services/api'

export const useDeviceStore = defineStore('device', () => {
  const deviceUuid = ref(localStorage.getItem('device_uuid') || generateUuid())
  const serialNumber = ref('')
  const appVersion = ref('1.0.0')
  const environment = ref(localStorage.getItem('environment') || 'production')
  const offlineMode = ref(false)
  const lastSeenAt = ref(null)
  const theme = ref(localStorage.getItem('theme') || 'light')
  const isOnline = ref(navigator.onLine)
  const terminalId = ref(null)
  const terminalInfo = ref(null)
  const terminalLoaded = ref(false)

  function generateUuid() {
    const uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
      const r = Math.random() * 16 | 0
      const v = c === 'x' ? r : (r & 0x3 | 0x8)
      return v.toString(16)
    })
    localStorage.setItem('device_uuid', uuid)
    return uuid
  }

  async function loadTerminal(force = false) {
    if (terminalLoaded.value && !force) return terminalInfo.value
    try {
      const terminal = await obterTerminalAtual()
      terminalInfo.value = terminal
      terminalId.value = terminal?.id ?? null
    } catch (err) {
      console.warn('[Device] Terminal não identificado:', err.message)
      terminalInfo.value = null
      terminalId.value = null
    } finally {
      terminalLoaded.value = true
    }
    return terminalInfo.value
  }

  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
    localStorage.setItem('theme', theme.value)
    document.documentElement.setAttribute('data-theme', theme.value)
  }

  function applyTheme() {
    document.documentElement.setAttribute('data-theme', theme.value)
  }

  function updateOnlineStatus() {
    isOnline.value = navigator.onLine
  }

  function setEnvironment(env) {
    environment.value = env
    localStorage.setItem('environment', env)
  }

  function init() {
    applyTheme()
    window.addEventListener('online', updateOnlineStatus)
    window.addEventListener('offline', updateOnlineStatus)
    lastSeenAt.value = new Date().toISOString()
    loadTerminal()
  }

  const terminalLabel = computed(() =>
    terminalInfo.value?.descterminal || (terminalId.value ? `Terminal #${terminalId.value}` : 'Não configurado')
  )

  return {
    deviceUuid,
    serialNumber,
    appVersion,
    environment,
    offlineMode,
    lastSeenAt,
    theme,
    isOnline,
    terminalId,
    terminalInfo,
    terminalLabel,
    terminalLoaded,
    loadTerminal,
    toggleTheme,
    applyTheme,
    setEnvironment,
    init
  }
})
