import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '@/services/api'
import { getProductImageUrl } from '@/utils/productImage'

export const useCatalogStore = defineStore('catalog', () => {
  const categories = ref([])
  const products = ref([])
  const selectedCategoryId = ref(null)
  const lastSyncAt = ref(null)
  const loading = ref(false)

  const productsByCategory = computed(() => {
    if (!selectedCategoryId.value) return products.value.sort((a, b) => a.id_produto - b.id_produto)
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

  function mapProduct(p) {
    const foto = getProductImageUrl(p.id_produto, p.foto)
    return {
      id_produto: p.id_produto,
      id_grupo: p.id_grupo,
      id_subgrupo: p.id_subgrupo,
      descproduto: p.descproduto,
      preco_venda: p.preco_venda,
      foto,
      image: foto,
      estoque: p.estoque,
      descgrupo: p.descgrupo,
      descsubgrupo: p.descsubgrupo,
      descmarca: p.descmarca,
      custo_medio: p.custo_medio
    }
  }

  /**
   * Carrega catálogo do banco de dados
   */
  async function fetchCatalog() {
    loading.value = true
    try {
      // Buscar grupos (categorias)
      const grupos = await api.obterGrupos()
      categories.value = (grupos || [])
        .sort((a, b) => a.id_grupo - b.id_grupo)
        .map(g => ({
          id: g.id_grupo,
          name: g.descgrupo,
          image: g.foto || '',
          icon: ''
        }))

      // Buscar produtos
      const prods = await api.obterProdutos()
      products.value = (prods || []).map(p => mapProduct(p))

      lastSyncAt.value = new Date().toISOString()
      console.log('[Catalog] ✅ Catálogo carregado com sucesso')
    } catch (error) {
      console.error('[Catalog] ⚠️ Erro ao buscar catálogo, usando dados vazios:', error)
      // Fallback: usar dados vazios se houver erro
      categories.value = []
      products.value = []
    } finally {
      loading.value = false
    }
  }

  /**
   * Carrega produtos filtrados por grupo
   */
  async function fetchProductsByGroup(idGrupo) {
    loading.value = true
    try {
      if (idGrupo) {
        const prods = await api.obterProdutos({ id_grupo: idGrupo })
        products.value = (prods || []).map(p => mapProduct(p))
      }
      selectCategory(idGrupo)
    } catch (error) {
      console.error('[Catalog] Erro ao buscar produtos do grupo:', error)
    } finally {
      loading.value = false
    }
  }

  return {
    categories,
    products,
    selectedCategoryId,
    lastSyncAt,
    loading,
    productsByCategory,
    getProductById,
    selectCategory,
    fetchCatalog,
    fetchProductsByGroup
  }
})
