<template>
  <div class="admin-login-view">
    <div class="login-content animate-fade-in">
      <div class="login-header">
        <h2 class="login-title">Acesso Administrativo</h2>
        <p class="login-subtitle">Digite o PIN para acessar</p>
      </div>

      <div class="pin-display">
        <span
          v-for="i in 4"
          :key="i"
          class="pin-dot"
          :class="{ filled: pin.length >= i }"
        />
      </div>

      <p v-if="error" class="login-error animate-slide-up">{{ error }}</p>

      <div class="pin-pad">
        <button
          v-for="num in [1,2,3,4,5,6,7,8,9,null,0,'del']"
          :key="num"
          class="pin-key"
          :class="{ invisible: num === null, 'pin-key-del': num === 'del' }"
          :disabled="num === null"
          @click="handleKey(num)"
        >
          <span v-if="num === 'del'">DEL</span>
          <span v-else-if="num !== null">{{ num }}</span>
        </button>
      </div>

      <button class="back-to-totem" @click="goBack">
        < Voltar ao Totem
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAdminStore } from '@/stores/admin'

const router = useRouter()
const admin = useAdminStore()

const pin = ref('')
const error = ref('')

onMounted(() => {
  // Sempre resetar a autenticação ao voltar para login
  // SEMPRE pedir senha antes de acessar admin
  admin.logout()
  pin.value = ''
  error.value = ''
})

function handleKey(key) {
  if (key === 'del') {
    pin.value = pin.value.slice(0, -1)
    error.value = ''
    return
  }
  if (key === null) return
  if (pin.value.length >= 4) return

  pin.value += String(key)
}

watch(pin, (val) => {
  if (val.length === 4) {
    const success = admin.login(val)
    if (success) {
      router.replace({ name: 'admin-panel' })
    } else {
      error.value = 'PIN incorreto'
      setTimeout(() => {
        pin.value = ''
        error.value = ''
      }, 1000)
    }
  }
})

function goBack() {
  router.push({ name: 'home' })
}
</script>


<style scoped>
.admin-login-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(
    135deg,
    #fef9f5 0%,
    #fef5f0 50%,
    #fdeee7 100%
  );
  width: 100vw;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
}

.login-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2xl);
  padding: var(--space-2xl);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-xl);
  box-shadow: 0 20px 60px rgba(245, 124, 0, 0.15);
  max-width: 420px;
  width: 100%;
}

.login-header {
  text-align: center;
}

.login-icon {
  font-size: 3rem;
  display: block;
  margin-bottom: var(--space-lg);
}

.login-title {
  font-size: var(--font-size-2xl);
  font-weight: 900;
  color: #0f172a;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.login-subtitle {
  font-size: var(--font-size-md);
  color: #64748b;
  margin-top: var(--space-md);
  font-weight: 500;
}

.pin-display {
  display: flex;
  gap: var(--space-lg);
  justify-content: center;
}

.pin-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(245, 124, 0, 0.1);
  border: 2px solid rgba(245, 124, 0, 0.2);
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.pin-dot.filled {
  background: #F57C00;
  border-color: #E27602;
  box-shadow: 0 4px 12px rgba(245, 124, 0, 0.3);
  transform: scale(1.15);
}

.login-error {
  color: #f44336;
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-bold);
  padding: var(--space-lg);
  background: rgba(244, 67, 54, 0.1);
  border: 1px solid rgba(244, 67, 54, 0.2);
  border-radius: var(--radius-md);
  text-align: center;
}

.pin-pad {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-md);
  justify-content: center;
  width: 100%;
  max-width: 280px;
}

.pin-key {
  width: 100%;
  aspect-ratio: 1;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, rgba(245, 124, 0, 0.08), rgba(245, 124, 0, 0.04));
  color: #0f172a;
  font-size: var(--font-size-2xl);
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  border: 1px solid rgba(245, 124, 0, 0.15);
  cursor: pointer;
}

.pin-key:active:not(:disabled) {
  background: linear-gradient(135deg, #F57C00, #E27602);
  color: white;
  transform: scale(0.95);
  box-shadow: 0 4px 12px rgba(245, 124, 0, 0.3);
}

.pin-key.invisible {
  visibility: hidden;
}

.pin-key-del {
  font-size: var(--font-size-xl);
  font-weight: 700;
}

.back-to-totem {
  background: none;
  color: var(--color-primary);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-bold);
  padding: var(--space-md) var(--space-lg);
  cursor: pointer;
  transition: all var(--transition-fast);
  border: none;
  letter-spacing: 0.5px;
}

.back-to-totem:hover {
  color: #E27602;
  transform: translateX(-4px);
}

/* ===== Responsividade ===== */
@media (max-width: 480px) {
  .login-content {
    gap: var(--space-xl);
    padding: var(--space-lg);
    max-width: 100%;
  }

  .login-title {
    font-size: var(--font-size-xl);
  }

  .pin-pad {
    max-width: 240px;
  }

  .pin-key {
    min-height: 60px;
  }
}
</style>
