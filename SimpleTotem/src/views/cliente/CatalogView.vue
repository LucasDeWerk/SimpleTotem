<template>
  <div class="catalog-view" @click="closeSidebarExpand">
    <!-- Overlay quando sidebar está expandida -->
    <div v-if="sidebarExpanded" class="sidebar-overlay" @click.stop="sidebarExpanded = false"></div>

    <!-- Sidebar de Grupos/Categorias -->
    <aside
      class="catalog-sidebar"
      :class="{ expanded: sidebarExpanded && !isWideLayout }"
      @click.stop="onSidebarClick"
    >
      <div class="sidebar-brand">

        <span class="brand-name">Simple<span class="brand-accent">Totem</span></span>
      </div>

      <nav class="sidebar-categories">
        <button
          v-for="cat in catalog.categories"
          :key="cat.id"
          class="sidebar-cat-btn"
          :class="{ active: catalog.selectedCategoryId === cat.id }"
          @click.stop="selectCategory(cat.id)"
        >
          <span class="cat-icon">{{ cat.icon }}</span>
          <span class="cat-name">{{ cat.name }}</span>
        </button>
      </nav>
    </aside>

    <!-- Área principal de produtos -->
    <main class="catalog-main">
      <div class="catalog-topbar">
        <button class="home-btn" @click="goHome" type="button">
          ← {{ lang.t.backToHome }}
        </button>
        <div class="topbar-info">
          <h2 class="topbar-title">{{ currentCategoryName }}</h2>
          <span class="topbar-count">
            {{ catalog.productsByCategory.length }}
            {{ catalog.productsByCategory.length === 1 ? lang.t.product : lang.t.products }}
          </span>
        </div>
        <div
          v-if="!device.isOnline"
          class="catalog-offline-badge"
          :title="lang.t.offline"
        >
          <span class="offline-dot" aria-hidden="true"></span>
          <span>{{ lang.t.offline }}</span>
        </div>
      </div>

      <!-- Grid de produtos -->
      <div class="products-area">
        <div v-if="catalog.loading" class="loading-message">
          <div class="loading-spinner-ring"></div>
          <p>{{ lang.t.loadingProducts }}</p>
        </div>

        <div v-else-if="catalog.productsByCategory.length === 0" class="empty-message">
          <span class="empty-icon">📦</span>
          <p>{{ lang.t.noProducts }}</p>
          <p class="empty-hint">{{ lang.t.tryOtherCategory }}</p>
        </div>

        <div v-else class="products-grid">
          <ProductCard
            v-for="product in catalog.productsByCategory"
            :key="product.id_produto"
            :id="product.id_produto"
            :name="product.descproduto"
            :price="product.preco_venda"
            :image="product.foto"
            :badge="null"
            :shortDescription="`${product.descsubgrupo} - ${product.descmarca || ''}`"
            :hasCustomization="false"
            :actionHint="lang.t.chooseQuantity"
            @click="handleProductClick(product)"
          />
        </div>

        <!-- Feedback de adicionado -->
        <transition name="slide-up">
          <div v-if="addedFeedback" class="added-toast">
            ✓ {{ addedProductName }} {{ lang.t.addedToCart }}
          </div>
        </transition>
      </div>
    </main>

    <!-- Footer / Barra do Carrinho -->
    <footer class="catalog-footer" :class="{ 'has-items': cart.itemCount > 0 }">
      <div v-if="cart.itemCount > 0" class="footer-cart">
        <div class="footer-items-scroll">
          <div class="footer-items-preview">
          <div
            v-for="(item, index) in cart.items.slice(0, 4)"
            :key="index"
            class="footer-item-chip"
          >
            <span class="chip-qty">{{ item.quantity }}x</span>
            <span class="chip-name">{{ item.name }}</span>
          </div>
          <span v-if="cart.items.length > 4" class="chip-more">
            +{{ cart.items.length - 4 }} {{ lang.t.moreItems }}
          </span>
          </div>
        </div>

        <div class="footer-actions">
          <div class="footer-total-info">
            <span class="footer-item-count">
              {{ cart.itemCount }} {{ cart.itemCount === 1 ? lang.t.item : lang.t.items }}
            </span>
            <span class="footer-total">R$ {{ cart.total.toFixed(2) }}</span>
          </div>
          <button class="footer-checkout-btn" @click="goToCart">
            <span>{{ lang.t.viewCart }}</span>
            <span class="checkout-arrow">→</span>
          </button>
        </div>
      </div>

      <div v-else class="footer-empty">
        <span class="footer-empty-icon">🛒</span>
        <span class="footer-empty-text">{{ lang.t.cartEmpty }}</span>
      </div>
    </footer>

    <!-- Modal de detalhe do produto -->
    <transition name="fade">
      <div v-if="selectedProduct" class="product-modal-overlay" @click.self="closeDetail">
        <div class="product-modal animate-slide-up">
          <button class="modal-close" @click="closeDetail">✕</button>

          <div class="modal-image-area">
            <img v-if="selectedProduct.foto" :src="selectedProduct.foto" :alt="selectedProduct.descproduto" />
            <div v-else class="modal-image-placeholder">📦</div>
          </div>

          <div class="modal-body">
            <h3 class="modal-product-name">{{ selectedProduct.descproduto }}</h3>
            <p class="modal-product-desc">{{ selectedProduct.descsubgrupo }} - {{ selectedProduct.descmarca }}</p>
            <span class="modal-product-price">R$ {{ selectedProduct.preco_venda.toFixed(2) }}</span>

            <div class="modal-quantity">
              <span class="modal-qty-label">{{ lang.t.quantity }}</span>
              <QuantityStepper v-model="detailQuantity" :min="1" :max="20" />
            </div>

            <div class="modal-notes">
              <label class="modal-notes-label">{{ lang.t.notesOptional }}</label>
              <textarea
                v-model="detailNotes"
                class="modal-notes-input"
                :placeholder="lang.t.notesPlaceholder"
                rows="2"
              ></textarea>
            </div>

            <div class="modal-total">
              <span>{{ lang.t.total }}:</span>
              <strong>R$ {{ (selectedProduct.preco_venda * detailQuantity).toFixed(2) }}</strong>
            </div>

            <button class="modal-add-btn" @click="addDetailToCart">
              {{ lang.t.addToCart }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCatalogStore } from '@/stores/catalog'
import { useCartStore } from '@/stores/cart'
import { useSessionStore } from '@/stores/session'
import { useLanguageStore } from '@/stores/language'
import { useDeviceStore } from '@/stores/device'
import ProductCard from '@/components/shared/ProductCard.vue'
import QuantityStepper from '@/components/shared/QuantityStepper.vue'

const router = useRouter()
const catalog = useCatalogStore()
const cart = useCartStore()
const session = useSessionStore()
const lang = useLanguageStore()
const device = useDeviceStore()

const isWideLayout = ref(typeof window !== 'undefined' ? window.innerWidth >= 1080 : true)

function updateLayout() {
  isWideLayout.value = window.innerWidth >= 1080
  if (isWideLayout.value) sidebarExpanded.value = false
}

onMounted(async () => {
  window.addEventListener('resize', updateLayout)
  try {
    if (catalog.categories.length === 0) {
      await catalog.fetchCatalog()
    }
    if (!catalog.selectedCategoryId && catalog.categories.length > 0) {
      catalog.selectCategory(catalog.categories[0].id)
    }
  } catch (error) {
    console.error('[CatalogView] Erro ao carregar catálogo:', error)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', updateLayout)
})

const addedFeedback = ref(false)
const addedProductName = ref('')

// Sidebar expandida
const sidebarExpanded = ref(false)

// Modal detalhe
const selectedProduct = ref(null)
const detailQuantity = ref(1)
const detailNotes = ref('')

const currentCategoryName = computed(() => {
  const cat = catalog.categories.find(c => c.id === catalog.selectedCategoryId)
  return cat ? cat.name : 'Todos os Produtos'
})

function handleProductClick(product) {
  // Todos os produtos abrem no detalhe para possíveis observações
  openDetail(product)
}

function openDetail(product) {
  selectedProduct.value = product
  detailQuantity.value = 1
  detailNotes.value = ''
}

function closeDetail() {
  selectedProduct.value = null
}

function addDetailToCart() {
  if (!selectedProduct.value) return

  const produtoParaCarrinho = {
    id: selectedProduct.value.id_produto,
    name: selectedProduct.value.descproduto,
    price: selectedProduct.value.preco_venda,
    image: selectedProduct.value.foto
  }

  cart.addItem(produtoParaCarrinho, detailQuantity.value, detailNotes.value)
  showFeedback(selectedProduct.value.descproduto)
  closeDetail()
}

function showFeedback(name) {
  addedProductName.value = name
  addedFeedback.value = true
  setTimeout(() => {
    addedFeedback.value = false
  }, 1500)
}

function goToCart() {
  router.push({ name: 'cart' })
}

async function goHome() {
  cart.clearCart()
  await router.replace({ name: 'home' })
  session.endSession()
}

function onSidebarClick() {
  if (!isWideLayout.value) {
    sidebarExpanded.value = true
  }
}

function selectCategory(categoryId) {
  catalog.selectCategory(categoryId)
  sidebarExpanded.value = false
}

function closeSidebarExpand() {
  sidebarExpanded.value = false
}
</script>

<style scoped>
.catalog-view {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  grid-template-rows: 1fr auto;
  height: 100%;
  overflow: hidden;
  background: linear-gradient(
    135deg,
    #fef9f5 0%,
    #fef5f0 50%,
    #fdeee7 100%
  );
}

/* ===== SIDEBAR ===== */
.catalog-sidebar {
  grid-row: 1 / 3;
  background: rgba(255, 255, 255, 0.95);
  border-right: 1px solid rgba(245, 124, 0, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 100;
  cursor: pointer;
  backdrop-filter: blur(10px);
}

.catalog-sidebar.expanded {
  width: 420px;
}

.sidebar-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 90;
  animation: fadeIn 0.3s ease;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-lg) var(--space-md);
  border-bottom: 1px solid rgba(245, 124, 0, 0.1);
  flex-shrink: 0;
  background: linear-gradient(135deg, rgba(245, 124, 0, 0.05), rgba(245, 124, 0, 0.02));
}

.brand-logo {
  font-size: 1.5rem;
  background: linear-gradient(135deg, #F57C00, #E27602);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: bold;
}

.brand-name {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-bold);
  color: var(--text-color);
  letter-spacing: -0.5px;
}

.brand-accent {
  color: var(--color-primary);
}

.sidebar-categories {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-sm);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sidebar-cat-btn {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-lg) var(--space-xl);
  border-radius: var(--radius-lg);
  background: transparent;
  color: var(--text-color);
  font-size: var(--font-size-xl);
  text-align: left;
  transition: all var(--transition-fast);
  min-height: 72px;
  flex-shrink: 0;
  font-weight: var(--font-weight-medium);
  border: 2px solid transparent;
}

.sidebar-cat-btn:active {
  background: rgba(245, 124, 0, 0.08);
  transform: translateX(4px);
}

.sidebar-cat-btn.active {
  background: linear-gradient(135deg, #F57C00 0%, #E27602 100%);
  color: white;
  font-weight: var(--font-weight-bold);
  box-shadow: 0 8px 24px rgba(245, 124, 0, 0.35);
  border-color: #F57C00;
}

.cat-icon {
  font-size: 1.3rem;
  width: 28px;
  text-align: center;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.cat-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ===== MAIN ===== */
.catalog-main {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: transparent;
  min-width: 0;
}

.catalog-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-lg);
  padding: var(--space-lg) var(--space-xl);
  border-bottom: 1px solid rgba(245, 124, 0, 0.08);
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(10px);
}

.home-btn {
  flex-shrink: 0;
  min-height: 48px;
  padding: var(--space-sm) var(--space-lg);
  background: rgba(245, 124, 0, 0.08);
  border: 1px solid rgba(245, 124, 0, 0.2);
  border-radius: var(--radius-md);
  color: var(--color-primary);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-bold);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.home-btn:active {
  background: rgba(245, 124, 0, 0.15);
}

.topbar-info {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
}

.topbar-title {
  font-size: var(--font-size-3xl);
  font-weight: 900;
  color: #0f172a;
  letter-spacing: -0.02em;
}

.topbar-count {
  font-size: var(--font-size-md);
  color: #64748b;
  opacity: 0.8;
  font-weight: 500;
}

.catalog-offline-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  padding: 8px 14px;
  min-height: 48px;
  background: rgba(244, 67, 54, 0.1);
  border: 1px solid rgba(244, 67, 54, 0.25);
  border-radius: var(--radius-md);
  color: var(--color-error);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  white-space: nowrap;
}

.offline-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-error);
  flex-shrink: 0;
}

.products-area {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-xl);
  position: relative;
}

.products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-xl);
  padding-bottom: var(--space-lg);
}

.loading-message,
.empty-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-lg);
  padding: var(--space-3xl) 0;
  color: #64748b;
  text-align: center;
}

.loading-spinner-ring {
  width: 48px;
  height: 48px;
  border: 4px solid rgba(245, 124, 0, 0.15);
  border-top-color: #F57C00;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.empty-hint {
  font-size: var(--font-size-md);
  color: #94a3b8;
  margin: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 3rem;
  opacity: 0.4;
}

.added-toast {
  position: fixed;
  bottom: 120px;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, #4caf50, #45a049);
  color: white;
  padding: var(--space-md) var(--space-xl);
  border-radius: var(--radius-full);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  box-shadow: 0 8px 24px rgba(76, 175, 80, 0.3);
  z-index: 500;
  white-space: nowrap;
  letter-spacing: 0.5px;
}

/* ===== FOOTER / CARRINHO ===== */
.catalog-footer {
  grid-column: 2;
  background: rgba(255, 255, 255, 0.95);
  border-top: 1px solid rgba(245, 124, 0, 0.1);
  padding: var(--space-md) var(--space-xl);
  flex-shrink: 0;
  min-width: 0;
  max-width: 100%;
  display: flex;
  align-items: stretch;
  transition: all var(--transition-fast);
  backdrop-filter: blur(10px);
}

.catalog-footer.has-items {
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 -4px 24px rgba(245, 124, 0, 0.15);
  min-height: auto;
  padding-top: var(--space-sm);
  padding-bottom: var(--space-md);
}

.footer-empty {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  width: 100%;
  justify-content: center;
  opacity: 0.5;
}

.footer-empty-icon {
  font-size: 1.2rem;
}

.footer-empty-text {
  font-size: var(--font-size-sm);
  color: #64748b;
  font-weight: 500;
}

.footer-cart {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 0;
  gap: var(--space-sm);
}

.footer-items-scroll {
  position: relative;
  width: 100%;
  max-width: 100%;
}

.footer-items-scroll::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 40px;
  background: linear-gradient(to right, transparent, rgba(255, 255, 255, 0.98));
  pointer-events: none;
}

.footer-items-preview {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  width: 100%;
  max-width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  padding-bottom: 2px;
}

.footer-items-preview::-webkit-scrollbar {
  display: none;
}

.footer-item-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(245, 124, 0, 0.08);
  border: 1px solid rgba(245, 124, 0, 0.2);
  border-radius: var(--radius-full);
  padding: 8px 14px;
  font-size: var(--font-size-sm);
  white-space: nowrap;
  flex-shrink: 0;
  max-width: 160px;
}

.footer-item-chip:hover {
  background: rgba(245, 124, 0, 0.12);
  border-color: rgba(245, 124, 0, 0.3);
}

.chip-qty {
  font-weight: var(--font-weight-bold);
  color: var(--color-primary);
  flex-shrink: 0;
}

.chip-name {
  color: var(--text-color);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chip-more {
  font-size: var(--font-size-xs);
  color: #64748b;
  flex-shrink: 0;
  font-weight: 600;
  white-space: nowrap;
  padding: 8px 12px;
  background: rgba(245, 124, 0, 0.06);
  border-radius: var(--radius-full);
}

.footer-actions {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-md);
  width: 100%;
}

.footer-total-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-width: 0;
}

.footer-item-count {
  font-size: var(--font-size-sm);
  color: #64748b;
  font-weight: 500;
}

.footer-total {
  font-size: clamp(1.25rem, 2.5vw, 2rem);
  font-weight: 900;
  color: var(--text-color-laranja);
  white-space: nowrap;
  letter-spacing: -0.01em;
}

.footer-checkout-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: linear-gradient(135deg, #F57C00 0%, #E27602 100%);
  color: white;
  padding: var(--space-md) var(--space-xl);
  border-radius: var(--radius-md);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  min-height: var(--btn-min-height);
  min-width: 200px;
  transition: all var(--transition-fast);
  white-space: nowrap;
  box-shadow: 0 8px 24px rgba(245, 124, 0, 0.3);
  letter-spacing: 0.5px;
  line-height: 1;
  border: none;
  cursor: pointer;
  flex-shrink: 0;
}

.footer-checkout-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(245, 124, 0, 0.4);
}

.footer-checkout-btn:active {
  transform: translateY(0);
  box-shadow: 0 6px 16px rgba(245, 124, 0, 0.3);
}

.checkout-arrow {
  font-size: 1.2em;
  transition: transform 0.3s ease;
  display: inline-flex;
  align-items: center;
}

.footer-checkout-btn:hover .checkout-arrow {
  transform: translateX(4px);
}

/* ===== MODAL DE DETALHE ===== */
.product-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: var(--space-xl);
}

.product-modal {
  background: white;
  border-radius: var(--radius-xl);
  max-width: 640px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-close {
  position: absolute;
  top: var(--space-md);
  right: var(--space-md);
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  font-size: 1.4rem;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
  transition: all var(--transition-fast);
  border: none;
  cursor: pointer;
}

.modal-close:hover {
  background: rgba(0, 0, 0, 0.8);
  transform: rotate(90deg);
}

.modal-image-area {
  width: 100%;
  height: 340px;
  background: linear-gradient(135deg, rgba(245, 124, 0, 0.1), rgba(245, 124, 0, 0.05));
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  overflow: hidden;
}

.modal-image-area img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.modal-image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 4rem;
  background: linear-gradient(135deg, rgba(245, 124, 0, 0.08), rgba(245, 124, 0, 0.04));
  color: var(--color-primary);
}

.modal-body {
  padding: var(--space-xl);
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.modal-product-name {
  font-size: var(--font-size-2xl);
  font-weight: 900;
  color: #0f172a;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.modal-product-desc {
  font-size: var(--font-size-md);
  color: #64748b;
  line-height: 1.5;
  font-weight: 500;
}

.modal-product-price {
  font-size: var(--font-size-3xl);
  font-weight: 900;
  color: var(--text-color-laranja);
  letter-spacing: -0.01em;
}

.modal-quantity {
  display: flex;
  align-items: center;
  gap: var(--space-lg);
  padding: var(--space-md) 0;
  border-top: 1px solid rgba(245, 124, 0, 0.08);
  border-bottom: 1px solid rgba(245, 124, 0, 0.08);
}

.modal-qty-label {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  color: #0f172a;
}

.modal-notes {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.modal-notes-label {
  font-size: var(--font-size-sm);
  color: #64748b;
  font-weight: 600;
}

.modal-notes-input {
  padding: var(--space-md);
  border: 1px solid rgba(245, 124, 0, 0.15);
  border-radius: var(--radius-md);
  background: rgba(245, 124, 0, 0.03);
  color: var(--text-color);
  font-size: var(--font-size-md);
  resize: none;
  font-family: inherit;
  transition: all var(--transition-fast);
}

.modal-notes-input:focus {
  outline: none;
  border-color: rgba(245, 124, 0, 0.3);
  background: rgba(245, 124, 0, 0.05);
}

.modal-notes-input::placeholder {
  color: #cbd5e1;
  opacity: 1;
}

.modal-total {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md) var(--space-lg);
  background: linear-gradient(135deg, rgba(245, 124, 0, 0.08), rgba(245, 124, 0, 0.04));
  border-radius: var(--radius-md);
  border: 1px solid rgba(245, 124, 0, 0.15);
  font-size: var(--font-size-lg);
  color: #0f172a;
  font-weight: 600;
}

.modal-total strong {
  font-size: var(--font-size-2xl);
  color: var(--text-color-laranja);
  font-weight: 900;
}

.modal-add-btn {
  width: 100%;
  min-height: var(--btn-min-height);
  background: linear-gradient(135deg, #F57C00 0%, #E27602 100%);
  color: white;
  border-radius: var(--radius-md);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  transition: all var(--transition-fast);
  box-shadow: 0 8px 24px rgba(245, 124, 0, 0.3);
  border: none;
  cursor: pointer;
  letter-spacing: 0.5px;
}

.modal-add-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(245, 124, 0, 0.4);
}

.modal-add-btn:active {
  transform: translateY(0);
  box-shadow: 0 6px 16px rgba(245, 124, 0, 0.3);
}

/* ===== Responsividade ===== */
@media (max-width: 768px) {
  .catalog-view {
    grid-template-columns: 1fr;
  }

  .catalog-sidebar {
    grid-row: 1;
  }

  .catalog-footer {
    grid-column: 1;
  }

  .catalog-topbar {
    padding: var(--space-md) var(--space-lg);
    flex-wrap: wrap;
    gap: var(--space-sm);
  }

  .catalog-offline-badge {
    width: 100%;
    justify-content: center;
  }

  .topbar-title {
    font-size: var(--font-size-xl);
  }

  .products-grid {
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: var(--space-md);
  }

  .footer-actions {
    grid-template-columns: 1fr;
    gap: var(--space-sm);
  }

  .footer-checkout-btn {
    width: 100%;
    min-width: 0;
  }

  .footer-total-info {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    width: 100%;
  }
}

@media (max-width: 480px) {
  .products-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: var(--space-sm);
  }

  .products-area {
    padding: var(--space-md);
  }

  .catalog-topbar {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-sm);
  }

  .modal-body {
    padding: var(--space-lg);
  }

  .footer-items-preview {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
}
</style>
