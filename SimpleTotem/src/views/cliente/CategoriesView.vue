<template>
  <ScreenContainer title="Categorias" subtitle="Escolha uma categoria para começar">
    <div class="categories-grid">
      <CategoryCard
        v-for="cat in catalog.categories"
        :key="cat.id"
        :id="cat.id"
        :name="cat.name"
        :icon="cat.icon"
        :image="cat.image"
        :active="catalog.selectedCategoryId === cat.id"
        @click="selectCategory(cat)"
      />
    </div>
  </ScreenContainer>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCatalogStore } from '@/stores/catalog'
import ScreenContainer from '@/components/shared/ScreenContainer.vue'
import CategoryCard from '@/components/shared/CategoryCard.vue'

const router = useRouter()
const catalog = useCatalogStore()

// Carregar categorias do banco quando a página monta
onMounted(async () => {
  if (catalog.categories.length === 0) {
    await catalog.fetchCategoriesFromDB()
  }
})

function selectCategory(cat) {
  catalog.selectCategory(cat.id)
  router.push({ name: 'products' })
}
</script>

<style scoped>
.categories-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-lg);
  padding-bottom: 100px;
}

/* ===== Responsividade ===== */
@media (max-width: 768px) {
  .categories-grid {
    grid-template-columns: 1fr;
    gap: var(--space-md);
  }
}

@media (max-width: 480px) {
  .categories-grid {
    gap: var(--space-sm);
  }
}
</style>
