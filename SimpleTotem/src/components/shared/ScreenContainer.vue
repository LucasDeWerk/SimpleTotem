<template>
  <div class="screen-container" :class="{ 'full-height': fullHeight, 'centered': centered }">
    <div v-if="title || subtitle" class="screen-header">
      <h1 v-if="title" class="screen-title">{{ title }}</h1>
      <p v-if="subtitle" class="screen-subtitle">{{ subtitle }}</p>
    </div>
    <div class="screen-content">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  fullHeight: { type: Boolean, default: false },
  centered: { type: Boolean, default: false }
})
</script>

<style scoped>
.screen-container {
  display: flex;
  flex-direction: column;
  padding: var(--space-xl);
  overflow-y: auto;
  flex: 1;
  background: linear-gradient(
    135deg,
    #fef9f5 0%,
    #fef5f0 50%,
    #fdeee7 100%
  );
}

.screen-container.full-height {
  height: 100%;
}

.screen-container.centered {
  justify-content: center;
  align-items: center;
  text-align: center;
}

.screen-header {
  margin-bottom: var(--space-2xl);
  padding-bottom: var(--space-lg);
  border-bottom: 1px solid rgba(245, 124, 0, 0.08);
}

.screen-title {
  font-size: var(--font-size-3xl);
  font-weight: 900;
  color: #0f172a;
  margin-bottom: var(--space-md);
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.screen-subtitle {
  font-size: var(--font-size-lg);
  color: #64748b;
  opacity: 0.85;
  font-weight: 500;
  letter-spacing: 0.01em;
}

.screen-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}
</style>
