import { onMounted, onUnmounted } from 'vue'
import { useSessionStore } from '@/stores/session'

export function useIdleTimer() {
  const session = useSessionStore()

  const events = ['touchstart', 'mousedown', 'mousemove', 'keydown', 'scroll']

  function handleActivity() {
    if (session.isActive) {
      session.resetTimer()
    }
  }

  onMounted(() => {
    events.forEach(event => {
      document.addEventListener(event, handleActivity, { passive: true })
    })
  })

  onUnmounted(() => {
    events.forEach(event => {
      document.removeEventListener(event, handleActivity)
    })
  })
}
