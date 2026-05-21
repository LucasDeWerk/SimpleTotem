import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const translations = {
  'pt-BR': {
    flag: '🇧🇷',
    label: 'Português',
    welcome: 'Bem-vindo!',
    tapToStart: 'Toque para começar sua compra',
    startOrder: 'INICIAR COMPRA',
  },
  'en-US': {
    flag: '🇺🇸',
    label: 'English',
    welcome: 'Welcome!',
    tapToStart: 'Tap to start your order',
    startOrder: 'START ORDER',
  },
  'es-ES': {
    flag: '🇪🇸',
    label: 'Español',
    welcome: '¡Bienvenido!',
    tapToStart: 'Toca para comenzar tu compra',
    startOrder: 'INICIAR COMPRA',
  },
}

const localeOrder = ['pt-BR', 'en-US', 'es-ES']

export const useLanguageStore = defineStore('language', () => {
  const currentLocale = ref(localStorage.getItem('totem_locale') || 'pt-BR')

  const t = computed(() => translations[currentLocale.value] || translations['pt-BR'])

  const currentFlag = computed(() => t.value.flag)
  const currentLabel = computed(() => t.value.label)

  function cycleLanguage() {
    const idx = localeOrder.indexOf(currentLocale.value)
    const next = localeOrder[(idx + 1) % localeOrder.length]
    currentLocale.value = next
    localStorage.setItem('totem_locale', next)
  }

  function setLocale(locale) {
    if (translations[locale]) {
      currentLocale.value = locale
      localStorage.setItem('totem_locale', locale)
    }
  }

  return {
    currentLocale,
    t,
    currentFlag,
    currentLabel,
    cycleLanguage,
    setLocale,
    localeOrder,
    translations,
  }
})

