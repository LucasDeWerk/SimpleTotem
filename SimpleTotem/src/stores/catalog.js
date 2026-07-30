import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getProductImageUrl } from '@/utils/productImage'
import { useSimpleSfiqueStore } from '@/stores/simplesfique'

export const useCatalogStore = defineStore('catalog', () => {
  const categories = ref([])
  const products = ref([])
  const selectedCategoryId = ref(null)
  const lastSyncAt = ref(null)
  const loading = ref(false)
  const loadError = ref(null)

  const productsByCategory = computed(() => {
    if (!selectedCategoryId.value) {
      return [...products.value].sort((a, b) => a.id_produto - b.id_produto)
    }
    return products.value
      .filter(p => p.id_grupo === selectedCategoryId.value)
      .sort((a, b) => a.id_produto - b.id_produto)
  })

  function getProductById(id) {
    return products.value.find(p => p.id_produto === id)
  }

  function selectCategory(categoryId) {
    selectedCategoryId.value = categoryId
  }

  function mapSfiqueProduct(mp) {
    const produtoId = Number(mp.produto_id ?? mp.id_produto ?? mp.produto?.id) || 0
    const menuId = Number(mp.menu_id) || 0
    const nome = mp.nome_produto || mp.produto?.nome || ''
    const preco = Number(
      mp.preco ??
      mp.preco_venda ??
      mp.valor_unitario ??
      mp.produto?.preco ??
      mp.produto?.preco_venda ??
      mp.produto?.valor_venda ??
      0
    )
    const rawFoto =
      mp.foto ||
      mp.produto?.foto ||
      (Array.isArray(mp.produto?.fotos) ? mp.produto.fotos[0] : mp.produto?.fotos) ||
      ''
    const apiFotoUrl = rawFoto.replace(/\\/g, '')
    const foto = getProductImageUrl(produtoId, apiFotoUrl)

    return {
      id_produto: produtoId,
      menu_produto_id: Number(mp.id) || null,
      id_grupo: menuId,
      id_subgrupo: null,
      descproduto: nome,
      preco_venda: preco,
      foto,
      image: foto,
      estoque: null,
      descgrupo: null,
      descsubgrupo: null,
      descmarca: null,
      emite_ticket: mp.emite_ticket ?? false,
      menu_id: menuId,
      ambiente_preparo_id: mp.ambiente_preparo_id != null ? Number(mp.ambiente_preparo_id) : null,
    }
  }

  function applySfiqueData(sfique) {
    categories.value = (sfique.menus || [])
      .filter(m => m.ativo !== false)
      .sort((a, b) => (a.ordem ?? 0) - (b.ordem ?? 0))
      .map(m => ({
        id: Number(m.id),
        name: m.nome,
        image: m.icone || '',
        icon: '',
      }))

    products.value = (sfique.menuProdutos || [])
      .map(mapSfiqueProduct)
      .filter(p => p.id_produto > 0)
      .sort((a, b) => a.id_produto - b.id_produto)
    lastSyncAt.value = new Date().toISOString()
  }

  /** Carrega catálogo exclusivamente da API SimplesFique */
  async function fetchCatalog(force = false) {
    loading.value = true
    loadError.value = null
    try {
      const sfique = useSimpleSfiqueStore()

      if (!sfique.isConfigured) {
        throw new Error('Terminal não configurado. Faça login no totem.')
      }

      // Usa cache local enquanto sincroniza
      if (sfique.menuProdutos.length > 0) {
        applySfiqueData(sfique)
      }

      await sfique.carregarConfig(force)

      // Se a API disse "sem mudança" mas ainda não temos dados, força download completo
      if (!force && sfique.menuProdutos.length === 0 && sfique.menus.length === 0) {
        await sfique.carregarConfig(true)
      }

      if (sfique.menuProdutos.length === 0 && sfique.menus.length === 0) {
        throw new Error('Nenhum produto disponível para este terminal.')
      }

      applySfiqueData(sfique)
      console.log('[Catalog] Catálogo carregado via SimplesFique:', {
        menus: categories.value.length,
        produtos: products.value.length,
      })
    } catch (error) {
      loadError.value = error.message || 'Erro ao carregar catálogo'
      console.error('[Catalog]', loadError.value)
      if (products.value.length === 0) {
        categories.value = []
        products.value = []
      }
      throw error
    } finally {
      loading.value = false
    }
  }

  function fetchProductsByGroup(idGrupo) {
    selectCategory(idGrupo)
  }

  return {
    categories,
    products,
    selectedCategoryId,
    lastSyncAt,
    loading,
    loadError,
    productsByCategory,
    getProductById,
    selectCategory,
    fetchCatalog,
    fetchProductsByGroup,
  }
})
