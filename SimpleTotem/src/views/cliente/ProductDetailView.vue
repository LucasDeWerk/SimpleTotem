<template>
  <ScreenContainer v-if="product">
    <div class="product-detail">
      <div class="pd-image-area">
        <img v-if="productImage" :src="productImage" :alt="product.descproduto" class="pd-image" />
        <div v-else class="pd-image-placeholder">[ Imagem ]</div>
        <span v-if="product.badge" class="pd-badge">{{ product.badge }}</span>
      </div>

      <div class="pd-info">
        <h2 class="pd-name">{{ product.descproduto }}</h2>
        <p class="pd-description">{{ product.descsubgrupo }} - {{ product.descmarca }}</p>
        <span class="pd-price">R$ {{ finalPrice.toFixed(2) }}</span>
      </div>

      <div class="pd-quantity">
        <span class="pd-qty-label">Quantidade:</span>
        <QuantityStepper v-model="quantity" :min="1" :max="20" />
      </div>

      <!-- Observações -->
      <div class="pd-notes">
        <label class="pd-notes-label">Observações (opcional):</label>
        <textarea
          v-model="notes"
          class="pd-notes-input"
          placeholder="Ex: Sem cebola, bem passado..."
          rows="2"
        ></textarea>
      </div>

      <div class="pd-total">
        <span class="pd-total-label">Total:</span>
        <span class="pd-total-value">R$ {{ (finalPrice * quantity).toFixed(2) }}</span>
      </div>

      <div class="pd-actions">
        <PrimaryActionButton
          label="ADICIONAR AO CARRINHO"
          icon="shopping-cart"
          :fullWidth="true"
          @click="addToCart"
        />
      </div>
    </div>
  </ScreenContainer>

  <ScreenContainer v-else centered>
    <p>Produto não encontrado.</p>
  </ScreenContainer>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCatalogStore } from '@/stores/catalog'
import { useCartStore } from '@/stores/cart'
import ScreenContainer from '@/components/shared/ScreenContainer.vue'
import QuantityStepper from '@/components/shared/QuantityStepper.vue'
import PrimaryActionButton from '@/components/shared/PrimaryActionButton.vue'

const route = useRoute()
const router = useRouter()
const catalog = useCatalogStore()
const cart = useCartStore()

const product = ref(null)
const quantity = ref(1)
const notes = ref('')

onMounted(async () => {
  const idProduto = route.params.id
  // Buscar produto do catálogo carregado
  product.value = catalog.getProductById(idProduto)

  if (!product.value) {
    // Se não encontrar, recarregar catálogo
    await catalog.fetchCatalog()
    product.value = catalog.getProductById(idProduto)
  }
})

const productImage = computed(() => product.value?.foto || product.value?.image || '')

const finalPrice = computed(() => {
  if (!product.value) return 0
  return product.value.preco_venda || product.value.price || 0
})

function addToCart() {
  if (!product.value) return

  cart.addItem({
    id: product.value.id_produto,
    name: product.value.descproduto,
    price: finalPrice.value,
    image: productImage.value
  }, quantity.value, notes.value)

  router.back()
}
</script>

<style scoped>
.product-detail {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
  padding-bottom: 100px;
}

.pd-image-area {
  position: relative;
  width: 100%;
  height: 320px;
  border-radius: var(--radius-xl);
  overflow: hidden;
  background: linear-gradient(135deg, rgba(245, 124, 0, 0.1), rgba(245, 124, 0, 0.05));
  box-shadow: 0 8px 24px rgba(245, 124, 0, 0.15);
}

.pd-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.pd-image-area:hover .pd-image {
  transform: scale(1.05);
}

.pd-image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 5rem;
  background: linear-gradient(135deg, rgba(245, 124, 0, 0.08), rgba(245, 124, 0, 0.04));
  color: var(--color-primary);
}

.pd-badge {
  position: absolute;
  top: var(--space-lg);
  right: var(--space-lg);
  padding: 8px 18px;
  border-radius: var(--radius-full);
  background: linear-gradient(135deg, #F57C00, #E27602);
  color: white;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  box-shadow: 0 8px 24px rgba(245, 124, 0, 0.3);
  letter-spacing: 0.5px;
}

.pd-info {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  padding: var(--space-md) 0;
  border-bottom: 1px solid rgba(245, 124, 0, 0.08);
}

.pd-name {
  font-size: var(--font-size-3xl);
  font-weight: 900;
  color: #0f172a;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.pd-description {
  font-size: var(--font-size-md);
  color: #64748b;
  line-height: 1.6;
  font-weight: 500;
}

.pd-price {
  font-size: var(--font-size-3xl);
  font-weight: 900;
  color: var(--text-color-laranja);
  letter-spacing: -0.01em;
}

.pd-quantity {
  display: flex;
  align-items: center;
  gap: var(--space-lg);
  padding: var(--space-lg) 0;
  border-bottom: 1px solid rgba(245, 124, 0, 0.08);
}

.pd-qty-label {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  color: #0f172a;
}

.pd-notes {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  padding: var(--space-lg) 0;
}

.pd-notes-label {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  color: #0f172a;
}

.pd-notes-input {
  padding: var(--space-md);
  border: 1px solid rgba(245, 124, 0, 0.15);
  border-radius: var(--radius-md);
  background: rgba(245, 124, 0, 0.03);
  color: var(--text-color);
  font-size: var(--font-size-md);
  resize: none;
  min-height: var(--input-min-height);
  font-family: inherit;
  transition: all var(--transition-fast);
}

.pd-notes-input:focus {
  outline: none;
  border-color: rgba(245, 124, 0, 0.3);
  background: rgba(245, 124, 0, 0.05);
}

.pd-notes-input::placeholder {
  color: #cbd5e1;
  opacity: 1;
}

.pd-total {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-lg);
  background: linear-gradient(135deg, rgba(245, 124, 0, 0.08), rgba(245, 124, 0, 0.04));
  border-radius: var(--radius-md);
  border: 1px solid rgba(245, 124, 0, 0.15);
}

.pd-total-label {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  color: #0f172a;
}

.pd-total-value {
  font-size: var(--font-size-2xl);
  font-weight: 900;
  color: var(--text-color-laranja);
  letter-spacing: -0.01em;
}

.pd-actions {
  padding-top: var(--space-md);
}

/* ===== Responsividade ===== */
@media (max-width: 768px) {
  .pd-image-area {
    height: 240px;
  }

  .pd-name {
    font-size: var(--font-size-2xl);
  }

  .pd-price {
    font-size: var(--font-size-2xl);
  }
}

@media (max-width: 480px) {
  .pd-image-area {
    height: 200px;
  }

  .pd-name {
    font-size: var(--font-size-xl);
  }

  .pd-price {
    font-size: var(--font-size-xl);
  }

  .pd-quantity {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
