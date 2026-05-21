<template>
  <div class="cart-item-row">
    <div class="item-info">
      <h4 class="item-name">{{ name }}</h4>
      <p v-if="modifiers && modifiers.length" class="item-modifiers">
        {{ modifiers.map(m => m.name).join(', ') }}
      </p>
      <p v-if="notes" class="item-notes">[N] {{ notes }}</p>
    </div>
    <div class="item-controls">
      <QuantityStepper
        :modelValue="quantity"
        :min="0"
        @update:modelValue="$emit('updateQuantity', $event)"
      />
    </div>
    <div class="item-prices">
      <span class="item-unit-price">R$ {{ unitPrice.toFixed(2) }} un.</span>
      <span class="item-total-price">R$ {{ totalPrice.toFixed(2) }}</span>
    </div>
    <button class="item-remove" @click="$emit('remove')">X</button>
  </div>
</template>

<script setup>
import QuantityStepper from './QuantityStepper.vue'

defineProps({
  name: { type: String, required: true },
  quantity: { type: Number, required: true },
  unitPrice: { type: Number, required: true },
  totalPrice: { type: Number, required: true },
  notes: { type: String, default: '' },
  modifiers: { type: Array, default: () => [] }
})

defineEmits(['updateQuantity', 'remove'])
</script>

<style scoped>
.cart-item-row {
  display: flex;
  align-items: center;
  gap: var(--space-lg);
  padding: var(--space-lg) var(--space-xl);
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  min-height: 90px;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--text-color);
}

.item-modifiers {
  font-size: var(--font-size-sm);
  color: var(--text-color-fourth);
  opacity: 0.7;
  margin-top: 2px;
}

.item-notes {
  font-size: var(--font-size-sm);
  color: var(--text-color-fourth);
  opacity: 0.6;
  margin-top: 2px;
}

.item-controls {
  flex-shrink: 0;
}

.item-prices {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  min-width: 120px;
}

.item-unit-price {
  font-size: var(--font-size-sm);
  color: var(--text-color-fourth);
  opacity: 0.6;
}

.item-total-price {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-color-laranja);
}

.item-remove {
  width: 52px;
  height: 52px;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-error);
  font-size: 1.4rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background var(--transition-fast);
  flex-shrink: 0;
}

.item-remove:active {
  background: rgba(244, 67, 54, 0.1);
}
</style>
