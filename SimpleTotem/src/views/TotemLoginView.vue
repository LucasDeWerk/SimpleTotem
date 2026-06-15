<template>
  <div class="totem-login-view">
    <div class="login-content animate-fade-in">
      <div class="login-header">
        <h2 class="login-title">Configuração do Totem</h2>
        <p class="login-subtitle">
          Nenhuma empresa encontrada. Use o usuário e a senha deste computador para configurar.
        </p>
      </div>

      <SystemLoginForm @success="onLoginSuccess" />
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAdminStore } from '@/stores/admin'
import SystemLoginForm from '@/components/admin/SystemLoginForm.vue'

const router = useRouter()
const admin = useAdminStore()

function onLoginSuccess({ usuario }) {
  admin.markAuthenticated(usuario)
  router.replace({ name: 'admin-panel', query: { secao: 'sync' } })
}
</script>

<style scoped>
.totem-login-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #fef9f5 0%, #fef5f0 50%, #fdeee7 100%);
  padding: var(--space-xl);
}

.login-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-2xl);
  width: 100%;
  max-width: 440px;
  padding: var(--space-2xl);
  background: rgba(255, 255, 255, 0.95);
  border-radius: var(--radius-xl);
  box-shadow: 0 20px 60px rgba(245, 124, 0, 0.15);
}

.login-header {
  text-align: center;
}

.login-title {
  font-size: var(--font-size-2xl);
  font-weight: 900;
  color: #0f172a;
  margin: 0;
}

.login-subtitle {
  margin-top: var(--space-md);
  color: #64748b;
  line-height: 1.5;
}

.animate-fade-in {
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
