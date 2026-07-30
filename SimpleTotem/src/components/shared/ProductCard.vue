<template>
  <button class="product-card" @click="$emit('click')">
    <div class="product-image-wrap">
      <img v-if="image" :src="image" :alt="name" class="product-image" />
      <div v-else class="product-image-placeholder">📦</div>
      <span v-if="badge" class="product-badge" :class="badgeClass">{{ badge }}</span>
    </div>
    <div class="product-info">
      <h3 class="product-name">{{ name }}</h3>
      <p v-if="shortDescription" class="product-desc">{{ shortDescription }}</p>
      <div class="product-footer">
        <span class="product-price">R$ {{ displayPrice.toFixed(2) }}</span>
        <span v-if="hasCustomization" class="product-customize-hint">{{ customizeHint }}</span>
        <span v-else class="product-add-hint">{{ actionHint }}</span>
      </div>
    </div>
  </button>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  id: { type: String, default: '' },
  name: { type: String, required: true },
  price: { type: Number, required: true },
  image: { type: String, default: '' },
  badge: { type: String, default: '' },
  shortDescription: { type: String, default: '' },
  hasCustomization: { type: Boolean, default: false },
  actionHint: { type: String, default: 'Escolher quantidade' },
  customizeHint: { type: String, default: 'Personalizar' }
})

defineEmits(['click'])

const displayPrice = computed(() => Number(props.price) || 0)

const badgeClass = computed(() => {
  const b = props.badge.toLowerCase()
  if (b.includes('promo')) return 'badge-promo'
  if (b.includes('novo') || b.includes('new')) return 'badge-new'
  if (b.includes('vendido') || b.includes('popular')) return 'badge-popular'
  return 'badge-default'
})
</script>

<style scoped>
.product-card {
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
  text-align: left;
}

.product-card:active {
  transform: scale(0.98);
  box-shadow: var(--shadow-md);
}

.product-image-wrap {
  position: relative;
  width: 100%;
  height: 220px;
  background: var(--bg-color-third);
  overflow: hidden;
}

.product-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.product-image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 3rem;
  background: var(--color-primary-light);
}

.product-badge {
  position: absolute;
  top: var(--space-sm);
  right: var(--space-sm);
  padding: 4px 12px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.badge-promo {
  background: var(--color-error);
  color: white;
}

.badge-new {
  background: var(--color-info);
  color: white;
}

.badge-popular {
  background: var(--color-primary);
  color: white;
}

.badge-default {
  background: var(--text-color-fourth);
  color: white;
}

.product-info {
  padding: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  flex: 1;
}

.product-name {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--text-color);
  line-height: 1.3;
}

.product-desc {
  font-size: var(--font-size-md);
  color: var(--text-color-fourth);
  opacity: 0.7;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.product-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding-top: var(--space-md);
}

.product-price {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-color-laranja);
}

.product-customize-hint,
.product-add-hint {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-medium);
  color: var(--color-primary);
}
</style>
