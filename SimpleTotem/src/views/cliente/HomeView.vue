<template>
  <div class="home-view">
    <!-- Elementos decorativos de fundo -->
    <div class="bg-decoration bg-decoration-1"></div>
    <div class="bg-decoration bg-decoration-2"></div>

    <div class="home-wrapper">
      <!-- Seção principal -->
      <div class="home-main animate-fade-in">
        <div class="home-header">
          <h1 class="home-headline">{{ lang.t.welcome }}</h1>
          <p class="home-description">{{ lang.t.tapToStart }}</p>
        </div>

        <div class="home-cta">
          <button class="btn-start" @click="startOrder">
            <span class="btn-text">{{ lang.t.startOrder }}</span>
            <span class="btn-arrow">→</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Seletor de idioma -->
    <div class="home-lang-switcher">
      <LanguageSwitcher />
    </div>

    <!-- Acesso admin oculto: toque 5x no canto inferior direito -->
    <div class="admin-access-area" @click="adminTapCount++"></div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useLanguageStore } from '@/stores/language'
import { useSimpleSfiqueStore } from '@/stores/simplesfique'
import LanguageSwitcher from '@/components/shared/LanguageSwitcher.vue'

const router = useRouter()
const session = useSessionStore()
const lang = useLanguageStore()
const sfique = useSimpleSfiqueStore()

const adminTapCount = ref(0)

function startOrder() {
  if (!sfique.isConfigured) {
    router.push({ name: 'totem-login' })
    return
  }
  session.startSession()
  router.push({ name: 'catalog' })
}

// 5 toques vai para admin
watch(adminTapCount, (val) => {
  if (val >= 5) {
    adminTapCount.value = 0
    router.push({ name: 'admin-login' })
  }
})

// Reset tap count depois de 3s
watch(adminTapCount, () => {
  setTimeout(() => {
    if (adminTapCount.value > 0 && adminTapCount.value < 5) {
      adminTapCount.value = 0
    }
  }, 3000)
})
</script>

<style scoped>
.home-view {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(
    135deg,
    #fef9f5 0%,
    #fef5f0 50%,
    #fdeee7 100%
  );
  padding: var(--space-2xl);
  position: relative;
  overflow: hidden;
}

/* ========== Decorações de fundo ========== */
.bg-decoration {
  position: absolute;
  border-radius: 50%;
  opacity: 0.03;
  pointer-events: none;
  filter: blur(40px);
}

.bg-decoration-1 {
  width: 600px;
  height: 600px;
  background: linear-gradient(135deg, #F57C00, #E27602);
  top: -200px;
  right: -150px;
  animation: float 20s ease-in-out infinite;
}

.bg-decoration-2 {
  width: 500px;
  height: 500px;
  background: linear-gradient(135deg, #F57C00, #FF9800);
  bottom: -150px;
  left: -100px;
  animation: float 25s ease-in-out infinite reverse;
}

@keyframes float {
  0%, 100% {
    transform: translate(0, 0);
  }
  50% {
    transform: translate(30px, -30px);
  }
}

/* ========== Wrapper Principal ========== */
.home-wrapper {
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  max-width: 900px;
}

.home-main {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-xl);
  text-align: center;
  width: 100%;
  padding: var(--space-xl);
}

/* ========== Header ========== */
.home-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  max-width: 700px;
}

.home-headline {
  font-size: clamp(2.5rem, 10vw, 4.5rem);
  font-weight: 900;
  color: #0f172a;
  line-height: 1.2;
  letter-spacing: -0.02em;
  margin: 0;
  word-spacing: 0.1em;
}

.home-description {
  font-size: clamp(1rem, 2.5vw, 1.5rem);
  color: #64748b;
  font-weight: 500;
  margin: 0;
  line-height: 1.6;
  letter-spacing: 0.01em;
}

/* ========== CTA (Call To Action) ========== */
.home-cta {
  display: flex;
  justify-content: center;
  margin-top: var(--space-lg);
  width: 100%;
}

.btn-start {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 18px 48px;
  min-height: var(--btn-min-height);
  background: linear-gradient(135deg, #F57C00 0%, #E27602 100%);
  color: white;
  font-size: clamp(1rem, 2vw, 1.25rem);
  font-weight: 700;
  border: none;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  box-shadow: 0 10px 30px rgba(245, 124, 0, 0.3);
  letter-spacing: 0.5px;
  min-width: 280px;
  position: relative;
  overflow: hidden;
  line-height: 1;
}

.btn-start::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transform: translateX(-100%);
}

.btn-start:hover {
  transform: translateY(-2px);
  box-shadow: 0 15px 40px rgba(245, 124, 0, 0.4);
}

.btn-start:active {
  transform: translateY(0);
  box-shadow: 0 8px 20px rgba(245, 124, 0, 0.3);
}

.btn-text {
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  line-height: 1;
}

.btn-arrow {
  font-size: 1.25em;
  transition: transform 0.3s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  margin-left: 4px;
}

.btn-start:hover .btn-arrow {
  transform: translateX(4px);
}

/* ========== Botão de idioma ========== */
.home-lang-switcher {
  position: fixed;
  top: 24px;
  right: 24px;
  z-index: 20;
}

/* ========== Admin area ========== */
.admin-access-area {
  position: fixed;
  bottom: 0;
  right: 0;
  width: 60px;
  height: 60px;
  z-index: 5;
  cursor: pointer;
}

/* ========== Responsividade ========== */
@media (max-width: 768px) {
  .home-view {
    padding: var(--space-lg);
  }

  .home-main {
    gap: var(--space-lg);
  }

  .home-headline {
    font-size: 2.5rem;
  }

  .home-description {
    font-size: 1.1rem;
  }

  .btn-start {
    padding: 16px 40px;
    min-width: 240px;
    font-size: 1rem;
  }

  .bg-decoration-1,
  .bg-decoration-2 {
    opacity: 0.05;
  }

  .home-lang-switcher {
    top: 16px;
    right: 16px;
  }
}

@media (max-width: 480px) {
  .home-headline {
    font-size: 2rem;
  }

  .home-description {
    font-size: 1rem;
  }

  .btn-start {
    padding: 14px 32px;
    min-width: 200px;
    gap: 8px;
  }

  .home-lang-switcher {
    top: 16px;
    right: 16px;
  }
}

/* ========== Animações ========== */
.animate-fade-in {
  animation: fadeIn 0.8s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
