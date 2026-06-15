import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useCartStore } from './cart'

export const useSessionStore = defineStore('session', () => {
  const sessionId = ref(null)
  const startedAt = ref(null)
  const timeoutSeconds = ref(120)
  const secondsLeft = ref(0)
  const isActive = ref(false)
  const paused = ref(false)

  let timeoutTimer = null
  let countdownInterval = null

  function generateSessionId() {
    return 'sess_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9)
  }

  function clearTimers() {
    clearTimeout(timeoutTimer)
    clearInterval(countdownInterval)
    timeoutTimer = null
    countdownInterval = null
  }

  function startCountdown() {
    clearInterval(countdownInterval)
    countdownInterval = setInterval(() => {
      if (paused.value) return
      secondsLeft.value--
      if (secondsLeft.value <= 0) {
        clearInterval(countdownInterval)
      }
    }, 1000)
  }

  function startSession() {
    sessionId.value = generateSessionId()
    startedAt.value = new Date().toISOString()
    isActive.value = true
    paused.value = false
    resetTimer()
  }

  function resetTimer() {
    if (paused.value || !isActive.value) return

    clearTimers()
    secondsLeft.value = timeoutSeconds.value
    startCountdown()

    timeoutTimer = setTimeout(() => {
      endSession()
    }, timeoutSeconds.value * 1000)
  }

  function pauseSession() {
    if (!isActive.value || paused.value) return
    paused.value = true
    clearTimers()
  }

  function resumeSession() {
    if (!isActive.value || !paused.value) return
    paused.value = false
    resetTimer()
  }

  function endSession() {
    clearTimers()

    sessionId.value = null
    startedAt.value = null
    isActive.value = false
    paused.value = false
    secondsLeft.value = 0

    const cart = useCartStore()
    cart.clearCart()
  }

  function destroy() {
    clearTimers()
  }

  return {
    sessionId,
    startedAt,
    timeoutSeconds,
    secondsLeft,
    isActive,
    paused,
    startSession,
    resetTimer,
    pauseSession,
    resumeSession,
    endSession,
    destroy,
  }
})
