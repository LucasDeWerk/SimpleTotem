<template>
  <ScreenContainer :title="lang.t.dineInQuestion" :subtitle="lang.t.dineInSubtitle">
    <div class="consumption-options">
      <button class="consumption-card" type="button" @click="choose('local')">
        <span class="consumption-icon">🍽️</span>
        <span class="consumption-label">{{ lang.t.dineIn }}</span>
      </button>
      <button class="consumption-card" type="button" @click="choose('viagem')">
        <span class="consumption-icon">🛍️</span>
        <span class="consumption-label">{{ lang.t.takeaway }}</span>
      </button>
    </div>
  </ScreenContainer>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'
import { useLanguageStore } from '@/stores/language'
import ScreenContainer from '@/components/shared/ScreenContainer.vue'

const router = useRouter()
const cart = useCartStore()
const lang = useLanguageStore()

onMounted(() => {
  // sem itens não há o que finalizar; a escolha é sempre refeita a cada pedido
  if (cart.items.length === 0) {
    router.replace({ name: 'catalog' })
    return
  }
  cart.modoConsumo = null
})

function choose(modo) {
  cart.modoConsumo = modo
  router.push({ name: 'payment' })
}
</script>

<style scoped>
.consumption-options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2xl);
  max-width: 860px;
  width: 100%;
  min-height: 100%;
  margin: 0 auto;
  align-content: center;
}

.consumption-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-xl);
  min-height: 320px;
  padding: var(--space-2xl);
  background: var(--bg-card);
  border: 2px solid rgba(245, 124, 0, 0.15);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: transform var(--transition-fast), border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.consumption-card:hover {
  border-color: #F57C00;
  box-shadow: 0 12px 32px rgba(245, 124, 0, 0.2);
}

.consumption-card:active {
  transform: scale(0.98);
}

.consumption-icon {
  font-size: 5rem;
  line-height: 1;
}

.consumption-label {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: #0f172a;
  text-align: center;
}

@media (max-width: 768px) {
  .consumption-options {
    grid-template-columns: 1fr;
  }
  .consumption-card {
    min-height: 200px;
  }
}
</style>
