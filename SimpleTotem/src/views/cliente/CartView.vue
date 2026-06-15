<template>
  <ScreenContainer
    :title="lang.t.yourCart"
    :subtitle="cart.itemCount + ' ' + (cart.itemCount === 1 ? lang.t.item : lang.t.items)"
  >
    <div v-if="cart.items.length === 0" class="cart-empty">
      <p class="cart-empty-icon">🛒</p>
      <p class="cart-empty-text">{{ lang.t.cartEmpty }}</p>
      <PrimaryActionButton :label="lang.t.viewProducts" @click="goToCategories" />
    </div>
    <div v-else class="cart-wrapper">
      <div class="cart-items">
        <CartItemRow
          v-for="(item, index) in cart.items"
          :key="index"
          :name="item.name"
          :quantity="item.quantity"
          :unitPrice="item.unitPrice"
          :totalPrice="item.totalPrice"
          :notes="item.notes"
          :modifiers="item.modifiers"
          @updateQuantity="cart.updateQuantity(index, $event)"
          @remove="cart.removeItem(index)"
        />
      </div>
      <div class="cart-summary">
        <div class="summary-row">
          <span>{{ lang.t.subtotal }}</span>
          <span>R$ {{ (cart.vendaCalculada?.subtotal ?? cart.subtotal).toFixed(2) }}</span>
        </div>
        <div v-if="(cart.vendaCalculada?.desconto ?? cart.discount) > 0" class="summary-row discount">
          <span>{{ lang.t.discount }}</span>
          <span>- R$ {{ (cart.vendaCalculada?.desconto ?? cart.discount).toFixed(2) }}</span>
        </div>
        <div class="summary-row total">
          <span>{{ lang.t.total }}</span>
          <span>R$ {{ (cart.vendaCalculada?.total ?? cart.total).toFixed(2) }}</span>
        </div>
      </div>
      <p v-if="cart.erroCalculo" class="cart-error">
        {{ cart.erroCalculo }}
      </p>
      <div class="cart-actions">
        <PrimaryActionButton
          :label="lang.t.finalizeOrder"
          :fullWidth="true"
          :disabled="cart.calculandoVenda"
          :loading="cart.calculandoVenda"
          @click="goToPayment"
        />
        <button class="cart-continue-btn" @click="goToCategories">{{ lang.t.continueShopping }}</button>
      </div>
    </div>
  </ScreenContainer>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useCartStore } from '@/stores/cart'
import { useLanguageStore } from '@/stores/language'
import ScreenContainer from '@/components/shared/ScreenContainer.vue'
import CartItemRow from '@/components/shared/CartItemRow.vue'
import PrimaryActionButton from '@/components/shared/PrimaryActionButton.vue'

const router = useRouter()
const cart = useCartStore()
const lang = useLanguageStore()

function goToCategories() {
  router.push({ name: 'catalog' })
}

async function goToPayment() {
  await cart.calcularVenda()
  if (!cart.erroCalculo) {
    router.push({ name: 'payment' })
  }
}
</script>

<style scoped>
.cart-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-xl);
  min-height: 100%;
}
.cart-empty-icon {
  font-size: 5rem;
  opacity: 0.25;
  margin: 0;
  line-height: 1;
}
.cart-empty-text {
  font-size: var(--font-size-2xl);
  color: #64748b;
  font-weight: 500;
  margin: 0;
}
.cart-wrapper {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 100%;
  max-width: 860px;
  width: 100%;
  margin: 0 auto;
  gap: var(--space-2xl);
  padding-bottom: var(--space-3xl);
}
.cart-items {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}
.cart-summary {
  background: linear-gradient(135deg, rgba(245, 124, 0, 0.08), rgba(245, 124, 0, 0.04));
  border: 1px solid rgba(245, 124, 0, 0.15);
  border-radius: var(--radius-lg);
  padding: var(--space-xl);
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}
.summary-row {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-xl);
  color: #0f172a;
  font-weight: 600;
}
.summary-row.discount {
  color: #4caf50;
  font-weight: 700;
}
.summary-row.total {
  font-size: clamp(1.5rem, 4vw, 2.25rem);
  font-weight: 900;
  color: var(--text-color-laranja);
  padding-top: var(--space-lg);
  border-top: 2px solid rgba(245, 124, 0, 0.15);
  letter-spacing: -0.01em;
}
.cart-error {
  color: #f44336;
  font-size: var(--font-size-md);
  font-weight: 600;
  padding: var(--space-md) var(--space-lg);
  background: rgba(244, 67, 54, 0.08);
  border-radius: var(--radius-md);
  border: 1px solid rgba(244, 67, 54, 0.2);
  text-align: center;
}
.cart-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  align-items: center;
}
.cart-continue-btn {
  background: none;
  border: none;
  color: var(--color-primary);
  font-size: var(--font-size-lg);
  font-weight: 700;
  min-height: var(--btn-min-height);
  min-width: 48px;
  padding: var(--space-md) var(--space-xl);
  cursor: pointer;
  transition: all var(--transition-fast);
  letter-spacing: 0.5px;
}
.cart-continue-btn:hover  { color: #E27602; transform: translateX(-4px); }
.cart-continue-btn:active { opacity: 0.8; transform: translateX(0); }
</style>
