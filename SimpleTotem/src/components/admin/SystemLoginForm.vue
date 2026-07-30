<template>
  <form class="login-form" @submit.prevent="handleSubmit">
    <label class="field">
      <span>Usuário do computador</span>
      <input
        v-model.trim="usuario"
        type="text"
        autocomplete="username"
        :disabled="loading"
        placeholder="Ex.: totem"
      />
    </label>

    <label class="field">
      <span>Senha</span>
      <input
        v-model="senha"
        type="password"
        autocomplete="current-password"
        :disabled="loading"
        placeholder="Senha de login do sistema"
      />
    </label>

    <p v-if="error" class="login-error">{{ error }}</p>

    <button class="btn-enter" type="submit" :disabled="loading || !canSubmit">
      {{ loading ? 'Entrando...' : submitLabel }}
    </button>
  </form>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import * as api from '@/services/api'

const props = defineProps({
  submitLabel: { type: String, default: 'Entrar' }
})

const emit = defineEmits(['success'])

const usuario = ref('')
const senha = ref('')
const error = ref('')
const loading = ref(false)

const canSubmit = computed(() => usuario.value.length > 0 && senha.value.length > 0)

onMounted(async () => {
  try {
    const electronUser = await window.electronAPI?.getSystemUser?.()
    if (electronUser) {
      usuario.value = electronUser
      return
    }
  } catch {
    // Electron indisponível (dev web)
  }

  try {
    const data = await api.obterUsuarioSugerido()
    if (data?.usuario) usuario.value = data.usuario
  } catch {
    // Sem sugestão — usuário digita manualmente
  }
})

async function handleSubmit() {
  if (!canSubmit.value || loading.value) return

  loading.value = true
  error.value = ''

  try {
    await api.loginSistema(usuario.value, senha.value)
    emit('success', { usuario: usuario.value })
  } catch (err) {
    error.value = err.message || 'Falha ao autenticar'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
  width: 100%;
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  font-weight: 600;
  color: #334155;
}

.field input {
  min-height: 52px;
  padding: 0 var(--space-lg);
  border: 2px solid rgba(245, 124, 0, 0.15);
  border-radius: var(--radius-md);
  font-size: var(--font-size-md);
  background: white;
}

.field input:focus {
  outline: none;
  border-color: #f57c00;
}

.login-error {
  color: #f44336;
  background: rgba(244, 67, 54, 0.1);
  border: 1px solid rgba(244, 67, 54, 0.2);
  border-radius: var(--radius-md);
  padding: var(--space-md);
  text-align: center;
}

.btn-enter {
  min-height: var(--btn-min-height);
  border: none;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, #f57c00 0%, #e27602 100%);
  color: white;
  font-size: var(--font-size-lg);
  font-weight: 700;
  cursor: pointer;
}

.btn-enter:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
