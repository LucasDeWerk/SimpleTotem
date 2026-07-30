<template>
  <form class="login-form" @submit.prevent="handleSubmit">
    <label class="field">
      <span>Email SimpleSfique</span>
      <input
        v-model.trim="email"
        type="email"
        autocomplete="username"
        :disabled="loading"
        placeholder="admin@minhaempresa.com.br"
      />
    </label>

    <label class="field">
      <span>Senha</span>
      <input
        v-model="senha"
        type="password"
        autocomplete="current-password"
        :disabled="loading"
        placeholder="Senha da conta"
      />
    </label>

    <p v-if="error" class="login-error">{{ error }}</p>

    <button class="btn-enter" type="submit" :disabled="loading || !canSubmit">
      {{ loading ? 'Conectando...' : 'Conectar e sincronizar empresa' }}
    </button>
  </form>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import * as api from '@/services/api'
import { useAdminStore } from '@/stores/admin'
import { useSimpleSfiqueStore } from '@/stores/simplesfique'

const emit = defineEmits(['success', 'requires-selection'])

const admin = useAdminStore()
const simplesfique = useSimpleSfiqueStore()

const email = ref('')
const senha = ref('')
const error = ref('')
const loading = ref(false)

const canSubmit = computed(() => email.value.length > 0 && senha.value.length > 0)

onMounted(() => {
  if (simplesfique.sessao?.email) email.value = simplesfique.sessao.email
})

async function handleSubmit() {
  if (!canSubmit.value || loading.value) return

  loading.value = true
  error.value = ''

  try {
    const result = await api.loginSimpleSfique({
      email: email.value,
      senha: senha.value,
      os_usuario: admin.adminUser || undefined,
      senha_os: admin.osSenha || undefined,
    })
    if (result.sessao) {
      simplesfique.setSessao(result.sessao)
    }
    if (result.requires_selection) {
      emit('requires-selection', result.empresas || [])
      return
    }
    emit('success', result.empresa)
  } catch (err) {
    error.value = err.message || 'Falha ao conectar ao SimpleSfique'
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
