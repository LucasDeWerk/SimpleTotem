import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from './cart'

export const useSessionStore = defineStore('session', () => {
  const sessionId = ref(null)
  const startedAt = ref(null)
  const timeoutSeconds = ref(90)
  const secondsLeft = ref(0)
  const isActive = ref(false)

  let timeoutTimer = null
  let countdownInterval = null

  function generateSessionId() {
    return 'sess_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9)
  }

  function startSession() {
    sessionId.value = generateSessionId()
    startedAt.value = new Date().toISOString()
    isActive.value = true
    resetTimer()
  }

  function resetTimer() {
    clearTimeout(timeoutTimer)
    clearInterval(countdownInterval)
    secondsLeft.value = timeoutSeconds.value

    countdownInterval = setInterval(() => {
      secondsLeft.value--
      if (secondsLeft.value <= 0) {
        clearInterval(countdownInterval)
      }
    }, 1000)

    timeoutTimer = setTimeout(() => {
      endSession()
    }, timeoutSeconds.value * 1000)
  }

  function endSession() {
    clearTimeout(timeoutTimer)
    clearInterval(countdownInterval)

    sessionId.value = null
    startedAt.value = null
    isActive.value = false
    secondsLeft.value = 0

    // Limpar carrinho
    const cart = useCartStore()
    cart.clearCart()
  }

  function destroy() {
    clearTimeout(timeoutTimer)
    clearInterval(countdownInterval)
  }

  return {
    sessionId,
    startedAt,
    timeoutSeconds,
    secondsLeft,
    isActive,
    startSession,
    resetTimer,
    endSession,
    destroy
  }
})
