<template>
  <ScreenContainer :title="categoryName" subtitle="Toque no produto para adicionar">
    <div class="products-grid">
      <ProductCard
        v-for="product in catalog.productsByCategory"
        :key="product.id"
        :id="product.id"
        :name="product.name"
        :price="product.price"
        :image="product.image"
        :badge="product.badge"
        :shortDescription="product.shortDescription"
        :hasCustomization="product.hasCustomization"
        @click="handleProductClick(product)"
      />
    </div>

    <div v-if="addedFeedback" class="added-feedback animate-slide-up">
      [+] Adicionado ao carrinho!
    </div>
  </ScreenContainer>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCatalogStore } from '@/stores/catalog'
import { useCartStore } from '@/stores/cart'
import ScreenContainer from '@/components/shared/ScreenContainer.vue'
import ProductCard from '@/components/shared/ProductCard.vue'

const router = useRouter()
const catalog = useCatalogStore()
const cart = useCartStore()

const addedFeedback = ref(false)

// Carregar produtos filtrados quando a página monta
onMounted(async () => {
  if (catalog.products.length === 0 && catalog.selectedCategoryId) {
    const categoryDbId = catalog.selectedCategoryId.replace('grupo-', '')
    await catalog.fetchProductsByGroup(parseInt(categoryDbId))
  }
})

const categoryName = computed(() => {
  const cat = catalog.categories.find(c => c.id === catalog.selectedCategoryId)
  return cat ? cat.name : 'Produtos'
})

function handleProductClick(product) {
  if (product.hasCustomization) {
    router.push({ name: 'product-detail', params: { id: product.id } })
  } else {
    cart.addItem(product)
    showFeedback()
  }
}

function showFeedback() {
  addedFeedback.value = true
  setTimeout(() => {
    addedFeedback.value = false
  }, 1500)
}
</script>

<style scoped>
.products-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-lg);
  padding-bottom: 100px;
}

.added-feedback {
  position: fixed;
  bottom: 100px;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, #4caf50, #45a049);
  color: white;
  padding: var(--space-md) var(--space-xl);
  border-radius: var(--radius-full);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  box-shadow: 0 8px 24px rgba(76, 175, 80, 0.3);
  z-index: 300;
  letter-spacing: 0.5px;
}

/* ===== Responsividade ===== */
@media (max-width: 768px) {
  .products-grid {
    grid-template-columns: 1fr;
    gap: var(--space-md);
  }
}

@media (max-width: 480px) {
  .products-grid {
    gap: var(--space-sm);
  }
}
</style>
