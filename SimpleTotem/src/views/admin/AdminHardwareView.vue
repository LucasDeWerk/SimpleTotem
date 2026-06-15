<template>
  <div class="hw-page">
    <header class="hw-header">
      <button class="hw-back" @click="$router.push({ name: 'admin-panel' })">
        <span class="material-icons">arrow_back</span>
        Voltar ao painel
      </button>
      <h1>Periféricos USB</h1>
    </header>
    <main class="hw-main">
      <PeripheralsConfigPanel show-usb-scan />
    </main>
  </div>
</template>

<script setup>
import PeripheralsConfigPanel from '@/components/admin/PeripheralsConfigPanel.vue'
</script>

<style scoped>
.hw-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #fef9f5 0%, #fef5f0 50%, #fdeee7 100%);
}

.hw-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.5rem;
  background: rgba(255, 255, 255, 0.95);
  border-bottom: 1px solid rgba(245, 124, 0, 0.1);
  box-shadow: 0 2px 12px rgba(245, 124, 0, 0.08);
}

.hw-header h1 {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 800;
  color: #0f172a;
}

.hw-back {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: rgba(245, 124, 0, 0.08);
  border: 1px solid rgba(245, 124, 0, 0.15);
  color: #c2410c;
  border-radius: 8px;
  padding: 0.5rem 0.85rem;
  cursor: pointer;
  font-weight: 700;
  font-size: 0.88rem;
}

.hw-main {
  flex: 1;
  padding: 1.25rem 1.5rem 2rem;
  overflow-y: auto;
}
</style>
