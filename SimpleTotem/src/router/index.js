import { createRouter, createWebHashHistory } from 'vue-router'

// Layout Cliente
import TotemClienteLayout from '@/layouts/TotemClienteLayout.vue'

// Views Cliente
import HomeView from '@/views/cliente/HomeView.vue'
import CatalogView from '@/views/cliente/CatalogView.vue'
import CartView from '@/views/cliente/CartView.vue'
import PaymentView from '@/views/cliente/PaymentView.vue'
import ProcessingView from '@/views/cliente/ProcessingView.vue'
import SuccessView from '@/views/cliente/SuccessView.vue'
import TimeoutView from '@/views/cliente/TimeoutView.vue'

// Views Admin (mínimo)
import AdminLoginView from '@/views/admin/AdminLoginView.vue'
import AdminPanelView from '@/views/admin/AdminPanelView.vue'

const routes = [
  {
    path: '/',
    redirect: '/totem'
  },

  // ===== CLIENTE =====
  {
    path: '/totem',
    component: TotemClienteLayout,
    children: [
      {
        path: '',
        name: 'home',
        component: HomeView,
        meta: { title: 'Início' }
      },
      {
        path: 'catalogo',
        name: 'catalog',
        component: CatalogView,
        meta: { title: 'Produtos' }
      },
      {
        path: 'carrinho',
        name: 'cart',
        component: CartView,
        meta: { title: 'Carrinho', showBack: true }
      },
      {
        path: 'pagamento',
        name: 'payment',
        component: PaymentView,
        meta: { title: 'Pagamento', showBack: true }
      },
      {
        path: 'processando',
        name: 'processing',
        component: ProcessingView,
        meta: { title: 'Processando', blockInteraction: true }
      },
      {
        path: 'concluido',
        name: 'success',
        component: SuccessView,
        meta: { title: 'Pedido Concluído' }
      },
      {
        path: 'timeout',
        name: 'timeout',
        component: TimeoutView,
        meta: { title: 'Sessão Encerrada' }
      }
    ]
  },

  // ===== ADMIN (login + painel único) =====
  {
    path: '/admin',
    name: 'admin-login',
    component: AdminLoginView,
    meta: { title: 'Acesso Administrativo' }
  },
  {
    path: '/admin/painel',
    name: 'admin-panel',
    component: AdminPanelView,
    meta: { title: 'Painel Admin', requiresAdmin: true }
  },
  {
    path: '/admin/hardware',
    name: 'admin-hardware',
    component: () => import('@/views/admin/AdminHardwareView.vue'),
    meta: { title: 'Configuração de Hardware', requiresAdmin: true }
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  if (to.meta.requiresAdmin) {
    const isAuthenticated = localStorage.getItem('admin_authenticated') === 'true'
    if (!isAuthenticated) {
      next({ name: 'admin-login' })
      return
    }
  }
  next()
})

export default router
