import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useDeviceStore = defineStore('device', () => {
  const deviceUuid = ref(localStorage.getItem('device_uuid') || generateUuid())
  const serialNumber = ref('')
  const appVersion = ref('1.0.0')
  const environment = ref(localStorage.getItem('environment') || 'production')
  const offlineMode = ref(false)
  const lastSeenAt = ref(null)
  const theme = ref(localStorage.getItem('theme') || 'light')
  const isOnline = ref(navigator.onLine)

  function generateUuid() {
    const uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
      const r = Math.random() * 16 | 0
      const v = c === 'x' ? r : (r & 0x3 | 0x8)
      return v.toString(16)
    })
    localStorage.setItem('device_uuid', uuid)
    return uuid
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

  // Inicializar listeners
  function init() {
    applyTheme()
    window.addEventListener('online', updateOnlineStatus)
    window.addEventListener('offline', updateOnlineStatus)
    lastSeenAt.value = new Date().toISOString()
  }

  return {
    deviceUuid,
    serialNumber,
    appVersion,
    environment,
    offlineMode,
    lastSeenAt,
    theme,
    isOnline,
    toggleTheme,
    applyTheme,
    setEnvironment,
    init
  }
})
