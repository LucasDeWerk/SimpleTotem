<template>
  <button
    class="category-card"
    :class="{ active }"
    @click="$emit('click')"
  >
    <div class="category-image">
      <img v-if="image" :src="image" :alt="name" />
      <span v-else class="category-icon">{{ icon }}</span>
    </div>
    <span class="category-name">{{ name }}</span>
  </button>
</template>

<script setup>
defineProps({
  id: { type: String, default: '' },
  name: { type: String, required: true },
  icon: { type: String, default: '' },
  image: { type: String, default: '' },
  active: { type: Boolean, default: false }
})

defineEmits(['click'])
</script>

<style scoped>
.category-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-md);
  background: var(--bg-card);
  border: 2px solid transparent;
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  min-height: 160px;
  transition: border-color var(--transition-fast), transform var(--transition-fast), box-shadow var(--transition-fast);
  box-shadow: var(--shadow-sm);
}

.category-card:active {
  transform: scale(0.97);
}

.category-card.active {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
}

.category-image {
  width: 80px;
  height: 80px;
  border-radius: var(--radius-md);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary-light);
}

.category-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.category-icon {
  font-size: 2.5rem;
}

.category-name {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-color);
  text-align: center;
}
</style>
