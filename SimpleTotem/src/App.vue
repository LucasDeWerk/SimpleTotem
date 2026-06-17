<template>
  <router-view v-slot="{ Component, route }">
    <div v-if="showBootstrapLoading" class="loading-container">
      <div class="spinner" />
      <p>Verificando configuração do totem...</p>
      <p v-if="company.error" class="loading-error">{{ company.error }}</p>
    </div>

    <transition v-else name="fade" mode="out-in">
      <component :is="Component" :key="route.path" />
    </transition>
  </router-view>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useCompanyStore } from '@/stores/company'
import { useSimpleSfiqueStore } from '@/stores/simplesfique'
import { useDeviceStore } from '@/stores/device'

const route = useRoute()
const company = useCompanyStore()

const SETUP_ROUTES = new Set(['totem-login', 'admin-login', 'admin-panel', 'admin-hardware'])

const showBootstrapLoading = computed(() => {
  if (company.isReady) return false
  return !SETUP_ROUTES.has(route.name)
})

onMounted(() => {
  if (company.hasCompanyData === null) {
    company.check()
  }
  useSimpleSfiqueStore().hydrate()
  useDeviceStore().init()
})
</script>

<style>
#app {
  width: 100%;
  height: 100%;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid rgba(255, 255, 255, 0.3);
  border-top: 4px solid white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-container p {
  font-size: 16px;
  margin: 0;
}

.loading-error {
  margin-top: 12px !important;
  max-width: 420px;
  text-align: center;
  opacity: 0.9;
}
</style>
