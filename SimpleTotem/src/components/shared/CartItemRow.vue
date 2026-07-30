<template>
  <div class="cart-item-row">
    <div class="item-info">
      <h4 class="item-name">{{ name }}</h4>
      <p v-if="modifiers && modifiers.length" class="item-modifiers">
        {{ modifiers.map(m => m.name).join(', ') }}
      </p>
      <p v-if="notes" class="item-notes">{{ lang.t.notesPrefix }} {{ notes }}</p>
    </div>
    <div class="item-bottom">
      <div class="item-controls">
        <QuantityStepper
          :modelValue="quantity"
          :min="0"
          @update:modelValue="$emit('updateQuantity', $event)"
        />
      </div>
      <div class="item-prices">
        <span class="item-unit-price">R$ {{ unitPrice.toFixed(2) }} {{ lang.t.unitPrice }}</span>
        <span class="item-total-price">R$ {{ totalPrice.toFixed(2) }}</span>
      </div>
      <button
        class="item-remove"
        type="button"
        :aria-label="lang.t.removeItem"
        @click="$emit('remove')"
      >
        <span class="item-remove-icon" aria-hidden="true">🗑</span>
        <span class="item-remove-label">{{ lang.t.removeItem }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { useLanguageStore } from '@/stores/language'
import QuantityStepper from './QuantityStepper.vue'

defineProps({
  name: { type: String, required: true },
  quantity: { type: Number, required: true },
  unitPrice: { type: Number, required: true },
  totalPrice: { type: Number, required: true },
  notes: { type: String, default: '' },
  modifiers: { type: Array, default: () => [] },
})

defineEmits(['updateQuantity', 'remove'])

const lang = useLanguageStore()
</script>

<style scoped>
.cart-item-row {
  display: flex;
  align-items: center;
  gap: var(--space-md);
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

.item-bottom {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  flex-shrink: 0;
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
  opacity: 0.8;
  margin-top: 2px;
}

.item-controls {
  flex-shrink: 0;
}

.item-prices {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  min-width: 100px;
  flex-shrink: 0;
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
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  min-width: 64px;
  min-height: 52px;
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-md);
  background: rgba(244, 67, 54, 0.08);
  color: var(--color-error);
  border: 1px solid rgba(244, 67, 54, 0.15);
  transition: background var(--transition-fast);
  flex-shrink: 0;
  cursor: pointer;
}

.item-remove:active {
  background: rgba(244, 67, 54, 0.15);
}

.item-remove-icon {
  font-size: 1.25rem;
  line-height: 1;
}

.item-remove-label {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

@media (max-width: 720px) {
  .cart-item-row {
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-md);
  }

  .item-bottom {
    justify-content: space-between;
    width: 100%;
  }

  .item-prices {
    align-items: flex-start;
    min-width: 0;
  }
}
</style>
