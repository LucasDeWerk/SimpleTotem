<template>
  <transition name="slide-up">
    <button
      v-if="visible && itemsCount > 0"
      class="floating-cart-btn"
      @click="$emit('click')"
    >

      <span class="fcb-info">
        <span class="fcb-count">{{ itemsCount }} {{ itemsCount === 1 ? 'item' : 'itens' }}</span>
        <span class="fcb-total">R$ {{ total.toFixed(2) }}</span>
      </span>
      <span class="fcb-arrow">></span>
    </button>
  </transition>
</template>

<script setup>
defineProps({
  itemsCount: { type: Number, default: 0 },
  total: { type: Number, default: 0 },
  visible: { type: Boolean, default: true }
})

defineEmits(['click'])
</script>

<style scoped>
.floating-cart-btn {
  position: fixed;
  bottom: var(--space-lg);
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: var(--space-md);
  background: var(--color-primary);
  color: white;
  padding: var(--space-md) var(--space-xl);
  border-radius: var(--radius-full);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  box-shadow: 0 8px 32px rgba(245, 124, 0, 0.4);
  min-height: var(--btn-min-height);
  z-index: 200;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}

.floating-cart-btn:active {
  transform: translateX(-50%) scale(0.97);
  box-shadow: 0 4px 16px rgba(245, 124, 0, 0.4);
}

.fcb-icon {
  font-size: 1.5rem;
}

.fcb-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.2;
}

.fcb-count {
  font-size: var(--font-size-sm);
  opacity: 0.9;
}

.fcb-total {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
}

.fcb-arrow {
  font-size: 1.5rem;
  margin-left: var(--space-sm);
}
</style>
