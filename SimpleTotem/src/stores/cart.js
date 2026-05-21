import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { iniciarVenda } from '@/services/api'
export const useCartStore = defineStore('cart', () => {
  const items = ref([])
  const itemCount = computed(() => {
    return items.value.reduce((total, item) => total + item.quantity, 0)
  })
  const subtotal = computed(() => {
    return items.value.reduce((total, item) => total + item.totalPrice, 0)
  })
  const discount = ref(0)
  const total = computed(() => {
    return Math.max(0, subtotal.value - discount.value)
  })
  // Dados calculados pelo servidor (/iniciavenda)
  const vendaCalculada = ref(null)
  const calculandoVenda = ref(false)
  const erroCalculo = ref(null)
  function addItem(product, quantity = 1, notes = '', modifiers = []) {
    const existingIndex = items.value.findIndex(
      item => item.productId === product.id && JSON.stringify(item.modifiers) === JSON.stringify(modifiers)
    )
    if (existingIndex >= 0) {
      items.value[existingIndex].quantity += quantity
      items.value[existingIndex].totalPrice = items.value[existingIndex].quantity * items.value[existingIndex].unitPrice
    } else {
      const modifiersPrice = modifiers.reduce((sum, m) => sum + (m.price || 0), 0)
      const unitPrice = product.price + modifiersPrice
      items.value.push({
        productId: product.id,
        name: product.name,
        image: product.image || '',
        quantity,
        unitPrice,
        totalPrice: unitPrice * quantity,
        notes,
        modifiers
      })
    }
    vendaCalculada.value = null
  }
  function removeItem(index) {
    items.value.splice(index, 1)
    vendaCalculada.value = null
  }
  function updateQuantity(index, quantity) {
    if (quantity <= 0) {
      removeItem(index)
      return
    }
    items.value[index].quantity = quantity
    items.value[index].totalPrice = items.value[index].unitPrice * quantity
    vendaCalculada.value = null
  }
  function clearCart() {
    items.value = []
    discount.value = 0
    vendaCalculada.value = null
    erroCalculo.value = null
  }
  async function calcularVenda() {
    if (items.value.length === 0) return
    calculandoVenda.value = true
    erroCalculo.value = null
    try {
      const itens = items.value.map(item => ({
        produto_id: item.productId,
        descricao: item.name,
        quantidade: item.quantity,
        preco_unitario: item.unitPrice,
      }))
      vendaCalculada.value = await iniciarVenda(itens)
    } catch (err) {
      erroCalculo.value = err.message || 'Erro ao calcular venda'
      console.error('[Cart] Erro em calcularVenda:', err)
    } finally {
      calculandoVenda.value = false
    }
  }
  return {
    items,
    itemCount,
    subtotal,
    discount,
    total,
    vendaCalculada,
    calculandoVenda,
    erroCalculo,
    addItem,
    removeItem,
    updateQuantity,
    clearCart,
    calcularVenda,
  }
})
