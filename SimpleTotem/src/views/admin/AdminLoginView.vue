<template>
  <div class="admin-login-view">
    <div class="login-content animate-fade-in">
      <div class="login-header">
        <h2 class="login-title">Acesso Administrativo</h2>
        <p class="login-subtitle">
          Use o usuário e a senha de login deste computador.
        </p>
      </div>

      <SystemLoginForm submit-label="Acessar painel" @success="onLoginSuccess" />

      <button v-if="company.hasCompanyData" class="back-to-totem" @click="goBack">
        < Voltar ao Totem
      </button>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAdminStore } from '@/stores/admin'
import { useCompanyStore } from '@/stores/company'
import SystemLoginForm from '@/components/admin/SystemLoginForm.vue'

const router = useRouter()
const admin = useAdminStore()
const company = useCompanyStore()

onMounted(() => {
  admin.logout()
})

function onLoginSuccess({ usuario }) {
  admin.markAuthenticated(usuario)
  router.replace({ name: 'admin-panel' })
}

function goBack() {
  if (company.hasCompanyData) {
    router.push({ name: 'home' })
    return
  }
  router.push({ name: 'totem-login' })
}
</script>

<style scoped>
.admin-login-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #fef9f5 0%, #fef5f0 50%, #fdeee7 100%);
  width: 100vw;
  position: fixed;
  inset: 0;
  z-index: 1000;
}

.login-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2xl);
  padding: var(--space-2xl);
  background: rgba(255, 255, 255, 0.95);
  border-radius: var(--radius-xl);
  box-shadow: 0 20px 60px rgba(245, 124, 0, 0.15);
  max-width: 440px;
  width: 100%;
}

.login-header {
  text-align: center;
  width: 100%;
}

.login-title {
  font-size: var(--font-size-2xl);
  font-weight: 900;
  color: #0f172a;
  margin: 0;
}

.login-subtitle {
  font-size: var(--font-size-md);
  color: #64748b;
  margin-top: var(--space-md);
  line-height: 1.5;
}

.back-to-totem {
  background: none;
  color: var(--color-primary);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-bold);
  padding: var(--space-md) var(--space-lg);
  cursor: pointer;
  border: none;
}

.back-to-totem:hover {
  color: #e27602;
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
